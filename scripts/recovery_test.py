#!/usr/bin/env python3
"""
Đo khả năng tự phục hồi: xoá một pod backend và đo
  - thời gian từ lúc xoá tới khi Deployment có đủ replica Ready trở lại,
  - số request thất bại trong lúc đó (gọi liên tục API gợi ý qua Ingress).

In bảng Markdown để điền vào ô [SỐ ĐO] ở slide kết quả.

Cách dùng:
  python scripts/recovery_test.py --url http://<node-ip>
  python scripts/recovery_test.py --dry-run          # chỉ in kế hoạch, không chạy kubectl/HTTP

Yêu cầu: kubectl trỏ tới đúng cụm; chỉ dùng thư viện chuẩn của Python.
"""
import argparse
import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request


def kubectl(*args, timeout=30):
    r = subprocess.run(["kubectl", *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def login(base, customer, password):
    req = urllib.request.Request(
        base + "/api/auth/login",
        data=json.dumps({"customer_number": customer, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["access_token"]


class Poller(threading.Thread):
    """Gọi API liên tục, ghi lại mã trạng thái và độ trễ."""

    def __init__(self, url, token, interval):
        super().__init__(daemon=True)
        self.url, self.token, self.interval = url, token, interval
        self.stop = threading.Event()
        self.results = []  # (thời điểm, mã trạng thái, ms)

    def run(self):
        while not self.stop.is_set():
            t0 = time.time()
            code = 0
            try:
                req = urllib.request.Request(self.url, headers={"Authorization": "Bearer " + self.token})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    code = resp.status
            except urllib.error.HTTPError as e:
                code = e.code
            except Exception:
                code = 0
            self.results.append((t0, code, (time.time() - t0) * 1000))
            time.sleep(self.interval)


def ready_state(ns, deploy):
    rc, out, err = kubectl("get", "deploy", deploy, "-n", ns, "-o", "jsonpath={.status.readyReplicas}/{.spec.replicas}")
    if rc != 0:
        raise RuntimeError(err or "kubectl lỗi")
    ready, _, want = out.partition("/")
    return int(ready or 0), int(want or 0)


def main():
    p = argparse.ArgumentParser(description="Đo thời gian tự phục hồi sau khi xoá một pod")
    p.add_argument("--url", default="http://localhost", help="Địa chỉ Ingress, ví dụ http://<node-ip>")
    p.add_argument("--namespace", default="vib-banking")
    p.add_argument("--deployment", default="backend-api")
    p.add_argument("--label", default="app=backend-api")
    p.add_argument("--customer", default="00992830")
    p.add_argument("--password", default="123456")
    p.add_argument("--interval", type=float, default=0.2, help="Giây giữa hai request (mặc định 0.2)")
    p.add_argument("--timeout", type=int, default=180, help="Chờ tối đa bao nhiêu giây (mặc định 180)")
    p.add_argument("--dry-run", action="store_true", help="Chỉ in kế hoạch")
    a = p.parse_args()

    base = a.url.rstrip("/")
    endpoint = f"{base}/api/recommendations/{a.customer}"
    print("Kế hoạch:")
    print(f"  1. Đăng nhập {a.customer} tại {base}")
    print(f"  2. Chọn 1 pod của deployment/{a.deployment} (nhãn {a.label}) trong namespace {a.namespace}")
    print(f"  3. Gọi liên tục {endpoint} mỗi {a.interval}s")
    print("  4. kubectl delete pod <pod đã chọn>, đo thời gian tới khi đủ replica Ready")
    print("  5. In bảng kết quả (Markdown)")
    if a.dry_run:
        return 0

    rc, out, err = kubectl("get", "pods", "-n", a.namespace, "-l", a.label, "--field-selector=status.phase=Running",
                           "-o", "jsonpath={.items[*].metadata.name}")
    if rc != 0:
        print("Lỗi: không chạy được kubectl:", err or "không rõ nguyên nhân")
        return 1
    pods = out.split()
    if not pods:
        print("Lỗi: không có pod Running nào khớp nhãn", a.label)
        return 1
    try:
        _, want = ready_state(a.namespace, a.deployment)
        token = login(base, a.customer, a.password)
    except Exception as e:
        print("Lỗi khi chuẩn bị (kiểm tra --url và cụm):", e)
        return 1

    victim = pods[0]
    print(f"\nĐang có {len(pods)} pod; số replica mong muốn: {want}. Pod sẽ xoá: {victim}")
    poller = Poller(endpoint, token, a.interval)
    poller.start()
    time.sleep(2)  # lấy vài mẫu trước khi xoá

    t_delete = time.time()
    rc, _, err = kubectl("delete", "pod", victim, "-n", a.namespace, "--wait=false")
    if rc != 0:
        poller.stop.set()
        print("Lỗi khi xoá pod:", err)
        return 1

    # Giai đoạn 1: chờ quan sát số pod Ready giảm; giai đoạn 2: chờ hồi phục đủ số replica.
    dipped, recovered_at, deadline = False, None, t_delete + a.timeout
    while time.time() < deadline:
        try:
            ready, want_now = ready_state(a.namespace, a.deployment)
        except Exception:
            time.sleep(0.5)
            continue
        if ready < want_now:
            dipped = True
        if (dipped or time.time() - t_delete > 15) and ready >= want_now:
            recovered_at = time.time()
            break
        time.sleep(0.5)

    time.sleep(3)  # lấy thêm vài mẫu sau khi hồi phục
    poller.stop.set()
    poller.join(timeout=6)

    window = [r for r in poller.results if r[0] >= t_delete - 0.001 and (recovered_at is None or r[0] <= recovered_at + 3)]
    total = len(window)
    errors = sum(1 for r in window if r[1] != 200)
    lat = sorted(r[2] for r in window if r[1] == 200)
    worst = f"{lat[-1]:.0f} ms" if lat else "n/a"

    print("\n=== KẾT QUẢ TỰ PHỤC HỒI (dán vào slide kết quả) ===")
    print("```")
    print("| Chỉ số                                  | Giá trị |")
    print("|-----------------------------------------|---------|")
    print(f"| Pod bị xoá                              | {victim} |")
    if recovered_at:
        note = "" if dipped else " (không bắt được lúc giảm, số này chỉ mang tính tham khảo)"
        print(f"| Thời gian tới khi đủ replica Ready (s)  | {recovered_at - t_delete:.1f}{note} |")
    else:
        print(f"| Thời gian tới khi đủ replica Ready (s)  | quá {a.timeout} s, chưa hồi phục |")
    print(f"| Số request trong lúc xảy ra sự cố       | {total} |")
    print(f"| Số request thất bại                     | {errors} |")
    if total:
        print(f"| Tỉ lệ thành công                        | {(total - errors) / total * 100:.1f}% |")
    print(f"| Độ trễ lớn nhất của request thành công  | {worst} |")
    print("```")
    return 0 if recovered_at else 2


if __name__ == "__main__":
    sys.exit(main())
