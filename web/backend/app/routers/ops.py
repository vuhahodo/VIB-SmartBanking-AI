import json
import logging
import os
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from ..database import engine
from .applications import OUTBOX_DIR, flush_local_outbox, is_chaos_db_down, set_chaos_db_down

router = APIRouter(prefix="/ops", tags=["ops"])
logger = logging.getLogger("vib.ops")


def _get_k8s_token() -> str:
    token_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
    if token_path.exists():
        return token_path.read_text().strip()
    return ""


def _call_k8s(path: str):
    token = _get_k8s_token()
    if not token:
        return None
    url = f"https://kubernetes.default.svc{path}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=4) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Lỗi khi truy vấn K8s API (%s): %s", path, exc)
        return None


@router.get("/cluster")
def get_cluster_status():
    """Lấy dữ liệu giám sát thời gian thực toàn bộ hạ tầng Cloud K8s, DB, Outbox, HPA và Events."""
    # 1. Kiểm tra trạng thái Database & Latency
    is_sim_down = is_chaos_db_down()
    if is_sim_down:
        db_status = "DOWN (SỰ CỐ MÔ PHỎNG)"
        db_latency_ms = -1.0
    else:
        db_status = "ONLINE"
        db_latency_ms = 0.0
        t0 = time.perf_counter()
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        except Exception as e:
            db_status = "DOWN"
            db_latency_ms = -1.0
            logger.warning("Database không khả dụng: %s", e)

    # 2. Kiểm tra bộ đệm Outbox phục hồi thảm họa
    outbox_files = list(OUTBOX_DIR.glob("*.json"))
    pending_items = []
    for f in outbox_files[:15]:
        try:
            pending_items.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass

    # 3. Lấy thông tin Pods từ K8s API
    pods_data = []
    pods_raw = _call_k8s("/api/v1/namespaces/vib-banking/pods")
    if pods_raw and "items" in pods_raw:
        for p in pods_raw["items"]:
            meta = p.get("metadata", {})
            st = p.get("status", {})
            spec = p.get("spec", {})
            c_statuses = st.get("containerStatuses", [])
            restarts = sum(cs.get("restartCount", 0) for cs in c_statuses)
            ready = all(cs.get("ready", False) for cs in c_statuses) if c_statuses else False

            created = meta.get("creationTimestamp", "")
            age_str = ""
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    seconds = (datetime.now(timezone.utc) - dt).total_seconds()
                    if seconds < 60:
                        age_str = f"{int(seconds)}s"
                    elif seconds < 3600:
                        age_str = f"{int(seconds // 60)}m"
                    else:
                        age_str = f"{int(seconds // 3600)}h"
                except Exception:
                    age_str = created

            pods_data.append({
                "name": meta.get("name", "unknown"),
                "app": meta.get("labels", {}).get("app", "unknown"),
                "phase": st.get("phase", "Unknown"),
                "ready": ready,
                "restarts": restarts,
                "ip": st.get("podIP", "N/A"),
                "node": spec.get("nodeName", "N/A"),
                "age": age_str,
            })

    # 4. Lấy thông tin HPA
    hpa_data = {"backend": {"current": 2, "min": 2, "max": 8, "target_cpu": 70, "current_cpu": 0}}
    hpa_raw = _call_k8s("/apis/autoscaling/v2/namespaces/vib-banking/horizontalpodautoscalers")
    if hpa_raw and "items" in hpa_raw:
        for item in hpa_raw["items"]:
            name = item.get("metadata", {}).get("name", "")
            spec = item.get("spec", {})
            st = item.get("status", {})
            current_replicas = st.get("currentReplicas", 2)
            min_r = spec.get("minReplicas", 2)
            max_r = spec.get("maxReplicas", 8)
            curr_cpu = 0
            for m in st.get("currentMetrics", []):
                if m.get("type") == "Resource" and m.get("resource", {}).get("name") == "cpu":
                    curr_cpu = m.get("resource", {}).get("current", {}).get("averageUtilization", 0)

            key = "backend" if "backend" in name else "frontend"
            hpa_data[key] = {
                "min": min_r,
                "max": max_r,
                "current": current_replicas,
                "target_cpu": 70 if key == "backend" else 80,
                "current_cpu": curr_cpu or 0,
            }

    # 5. Lấy các sự kiện K8s gần nhất (Events Log)
    events_data = []
    events_raw = _call_k8s("/api/v1/namespaces/vib-banking/events")
    if events_raw and "items" in events_raw:
        sorted_events = sorted(
            events_raw["items"],
            key=lambda x: x.get("lastTimestamp") or x.get("eventTime") or "",
            reverse=True,
        )
        for e in sorted_events[:12]:
            events_data.append({
                "type": e.get("type", "Normal"),
                "reason": e.get("reason", "Unknown"),
                "message": e.get("message", ""),
                "involved": e.get("involvedObject", {}).get("name", ""),
                "time": e.get("lastTimestamp") or e.get("eventTime") or "Vừa xong",
            })

    # Đánh giá tổng quan sức khỏe hệ thống
    total_restarts = sum(p["restarts"] for p in pods_data)
    degraded = is_sim_down or db_status != "ONLINE" or any(not p["ready"] for p in pods_data if p["phase"] == "Running") or len(outbox_files) > 0
    overall_health = "DEGRADED" if degraded else "HEALTHY"

    return {
        "status": overall_health,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chaos": {"db_down": is_sim_down},
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
            "pvc": "postgres-pvc (5Gi Persistent)",
            "network_policy": "Chỉ Backend & Backup được truy cập",
        },
        "outbox": {
            "pending_count": len(outbox_files),
            "pending_items": pending_items,
            "worker_interval_sec": 2,
            "worker_status": "TẠM DỪNG (Do DB đang lỗi)" if is_sim_down else "RUNNING (Tự động đồng bộ ngầm)",
        },
        "hpa": hpa_data,
        "security": {
            "https": True,
            "protocol": "TLSv1.3",
            "rate_limiting": "25 RPS (Burst 50)",
            "network_policy_active": True,
            "hsts_active": True,
        },
        "pods": pods_data,
        "events": events_data,
        "summary": {
            "total_pods": len(pods_data),
            "ready_pods": sum(1 for p in pods_data if p["ready"]),
            "total_restarts": total_restarts,
        },
    }


@router.post("/toggle-chaos-db")
def toggle_chaos_db():
    """Bật / Tắt chế độ giả lập sự cố mất kết nối Database để dev kiểm chứng Outbox đồng bộ toàn cụm."""
    current_down = is_chaos_db_down()
    new_down = not current_down
    set_chaos_db_down(new_down)
    if not new_down:
        # Khi khôi phục DB, tự động kích hoạt đồng bộ Outbox
        flush_local_outbox()
    return {
        "status": "SUCCESS",
        "chaos_db_down": new_down,
        "message": "⚠️ ĐÃ KÍCH HOẠT SỰ CỐ MÔ PHỎNG: Database bị ngắt kết nối. Mọi đơn đăng ký mới sẽ lưu vào Outbox!" if new_down else "✓ ĐÃ KHÔI PHỤC KẾT NỐI: Database online trở lại. Toàn bộ đơn trong Outbox đã được tự động đồng bộ vào PostgreSQL!",
    }


@router.post("/stress-test")
def trigger_stress_test():
    """Gây tải CPU nhanh bằng việc suy luận hàng loạt để dev quan sát HPA co giãn."""
    import concurrent.futures
    from ..ai_engine import load_engine
    eng = load_engine()
    dummy_feat = {"CUSTOMER_NUMBER": "00992830", "has_loan": 1, "has_creditcard": 0}
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(eng.predict_single, dummy_feat) for _ in range(60)]
        concurrent.futures.wait(futures)
    dur_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "status": "SUCCESS",
        "message": f"Đã thực hiện burst 60 phép tính AI XGBoost trong {dur_ms}ms để kích hoạt tải CPU cho HPA.",
        "duration_ms": dur_ms,
    }


@router.post("/sync-outbox")
def sync_outbox_manual():
    """Kích hoạt ép buộc đối soát Outbox khẩn cấp từ giao diện Dev."""
    synced, errors = flush_local_outbox()
    return {
        "status": "SUCCESS",
        "message": f"Đối soát thành công {len(synced)} hồ sơ vào cơ sở dữ liệu.",
        "synced": synced,
        "errors": errors,
    }


@router.post("/trigger-backup")
def trigger_backup_manual():
    """Kích hoạt Job sao lưu PostgreSQL tức thời qua K8s API."""
    token = _get_k8s_token()
    if not token:
        return {"status": "SKIPPED", "message": "Không tìm thấy serviceaccount token (môi trường non-K8s)."}

    cj = _call_k8s("/apis/batch/v1/namespaces/vib-banking/cronjobs/pg-backup")
    if not cj:
        return {"status": "ERROR", "message": "Không tìm thấy CronJob pg-backup trong namespace vib-banking."}

    job_name = f"pg-backup-ondemand-{int(time.time())}"
    job_spec = cj.get("spec", {}).get("jobTemplate", {}).get("spec", {})
    body = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": "vib-banking",
        },
        "spec": job_spec,
    }

    url = "https://kubernetes.default.svc/apis/batch/v1/namespaces/vib-banking/jobs"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            return {
                "status": "SUCCESS",
                "message": f"Đã kích hoạt Job sao lưu cơ sở dữ liệu '{job_name}' thành công!",
                "job_name": job_name,
            }
    except Exception as exc:
        return {"status": "ERROR", "message": f"Lỗi kích hoạt K8s Job: {exc}"}
