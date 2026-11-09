import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..ai_engine import PRODUCTS_BY_CODE, VIBRecommendationEngine, get_engine
from ..auth import get_current_customer
from ..database import SessionLocal, get_db
from ..models import Application
from ..schemas import ApplicationIn, ApplicationOut

router = APIRouter(prefix="/applications", tags=["applications"])
logger = logging.getLogger("vib.applications")

# Thư mục Outbox buffer đệm hồ sơ khi Database gặp sự cố (Resilience Storage)
OUTBOX_DIR = Path("/tmp/vib_outbox")
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)


def is_chaos_db_down() -> bool:
    """Kiểm tra cờ sự cố database dùng chung trên toàn bộ các pod của cụm K8s."""
    try:
        with SessionLocal() as db:
            val = db.execute(text("SELECT is_active FROM system_chaos WHERE key = 'db_down'")).scalar()
            return bool(val)
    except Exception:
        return False


def set_chaos_db_down(down: bool) -> bool:
    """Cập nhật cờ sự cố database vào PostgreSQL để đồng bộ tức thì mọi replica pod."""
    try:
        with SessionLocal() as db:
            db.execute(
                text("INSERT INTO system_chaos (key, is_active, updated_at) VALUES ('db_down', :v, NOW()) ON CONFLICT (key) DO UPDATE SET is_active = :v, updated_at = NOW()"),
                {"v": down}
            )
            db.commit()
            return True
    except Exception as e:
        logger.warning("Không thể cập nhật system_chaos: %s", e)
        return False


def flush_local_outbox():
    """Đồng bộ các file json trong outbox buffer nội bộ của pod vào DB."""
    if is_chaos_db_down():
        return [], []
    synced = []
    errors = []
    files = list(OUTBOX_DIR.glob("*.json"))
    if not files:
        return synced, errors
    try:
        with SessionLocal() as db:
            for filepath in files:
                try:
                    data = json.loads(filepath.read_text(encoding="utf-8"))
                    app_code = data["application_code"]
                    exists = db.scalar(select(Application).where(Application.application_code == app_code))
                    if not exists:
                        app = Application(
                            application_code=app_code,
                            customer_number=data["customer_number"],
                            product_code=data["product_code"],
                            status="SUBMITTED",
                            payload={
                                **data.get("payload", {}),
                                "synced_from_outbox": True,
                                "synced_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        db.add(app)
                        db.commit()
                    filepath.unlink(missing_ok=True)
                    synced.append(app_code)
                    logger.info("Outbox worker: đã nạp thành công đơn %s vào PostgreSQL", app_code)
                except Exception as e:
                    db.rollback()
                    errors.append({"file": filepath.name, "error": str(e)})
    except Exception as conn_err:
        logger.debug("Outbox worker: DB chưa sẵn sàng (%s)", conn_err)
    return synced, errors


def _start_background_syncer():
    import threading
    import time

    def _loop():
        while True:
            time.sleep(2)
            try:
                flush_local_outbox()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


_start_background_syncer()


def to_out(a: Application, is_duplicate: bool = False) -> ApplicationOut:
    payload = a.payload if isinstance(a.payload, dict) else {}
    return ApplicationOut(
        application_id=a.application_code,
        status=a.status,
        product_code=a.product_code,
        created_at=a.created_at,
        ai_score=payload.get("ai_score"),
        decision_reason=payload.get("decision_reason"),
        assigned_limit=payload.get("assigned_limit"),
        is_duplicate=is_duplicate,
        mode=payload.get("mode", "ONLINE"),
    )


def calculate_credit_limit(product_code: str, monthly_income: float | None, requested_amount: float | None, prob: float) -> float:
    """Tính hạn mức đề xuất dựa trên điểm AI và thu nhập (áp dụng khi phê duyệt sơ bộ)."""
    income = float(monthly_income or 15_000_000)
    if product_code == "CREDIT_CARD":
        multiplier = 3.0 if prob >= 0.7 else 2.0
        return min(round(income * multiplier, -6), 150_000_000)
    elif product_code == "CONSUMER_LOAN":
        max_possible = income * 5.0
        req = float(requested_amount or 50_000_000)
        return min(req, max_possible, 100_000_000)
    elif product_code == "TERM_DEPOSIT":
        return float(requested_amount or 20_000_000)
    return 10_000_000.0


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def submit_application(
    body: ApplicationIn,
    response: Response,
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    idempotency_key_alt: str | None = Header(None, alias="Idempotency-Key"),
    simulate_failure: str | None = Query(None, description="Mô phỏng sự cố: 'ai_error' hoặc 'db_error'"),
    db: Session = Depends(get_db),
    current: str = Depends(get_current_customer),
    engine: VIBRecommendationEngine = Depends(get_engine),
):
    """
    Quy trình Đăng ký từ xa giải quyết cả 2 kịch bản:
      1. KHÔNG CÓ SỰ CỐ (Happy path): Thẩm định tức thì bằng AI XGBoost -> Tự động phê duyệt sơ bộ (PRE_APPROVED).
      2. CÓ SỰ CỐ (Incidents & Resilience):
         - Mạng lag/Double click: Idempotency Pattern chống gửi đơn trùng lặp.
         - AI Service lỗi/treo: Circuit Breaker kích hoạt Rule-based Fallback (dựa trên thu nhập).
         - Database lỗi/crash: Outbox Buffer tạm lưu và trả mã QUEUED_OFFLINE (HTTP 202) không làm mất đơn.
    """
    if body.product_code not in PRODUCTS_BY_CODE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sản phẩm không tồn tại")

    idem_key = x_idempotency_key or idempotency_key_alt or body.idempotency_key

    # --------------------------------------------------------------------------
    # SỰ CỐ 1: CHỐNG TRÙNG LẶP DO MẠNG LAG / CLIENT RETRY (IDEMPOTENCY PATTERN)
    # --------------------------------------------------------------------------
    if idem_key:
        recent_apps = db.scalars(
            select(Application)
            .where(Application.customer_number == current)
            .order_by(Application.created_at.desc())
            .limit(20)
        ).all()
        for app_item in recent_apps:
            p = app_item.payload if isinstance(app_item.payload, dict) else {}
            if p.get("idempotency_key") == idem_key:
                logger.info("Phát hiện request trùng lặp (Idempotency Key=%s). Trả kết quả cũ.", idem_key)
                response.status_code = status.HTTP_200_OK
                return to_out(app_item, is_duplicate=True)

    # --------------------------------------------------------------------------
    # TẦNG 2: THẨM ĐỊNH AI THỜI GIAN THỰC & SỰ CỐ AI (CIRCUIT BREAKER / FALLBACK)
    # --------------------------------------------------------------------------
    ai_score: float | None = None
    assigned_limit: float | None = None
    decision_reason: str = ""
    status_val: str = "SUBMITTED"
    mode_val: str = "ONLINE"

    target_mapping = {
        "CREDIT_CARD": "target_creditcard",
        "CONSUMER_LOAN": "target_loan",
        "TERM_DEPOSIT": "target_term_deposit",
    }
    target_key = target_mapping.get(body.product_code)

    try:
        # Kiểm tra mô phỏng sự cố AI (để kiểm thử kịch bản có sự cố)
        if simulate_failure == "ai_error" or SIMULATED_CHAOS_MODE.get("ai_down", False):
            raise RuntimeError("SIMULATED_AI_TIMEOUT: Dịch vụ suy luận mô hình XGBoost bị quá tải / timeout.")

        # Lấy đặc trưng khách hàng trực tiếp từ DB
        row = db.execute(text("SELECT features FROM customer_features WHERE customer_number = :c"), {"c": current}).fetchone()
        features = {}
        if row and row[0]:
            features = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        features["CUSTOMER_NUMBER"] = current

        prediction = engine.predict_single(features)
        rec_item = next((r for r in prediction["recommendations"] if r["target_key"] == target_key), None)
        if rec_item:
            ai_score = float(rec_item["score"])
        else:
            ai_score = float(prediction["top_product"]["score"])

        # Quyết định phê duyệt tự động dựa trên ngưỡng điểm AI
        if ai_score >= 0.5:
            status_val = "PRE_APPROVED"
            assigned_limit = calculate_credit_limit(body.product_code, body.monthly_income, body.amount, ai_score)
            decision_reason = f"AI phê duyệt tức thì: Điểm tín nhiệm cao ({ai_score*100:.1f}%), đủ điều kiện cấp hạn mức tự động."
        else:
            status_val = "PENDING_REVIEW"
            decision_reason = f"Điểm tín nhiệm sơ bộ ({ai_score*100:.1f}%), hồ sơ được chuyển sang chuyên viên VIB liên hệ thẩm định chi tiết."
        mode_val = "ONLINE"

    except Exception as ai_exc:
        # SỰ CỐ 2: AI SERVICE CRASH/TIMEOUT -> KÍCH HOẠT RULE-BASED FALLBACK
        logger.warning("AI Engine gặp sự cố (%s). Kích hoạt Circuit Breaker & Rule-based Fallback.", ai_exc)
        mode_val = "FALLBACK_RULE_BASED"
        ai_score = None
        income = float(body.monthly_income or 0)

        # Fallback theo quy tắc nghiệp vụ: Thu nhập >= 15 triệu -> Duyệt sơ bộ
        if income >= 15_000_000:
            status_val = "PRE_APPROVED"
            assigned_limit = min(income * 2.0, 100_000_000)
            decision_reason = f"⚡ Áp dụng cơ chế dự phòng (Rule-based Fallback khi AI gián đoạn): Phê duyệt sơ bộ dựa trên thu nhập ({income:,.0f} VND)."
        else:
            status_val = "PENDING_REVIEW"
            assigned_limit = None
            decision_reason = "⚡ Áp dụng cơ chế dự phòng: Hồ sơ được tiếp nhận và chuyển tiếp an toàn sang kênh thẩm định thủ công."

    # --------------------------------------------------------------------------
    # TẦNG 3: LƯU TRỮ POSTGRESQL & SỰ CỐ CƠ SỞ DỮ LIỆU (OUTBOX BUFFER RESILIENCE)
    # --------------------------------------------------------------------------
    payload_data = {
        **body.model_dump(mode="json", exclude={"product_code"}),
        "idempotency_key": idem_key,
        "ai_score": ai_score,
        "assigned_limit": assigned_limit,
        "decision_reason": decision_reason,
        "mode": mode_val,
    }
    app_code = f"APP-{secrets.token_hex(3).upper()}"

    try:
        # Kiểm tra mô phỏng sự cố Database (để kiểm thử kịch bản có sự cố)
        if simulate_failure == "db_error" or is_chaos_db_down():
            raise RuntimeError("SIMULATED_DATABASE_FAILURE: Mất kết nối tới cụm PostgreSQL StatefulSet.")

        app = Application(
            application_code=app_code,
            customer_number=current,
            product_code=body.product_code,
            status=status_val,
            payload=payload_data,
        )
        db.add(app)
        db.commit()
        db.refresh(app)
        return to_out(app, is_duplicate=False)

    except Exception as db_exc:
        # SỰ CỐ 3: DATABASE CRASH/FAILOVER -> GHI VÀO LOCAL OUTBOX BUFFER
        db.rollback()
        offline_code = f"APP-OFFLINE-{secrets.token_hex(3).upper()}"
        outbox_payload = {
            "application_code": offline_code,
            "customer_number": current,
            "product_code": body.product_code,
            "status": "QUEUED_OFFLINE",
            "payload": payload_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        buffer_file = OUTBOX_DIR / f"{offline_code}.json"
        buffer_file.write_text(json.dumps(outbox_payload, ensure_ascii=False), encoding="utf-8")
        logger.error("Database không phản hồi (%s). Đã lưu đơn an toàn vào Outbox: %s", db_exc, buffer_file)

        response.status_code = status.HTTP_202_ACCEPTED
        fake_app = Application(
            application_code=offline_code,
            customer_number=current,
            product_code=body.product_code,
            status="QUEUED_OFFLINE",
            payload={
                **payload_data,
                "mode": "FALLBACK_OUTBOX",
                "decision_reason": "⚡ Áp dụng cơ chế dự phòng Outbox (Cơ sở dữ liệu đang bảo trì/failover): Đơn đăng ký đã lưu vào bộ đệm an toàn và sẽ tự động đồng bộ khi DB online.",
            },
            created_at=datetime.now(timezone.utc),
        )
        return to_out(fake_app, is_duplicate=False)


@router.get("", response_model=list[ApplicationOut])
def my_applications(db: Session = Depends(get_db), current: str = Depends(get_current_customer)):
    """Lấy danh sách các hồ sơ đăng ký của khách hàng hiện tại."""
    rows = db.scalars(
        select(Application).where(Application.customer_number == current).order_by(Application.created_at.desc())
    ).all()
    return [to_out(a) for a in rows]


@router.post("/sync-outbox")
def sync_outbox():
    """Worker đồng bộ các hồ sơ từ Outbox Buffer vào PostgreSQL khi kết nối được khôi phục."""
    synced, errors = flush_local_outbox()
    return {
        "message": f"Đã đồng bộ {len(synced)} hồ sơ vào cơ sở dữ liệu.",
        "synced": synced,
        "errors": errors,
    }

