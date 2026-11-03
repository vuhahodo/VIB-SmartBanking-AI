#!/usr/bin/env python3
"""
VIB-SmartBanking Load Testing & HPA Verification Tool
=====================================================
Kịch bản kiểm thử chịu tải để kích hoạt Horizontal Pod Autoscaler (HPA 2 -> 8 pods)
và đo đạc số liệu hiệu năng thực tế (RPS, Latency percentiles p50/p90/p95/p99) cho Slide 10.

Không cần cài thêm thư viện (chỉ dùng thư viện chuẩn của Python: urllib, threading, json, time).

Cách dùng:
  python scripts/load_test.py --url http://172.17.242.190 --duration 60 --concurrency 30
  python scripts/load_test.py --url http://localhost:8000 --duration 30 --concurrency 20
"""

import argparse
import json
import math
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import List, Tuple


class LoadTester:
    def __init__(
        self,
        base_url: str,
        customer_id: str = "00992830",
        password: str = "123456",
        concurrency: int = 30,
        duration: int = 60,
        endpoint: str | None = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.customer_id = customer_id
        self.password = password
        self.concurrency = concurrency
        self.duration = duration
        self.timeout = timeout
        self.endpoint = endpoint or f"/api/recommendations/{self.customer_id}"
        self.token = ""

        # Kết quả đo đạc
        self.latencies: List[float] = []  # millisecond
        self.status_codes: dict[int, int] = {}
        self.errors: List[str] = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

    def check_health(self) -> bool:
        """Kiểm tra backend có phản hồi không."""
        urls = [f"{self.base_url}/ready", f"{self.base_url}/health", f"{self.base_url}/api/health"]
        for u in urls:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "VIB-LoadTester/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        print(f"  [OK] Endpoint kiem tra suc khoe: {u} (HTTP {resp.status})")
                        return True
            except Exception:
                continue
        print(f"  [CANH BAO] Khong the ket noi cac endpoint health tren {self.base_url}")
        return False

    def login(self) -> str:
        """Dang nhap vao he thong de lay JWT Bearer token."""
        login_url = f"{self.base_url}/api/auth/login"
        payload = json.dumps({"customer_number": self.customer_id, "password": self.password}).encode("utf-8")
        req = urllib.request.Request(
            login_url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "VIB-LoadTester/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                token = data.get("access_token", "")
                if token:
                    print(f"  [OK] Dang nhap thanh cong voi ma KH {self.customer_id}. Lay duoc JWT token.")
                    return token
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            print(f"  [LOI] Dang nhap that bai (HTTP {e.code}): {err_msg}")
        except Exception as e:
            print(f"  [LOI] Loi ket noi khi dang nhap: {e}")
        return ""

    def _worker(self, target_url: str, headers: dict):
        """Worker gui request lien tuc trong khoang thoi gian duration."""
        while not self.stop_event.is_set():
            start_time = time.perf_counter()
            try:
                req = urllib.request.Request(target_url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    code = resp.status
                    _ = resp.read()  # Doc het response
            except urllib.error.HTTPError as e:
                code = e.code
            except Exception as e:
                code = 0  # Network timeout / connection error
                with self.lock:
                    if len(self.errors) < 10:
                        self.errors.append(str(e))

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            with self.lock:
                self.latencies.append(latency_ms)
                self.status_codes[code] = self.status_codes.get(code, 0) + 1

    def run(self):
        print("\n" + "=" * 65)
        print("    VIB-SMARTBANKING: BAT DAU KIEM THU TAI TRONG & HPA")
        print("=" * 65)
        print(f"Target Base URL:   {self.base_url}")
        print(f"Target Endpoint:   {self.endpoint}")
        print(f"Concurrency:       {self.concurrency} concurrent threads")
        print(f"Test Duration:     {self.duration} giay")
        print(f"Customer Number:   {self.customer_id}")
        print("-" * 65)

        # 1. Health check
        self.check_health()

        # 2. Login
        self.token = self.login()
        if not self.token:
            print("  [LOI] Khong the tiep tuc neu khong co Token xac thuc.")
            sys.exit(1)

        target_url = f"{self.base_url}{self.endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "VIB-LoadTester/1.0",
        }

        print("\n>> Dang khoi tao cac luong tai... Vui long theo doi Terminal HPA:")
        print("   kubectl get hpa -n vib-banking -w")
        print("   kubectl get pods -n vib-banking -w\n")

        # 3. Khoi tao threads
        threads = []
        for _ in range(self.concurrency):
            t = threading.Thread(target=self._worker, args=(target_url, headers), daemon=True)
            threads.append(t)

        start_time = time.perf_counter()
        for t in threads:
            t.start()

        # 4. Vong lap in tien do truc quan
        try:
            while True:
                elapsed = time.perf_counter() - start_time
                if elapsed >= self.duration:
                    break
                time.sleep(1.0)
                with self.lock:
                    total_req = len(self.latencies)
                    success_req = self.status_codes.get(200, 0)
                    cur_rps = total_req / max(elapsed, 0.1)
                    succ_pct = (success_req / total_req * 100) if total_req > 0 else 0
                    recent_lat = self.latencies[-10:] if self.latencies else [0]
                    avg_lat = sum(recent_lat) / len(recent_lat)

                sys.stdout.write(
                    f"\r[{int(elapsed):02d}s/{self.duration:02d}s] "
                    f"Tong Req: {total_req:<6} | RPS: {cur_rps:6.1f} | "
                    f"200 OK: {succ_pct:5.1f}% | Latency gan nhat: {avg_lat:5.1f} ms"
                )
                sys.stdout.flush()
        except KeyboardInterrupt:
            print("\n\n[DUNG] Nguoi dung yeu cau dung dot kiem thu (Ctrl+C).")
        finally:
            self.stop_event.set()
            for t in threads:
                t.join(timeout=1.0)

        total_time = time.perf_counter() - start_time
        print(f"\n\nHoan thanh dot test sau {total_time:.2f} giay.")
        self.report(total_time)

    def report(self, total_time: float):
        """In bao cao chi tiet cac chi so hieu nang."""
        if not self.latencies:
            print("Khong co du lieu request nao duoc ghi nhan.")
            return

        sorted_lat = sorted(self.latencies)
        n = len(sorted_lat)
        total_req = n
        success_req = self.status_codes.get(200, 0)
        failed_req = total_req - success_req
        rps = total_req / max(total_time, 0.001)

        def percentile(p: float) -> float:
            k = (n - 1) * (p / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_lat[int(k)]
            d0 = sorted_lat[int(f)] * (c - k)
            d1 = sorted_lat[int(c)] * (k - f)
            return d0 + d1

        min_lat = sorted_lat[0]
        p50 = percentile(50)
        p90 = percentile(90)
        p95 = percentile(95)
        p99 = percentile(99)
        max_lat = sorted_lat[-1]
        mean_lat = sum(sorted_lat) / n

        print("\n" + "=" * 65)
        print("              KET QUA DO DAC HIEN NANG THUC TE")
        print("=" * 65)
        print(f"Tong so requests:        {total_req:,}")
        print(f"Thanh cong (HTTP 200):   {success_req:,} ({success_req/total_req*100:.2f}%)")
        print(f"That bai / Loi:          {failed_req:,} ({failed_req/total_req*100:.2f}%)")
        print(f"Thoi gian do:            {total_time:.2f} s")
        print(f"Throughput (RPS):        {rps:.2f} requests/s")
        print("-" * 65)
        print("Phan vi do tre (Latency Percentiles):")
        print(f"  * Min Latency:         {min_lat:7.2f} ms")
        print(f"  * p50 (Median):        {p50:7.2f} ms")
        print(f"  * p90:                 {p90:7.2f} ms")
        print(f"  * p95:                 {p95:7.2f} ms")
        print(f"  * p99:                 {p99:7.2f} ms")
        print(f"  * Max Latency:         {max_lat:7.2f} ms")
        print(f"  * Trung binh (Mean):   {mean_lat:7.2f} ms")
        print("-" * 65)
        print("Phan bo ma trang thai HTTP:")
        for code, count in sorted(self.status_codes.items()):
            label = "HTTP " + str(code) if code > 0 else "Network Timeout/Error"
            print(f"  {label:<22}: {count:>6} ({count/total_req*100:5.1f}%)")

        if self.errors:
            print("-" * 65)
            print("Cac loi tieu bieu gap phai:")
            for e in self.errors[:5]:
                print(f"  - {e}")

        print("=" * 65)
        print("\n[!] DU LIEU DE DIEN VAO SLIDE 10 VA PRESENTATION_PLAN.md:")
        print("```markdown")
        print("| Chi so                  | Gia tri do duoc |")
        print("|-------------------------|-----------------|")
        print(f"| RPS (Requests/giay)     | {rps:.1f} req/s     |")
        print(f"| Latency p50 (trung vi)  | {p50:.1f} ms        |")
        print(f"| Latency p95             | {p95:.1f} ms        |")
        print(f"| Latency p99             | {p99:.1f} ms        |")
        print(f"| Ti le thanh cong (200)  | {success_req/total_req*100:.1f}%          |")
        print(f"| So replicas quan sat    | [Ghi tu kubectl get hpa] |")
        print("```")
        print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Cong cu do tai va kich hoat HPA VIB-SmartBanking")
    parser.add_argument("--url", "-u", default="http://localhost", help="Base URL cua ingress hoac backend (mac dinh: http://localhost)")
    parser.add_argument("--customer", "-c", default="00992830", help="Ma khach hang demo (mac dinh: 00992830)")
    parser.add_argument("--password", "-p", default="123456", help="Mat khau dang nhap (mac dinh: 123456)")
    parser.add_argument("--concurrency", "-n", type=int, default=30, help="So luong thread dong thoi (mac dinh: 30)")
    parser.add_argument("--duration", "-d", type=int, default=60, help="Thoi gian tao tai tinh bang giay (mac dinh: 60)")
    parser.add_argument("--endpoint", "-e", default="", help="Endpoint tuy chon de test tai (mac dinh: /api/recommendations/<customer_id>)")
    parser.add_argument("--timeout", "-t", type=float, default=10.0, help="Timeout moi request (mac dinh: 10.0)")

    args = parser.parse_args()
    tester = LoadTester(
        base_url=args.url,
        customer_id=args.customer,
        password=args.password,
        concurrency=args.concurrency,
        duration=args.duration,
        endpoint=args.endpoint or None,
        timeout=args.timeout,
    )
    tester.run()


if __name__ == "__main__":
    main()

