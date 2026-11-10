#!/usr/bin/env python3
"""
Kịch bản tự động thực nghiệm Self-healing & Zero-Downtime cho buổi Demo:
1. Gửi request liên tục vào ứng dụng qua Ingress.
2. Xóa 1 Pod Backend đang chạy (simulate pod crash).
3. Đo thời gian hồi sinh (Recovery Time Objective - RTO) và xác nhận 0 request bị gián đoạn.
"""
import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request


def get_backend_pods():
    try:
        out = subprocess.check_output(
            ["kubectl", "get", "pods", "-n", "vib-banking", "-l", "app=backend-api", "-o", "jsonpath={.items[*].metadata.name}"],
            text=True,
        )
        return out.strip().split()
    except Exception as e:
        return []


def is_pod_ready(pod_name):
    try:
        out = subprocess.check_output(
            ["kubectl", "get", "pod", pod_name, "-n", "vib-banking", "-o", "jsonpath={.status.containerStatuses[0].ready}"],
            text=True,
        ).strip()
        return out == "true"
    except Exception:
        return False


def monitor_traffic(stop_event, stats):
    token = ""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1/api/auth/login",
            data=json.dumps({"customer_number": "00992830", "password": "123456"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            token = json.loads(r.read().decode()).get("access_token", "")
    except Exception:
        pass

    target = "http://127.0.0.1/api/recommendations/00992830"
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    while not stop_event.is_set():
        stats["total"] += 1
        try:
            r = urllib.request.Request(target, headers=headers)
            with urllib.request.urlopen(r, timeout=3) as resp:
                if resp.status == 200:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
        except Exception:
            stats["failed"] += 1
        time.sleep(0.4)


def main():
    print("=" * 65)
    print("  THỰC NGHIỆM KHẢ NĂNG TỰ PHỤC HỒI (SELF-HEALING) & ZERO-DOWNTIME")
    print("=" * 65)

    initial_pods = get_backend_pods()
    if not initial_pods:
        print("Không tìm thấy pod backend nào đang chạy trong namespace vib-banking!")
        sys.exit(1)

    victim_pod = initial_pods[0]
    initial_set = set(initial_pods)
    print(f"[*] Danh sách Pods Backend ban đầu: {', '.join(initial_pods)}")
    print(f"[*] Pod sẽ bị xóa để mô phỏng sự cố: {victim_pod}")
    print("[*] Đang khởi động luồng traffic kiểm tra tính sẵn sàng liên tục...")

    stats = {"total": 0, "success": 0, "failed": 0}
    stop_event = threading.Event()
    t = threading.Thread(target=monitor_traffic, args=(stop_event, stats), daemon=True)
    t.start()

    time.sleep(2.0)
    print(f"\n[!] BẮT ĐẦU XÓA POD: kubectl delete pod {victim_pod} -n vib-banking ...")
    t0 = time.perf_counter()
    subprocess.call(["kubectl", "delete", "pod", victim_pod, "-n", "vib-banking", "--wait=false"])

    print("[*] Đang giám sát quá trình K8s tự động khởi tạo Pod thay thế...")
    new_pod_name = ""
    new_pod_ready = False

    while time.perf_counter() - t0 < 60:
        time.sleep(1.0)
        current_pods = set(get_backend_pods())
        new_candidates = list(current_pods - initial_set)
        if new_candidates:
            new_pod_name = new_candidates[0]
            if is_pod_ready(new_pod_name):
                new_pod_ready = True
                break

        elapsed = time.perf_counter() - t0
        sys.stdout.write(f"\r  Đang theo dõi... Thời gian: {elapsed:4.1f}s | Pod mới: {new_pod_name or 'Đang tạo...'} | Requests 200 OK: {stats['success']} | Lỗi: {stats['failed']}")
        sys.stdout.flush()

    stop_event.set()
    t.join(timeout=1.0)
    rto = time.perf_counter() - t0

    print("\n\n" + "=" * 65)
    print("                KẾT QUẢ THỰC NGHIỆM SELF-HEALING")
    print("=" * 65)
    if new_pod_ready:
        print(f"  [PASS] Pod mới ({new_pod_name}) đã khởi tạo, nạp model và đạt 1/1 Ready!")
        print(f"  * Thời gian phục hồi (RTO):              {rto:.2f} giây")
    else:
        print(f"  [WARN] Pod mới ({new_pod_name}) chưa kịp Ready sau {rto:.2f}s")

    print(f"  * Tổng số request trong lúc xảy ra sự cố: {stats['total']}")
    print(f"  * Số request thành công (200 OK):         {stats['success']} ({stats['success']/max(stats['total'],1)*100:.1f}%)")
    print(f"  * Số request bị gián đoạn (Lỗi):          {stats['failed']} ({stats['failed']/max(stats['total'],1)*100:.1f}%)")
    print("-" * 65)
    if stats["failed"] == 0:
        print("  KẾT LUẬN: Trong lúc pod bị xoá, mọi request đều thành công (0% lỗi): Ingress chuyển")
        print("            request sang pod còn lại cho tới khi pod mới Ready.")
    else:
        print(f"  KẾT LUẬN: Có {stats['failed']} request lỗi trong lúc pod bị xoá (xem số liệu ở trên).")
        print("            Ghi đúng số này khi báo cáo, không làm tròn thành 0%.")
    print("=================================================================\n")


if __name__ == "__main__":
    main()
