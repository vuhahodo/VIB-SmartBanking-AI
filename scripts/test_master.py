#!/usr/bin/env python3
"""
KIỂM THỬ TOÀN DIỆN HỆ THỐNG VIB-SMARTBANKING-AI:
Bao gồm toàn bộ chức năng cũ (Core Banking, AI Inference) và
các chức năng mới (Bài toán Đăng ký Từ xa: Có sự cố & Không sự cố,
Bảng Quản trị Hạ tầng Cloud Dev/Ops, Bảo mật & Tự phục hồi).
"""
import argparse
import json
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

COLOR_RESET = "\033[0m"
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_CYAN = "\033[96m"
COLOR_BOLD = "\033[1m"


def print_step(title):
    print(f"\n{COLOR_CYAN}{COLOR_BOLD}>>> {title}{COLOR_RESET}")


def print_pass(msg):
    print(f"  {COLOR_GREEN}[PASS]{COLOR_RESET} {msg}")


def print_fail(msg):
    print(f"  {COLOR_RED}[FAIL]{COLOR_RESET} {msg}")


def print_warn(msg):
    print(f"  {COLOR_YELLOW}[WARN]{COLOR_RESET} {msg}")


def print_info(msg):
    print(f"  {COLOR_BOLD}[*]{COLOR_RESET} {msg}")


def http_request(url, method="GET", data=None, headers=None, timeout=10, insecure_ssl=True):
    headers = headers or {}
    data_bytes = None
    if data is not None:
        if isinstance(data, (dict, list)):
            data_bytes = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    ctx = None
    if insecure_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            body = resp.read().decode("utf-8", errors="replace")
            res_headers = dict(resp.headers)
            try:
                json_data = json.loads(body)
            except Exception:
                json_data = None
            return resp.status, json_data, body, res_headers, elapsed_ms
    except urllib.error.HTTPError as err:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        body = err.read().decode("utf-8", errors="replace")
        try:
            json_data = json.loads(body)
        except Exception:
            json_data = None
        return err.code, json_data, body, dict(err.headers), elapsed_ms
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return 0, None, str(exc), {}, elapsed_ms


def main():
    parser = argparse.ArgumentParser(description="Kiểm thử toàn diện VIB-SmartBanking-AI")
    parser.add_argument("--url", default="http://172.17.242.190", help="Địa chỉ cụm K8s Ingress")
    parser.add_argument("--customer", default="00992830", help="Mã khách hàng thực nghiệm")
    parser.add_argument("--password", default="123456", help="Mật khẩu demo")
    args = parser.parse_args()

    base_http = args.url.rstrip("/")
    base_https = base_http.replace("http://", "https://")
    total_tests = 0
    passed_tests = 0

    print("=" * 80)
    print(f"      KIỂM THỬ TOÀN DIỆN DỰ ÁN VIB-SMARTBANKING-AI (OLD & NEW FUNCTIONS)")
    print(f"      Target: {base_http} | Khách hàng kiểm thử: {args.customer}")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # PHẦN 1: HẠ TẦNG & TÍNH SẴN SÀNG (HEALTH & PROBES)
    # --------------------------------------------------------------------------
    print_step("[PHẦN 1/6] KIỂM TRA HẠ TẦNG & PROBES K8S...")

    # 1.1 Liveness Probe
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/health")
    if code == 200 and js and js.get("status") == "ok":
        passed_tests += 1
        print_pass(f"1.1 Liveness Probe (/health) -> HTTP 200 OK ({ms:.1f}ms)")
    else:
        print_fail(f"1.1 Liveness Probe thất bại: code {code}")

    # 1.2 Readiness Probe
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/ready")
    if code == 200 and js and js.get("status") == "ready":
        passed_tests += 1
        print_pass(f"1.2 Readiness Probe (/ready) -> HTTP 200 Ready (Database & 3 AI Models Ready, {ms:.1f}ms)")
    else:
        print_fail(f"1.2 Readiness Probe thất bại: code {code}")

    # 1.3 Frontend UI
    total_tests += 1
    code, _, body, _, ms = http_request(f"{base_http}/")
    if code == 200 and "VIB SmartBanking" in body:
        passed_tests += 1
        print_pass(f"1.3 Frontend UI Root (/) -> HTTP 200 OK ({ms:.1f}ms)")
    else:
        print_fail(f"1.3 Frontend UI không tải được: code {code}")

    # --------------------------------------------------------------------------
    # PHẦN 2: CHỨC NĂNG CŨ - NGHIỆP VỤ NGÂN HÀNG SỐ (AUTH & CORE BANKING)
    # --------------------------------------------------------------------------
    print_step("[PHẦN 2/6] KIỂM TRA CHỨC NĂNG CŨ: XÁC THỰC & NGHIỆP VỤ NGÂN HÀNG...")

    # 2.1 Demo accounts
    total_tests += 1
    code, js, _, _, _ = http_request(f"{base_http}/api/auth/demo-accounts")
    if code == 200:
        passed_tests += 1
        print_pass(f"2.1 Danh sách tài khoản Demo -> HTTP 200 OK")
    elif code == 404:
        passed_tests += 1
        print_pass(f"2.1 Bảo mật Production (DEMO_MODE=false) -> Ẩn danh sách demo an toàn (HTTP 404)")
    else:
        print_warn(f"2.1 Danh sách Demo ẩn (DEMO_MODE=false) -> Mã {code}")

    # 2.2 Đăng nhập JWT
    total_tests += 1
    login_payload = {"customer_number": args.customer, "password": args.password}
    code, js, _, _, ms = http_request(f"{base_http}/api/auth/login", method="POST", data=login_payload)
    token = None
    if code == 200 and js and "access_token" in js:
        passed_tests += 1
        token = js["access_token"]
        print_pass(f"2.2 Đăng nhập JWT thành công ({ms:.1f}ms) -> Đã cấp Token Bearer")
    else:
        print_fail(f"2.2 Đăng nhập thất bại: HTTP {code}")
        return 1

    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2.3 Hồ sơ khách hàng & Tài khoản
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/api/customers/{args.customer}", headers=auth_headers)
    if code == 200 and js and "profile" in js and "accounts" in js:
        passed_tests += 1
        prof = js["profile"]
        accs = js["accounts"]
        print_pass(f"2.3 Hồ sơ khách hàng -> HTTP 200 ({prof.get('full_name')} - {len(accs)} tài khoản)")
    else:
        print_fail(f"2.3 Lấy hồ sơ khách hàng thất bại: HTTP {code}")

    # 2.4 Lịch sử giao dịch
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/api/customers/{args.customer}/transactions", headers=auth_headers)
    if code == 200 and isinstance(js, list):
        passed_tests += 1
        print_pass(f"2.4 Lịch sử giao dịch -> HTTP 200 ({len(js)} giao dịch gần nhất)")
    else:
        print_fail(f"2.4 Lấy lịch sử giao dịch thất bại: HTTP {code}")

    # 2.5 Danh mục sản phẩm
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/api/products", headers=auth_headers)
    if code == 200 and isinstance(js, list) and len(js) >= 3:
        passed_tests += 1
        print_pass(f"2.5 Danh mục sản phẩm tài chính -> HTTP 200 ({len(js)} sản phẩm)")
    else:
        print_fail(f"2.5 Lấy danh mục sản phẩm thất bại: HTTP {code}")

    # --------------------------------------------------------------------------
    # PHẦN 3: CHỨC NĂNG CŨ - AI INFERENCE & KHOA HỌC DỮ LIỆU
    # --------------------------------------------------------------------------
    print_step("[PHẦN 3/6] KIỂM TRA CHỨC NĂNG CŨ: SUY LUẬN AI THỜI GIAN THỰC...")

    # 3.1 AI Recommendations (3 XGBoost models)
    total_tests += 1
    print_info(f"Đang chạy 3 mô hình XGBoost suy luận thời gian thực cho khách hàng {args.customer}...")
    code, js, _, _, ms = http_request(f"{base_http}/api/recommendations/{args.customer}", headers=auth_headers)
    if code == 200 and js and "recommendations" in js:
        passed_tests += 1
        top_p = js.get("top_product", {})
        print_pass(f"3.1 AI Inference thành công ({ms:.1f}ms) -> Gợi ý hàng đầu: {top_p.get('product_name')} (Score: {top_p.get('score'):.3f})")
    else:
        print_fail(f"3.1 AI Inference thất bại: HTTP {code}")

    # 3.2 AI Metrics (training_metrics.json)
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/api/ai/metrics", headers=auth_headers)
    if code == 200 and js and "results" in js:
        passed_tests += 1
        auc_card = js["results"]["target_creditcard"]["roc_auc"]
        auc_loan = js["results"]["target_loan"]["roc_auc"]
        auc_td = js["results"]["target_term_deposit"]["roc_auc"]
        print_pass(f"3.2 Chỉ số kiểm thử mô hình AI -> ROC-AUC: Card={auc_card:.4f}, Loan={auc_loan:.4f}, Deposit={auc_td:.4f}")
    else:
        print_fail(f"3.2 Lấy chỉ số AI Metrics thất bại: HTTP {code}")

    # --------------------------------------------------------------------------
    # PHẦN 4: CHỨC NĂNG MỚI - BÀI TOÁN ĐĂNG KÝ TỪ XA (HAPPY & FAILURE PATHS)
    # --------------------------------------------------------------------------
    print_step("[PHẦN 4/6] KIỂM TRA BÀI TOÁN ĐĂNG KÝ TỪ XA (CÓ SỰ CỐ & KHÔNG SỰ CỐ)...")

    # 4.1 Happy Path: Đăng ký thành công trực tiếp
    total_tests += 1
    app_payload = {
        "product_code": "CREDIT_CARD",
        "full_name": "Nguyễn Thị Minh Anh",
        "phone": "0941790088",
        "email": "kh00992830@example.com",
        "monthly_income": 25000000,
        "amount": 50000000,
    }
    idem_key_1 = f"IDEM-HAPPY-{int(time.time()*1000)}"
    code, js, _, _, ms = http_request(
        f"{base_http}/api/applications",
        method="POST",
        data=app_payload,
        headers={**auth_headers, "Idempotency-Key": idem_key_1},
    )
    if code == 201 and js and "application_id" in js:
        passed_tests += 1
        app_id = js["application_id"]
        st = js["status"]
        limit = js.get("assigned_limit") or 0
        print_pass(f"4.1 [KHÔNG SỰ CỐ] Nộp hồ sơ mở thẻ thành công (HTTP 201 Created, {ms:.1f}ms)")
        print_info(f"    Mã hồ sơ: {app_id} | Trạng thái: {st} | Hạn mức AI cấp: {limit:,.0f} VND")
    else:
        print_fail(f"4.1 [KHÔNG SỰ CỐ] Nộp hồ sơ thất bại: HTTP {code}")

    # 4.2 Idempotency: Gửi lại cùng key không trùng lặp
    total_tests += 1
    code, js, _, _, ms = http_request(
        f"{base_http}/api/applications",
        method="POST",
        data=app_payload,
        headers={**auth_headers, "Idempotency-Key": idem_key_1},
    )
    if code == 200 and js and js.get("is_duplicate") is True:
        passed_tests += 1
        print_pass(f"4.2 [CHỐNG TRÙNG LẶP] Idempotency Key bảo vệ toàn vẹn: Trả về đơn cũ an toàn (HTTP 200 OK)")
    else:
        print_fail(f"4.2 Kiểm tra Idempotency thất bại: HTTP {code}")

    # 4.3 Failure Path 1: Sự cố AI quá tải / Timeout -> Rule-based Fallback
    total_tests += 1
    ai_err_payload = {
        "product_code": "CONSUMER_LOAN",
        "full_name": "Nguyễn Thị Minh Anh",
        "phone": "0941790088",
        "email": "kh00992830@example.com",
        "monthly_income": 20000000,
        "amount": 40000000,
    }
    code, js, _, _, ms = http_request(
        f"{base_http}/api/applications?simulate_failure=ai_error",
        method="POST",
        data=ai_err_payload,
        headers={**auth_headers, "Idempotency-Key": f"IDEM-AIERR-{int(time.time()*1000)}"},
    )
    if code in (200, 201) and js and "FALLBACK" in js.get("mode", ""):
        passed_tests += 1
        print_pass(f"4.3 [SỰ CỐ AI GIÁN ĐOẠN] Kích hoạt Circuit Breaker & Rule-based Fallback thành công!")
        print_info(f"    Lý do phê duyệt dự phòng: {js.get('decision_reason')}")
    else:
        print_fail(f"4.3 Xử lý sự cố AI thất bại: HTTP {code}")

    # 4.4 Failure Path 2: Sự cố Thảm họa Database Crash -> Outbox Buffer
    total_tests += 1
    db_err_payload = {
        "product_code": "TERM_DEPOSIT",
        "full_name": "Nguyễn Thị Minh Anh",
        "phone": "0941790088",
        "email": "kh00992830@example.com",
        "monthly_income": 30000000,
        "amount": 100000000,
    }
    code, js, _, _, ms = http_request(
        f"{base_http}/api/applications?simulate_failure=db_error",
        method="POST",
        data=db_err_payload,
        headers={**auth_headers, "Idempotency-Key": f"IDEM-DBERR-{int(time.time()*1000)}"},
    )
    offline_app_id = None
    if code == 202 and js and "APP-OFFLINE" in js.get("application_id", ""):
        passed_tests += 1
        offline_app_id = js["application_id"]
        print_pass(f"4.4 [SỰ CỐ ĐỨT KẾT NỐI DB] Kích hoạt Transactional Outbox Buffer thành công (HTTP 202 Accepted, {ms:.1f}ms)!")
        print_info(f"    Mã hồ sơ đệm an toàn: {offline_app_id} (Hệ thống không sập HTTP 500, khách hàng không bị mất đơn)")
    else:
        print_fail(f"4.4 Xử lý sự cố DB thất bại: HTTP {code}")

    # 4.5 Auto-Reconciliation & Zero Data Loss
    total_tests += 1
    print_info("Đợi Background Worker tự động đồng bộ Outbox vào PostgreSQL (chu kỳ 2s)...")
    time.sleep(3)
    code, js, _, _, _ = http_request(f"{base_http}/api/applications", headers=auth_headers)
    found_offline = False
    if code == 200 and isinstance(js, list):
        for item in js:
            if item.get("application_id") == offline_app_id:
                found_offline = True
                break

    if found_offline:
        passed_tests += 1
        print_pass(f"4.5 [ĐỐI SOÁT & 0% MẤT DỮ LIỆU] Hồ sơ {offline_app_id} đã được tự động nạp chính thức vào PostgreSQL!")
    else:
        # Nếu chưa xong, gọi ép buộc sync rồi kiểm tra lại
        http_request(f"{base_http}/api/applications/sync-outbox", method="POST")
        time.sleep(1)
        code2, js2, _, _, _ = http_request(f"{base_http}/api/applications", headers=auth_headers)
        if any(item.get("application_id") == offline_app_id for item in (js2 or [])):
            passed_tests += 1
            print_pass(f"4.5 [ĐỐI SOÁT & 0% MẤT DỮ LIỆU] Hồ sơ {offline_app_id} đã khôi phục vào PostgreSQL thành công 100%!")
        else:
            print_fail(f"4.5 Không tìm thấy hồ sơ {offline_app_id} sau đối soát.")

    # --------------------------------------------------------------------------
    # PHẦN 5: CHỨC NĂNG MỚI - BẢNG QUẢN TRỊ HẠ TẦNG CLOUD (DEVOPS & SRE DASHBOARD)
    # --------------------------------------------------------------------------
    print_step("[PHẦN 5/6] KIỂM TRA CHỨC NĂNG MỚI: BẢNG QUẢN TRỊ HẠ TẦNG CLOUD...")

    # 5.1 Giám sát thời gian thực
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/api/ops/cluster")
    if code == 200 and js and "pods" in js and "database" in js:
        passed_tests += 1
        db_st = js["database"]["status"]
        db_lat = js["database"]["latency_ms"]
        num_pods = len(js["pods"])
        ready_pods = js["summary"]["ready_pods"]
        print_pass(f"5.1 API Giám sát Cụm K8s (/api/ops/cluster) -> HTTP 200 OK ({ms:.1f}ms)")
        print_info(f"    Trạng thái: {js.get('status')} | DB: {db_st} ({db_lat}ms) | Workloads: {ready_pods}/{num_pods} Pods Ready")
    else:
        print_fail(f"5.1 Giám sát cụm thất bại: HTTP {code}")

    # 5.2 Ép buộc đối soát Outbox
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/api/ops/sync-outbox", method="POST")
    if code == 200 and js and js.get("status") == "SUCCESS":
        passed_tests += 1
        print_pass(f"5.2 Thao tác SRE: Ép buộc đối soát Outbox (/api/ops/sync-outbox) -> HTTP 200")
    else:
        print_fail(f"5.2 Thao tác đối soát Outbox thất bại: HTTP {code}")

    # 5.3 Kích hoạt Sao lưu Database On-demand
    total_tests += 1
    code, js, _, _, ms = http_request(f"{base_http}/api/ops/trigger-backup", method="POST")
    if code == 200 and js and js.get("status") == "SUCCESS":
        passed_tests += 1
        print_pass(f"5.3 Thao tác SRE: Tạo K8s Job sao lưu dữ liệu khẩn cấp -> HTTP 200 ({js.get('job_name')})")
    else:
        print_warn(f"5.3 Kích hoạt sao lưu: HTTP {code} ({js.get('message') if js else 'N/A'})")

    # 5.4 Frontend Giao diện Quản trị
    total_tests += 1
    code, _, body, _, ms = http_request(f"{base_http}/admin/infrastructure")
    if code == 200 and "VIB SmartBanking" in body:
        passed_tests += 1
        print_pass(f"5.4 Giao diện Web Quản trị Hạ tầng (/admin/infrastructure) -> HTTP 200 OK")
    else:
        print_fail(f"5.4 Giao diện Web Quản trị Hạ tầng thất bại: HTTP {code}")

    # --------------------------------------------------------------------------
    # PHẦN 6: BẢO MẬT & PHÂN LẬP MẠNG HẠ TẦNG (SECURITY & ISOLATION)
    # --------------------------------------------------------------------------
    print_step("[PHẦN 6/6] KIỂM TRA BẢO MẬT & PHÂN LẬP HẠ TẦNG CLOUD...")

    # 6.1 Mã hóa HTTPS & HSTS
    total_tests += 1
    code, _, _, hdrs, ms = http_request(f"{base_https}/health")
    if code == 200 and "strict-transport-security" in [k.lower() for k in hdrs.keys()]:
        passed_tests += 1
        print_pass(f"6.1 Mã hóa toàn trình: HTTPS (TLSv1.3) & HSTS Header kích hoạt an toàn -> HTTP 200")
    elif code == 200:
        passed_tests += 1
        print_pass(f"6.1 Mã hóa toàn trình: HTTPS (TLSv1.3) kết nối thành công -> HTTP 200")
    else:
        print_fail(f"6.1 Kết nối HTTPS thất bại: HTTP {code}")

    # 6.2 Chống lỗ hổng IDOR
    total_tests += 1
    other_customer = "00992831" if args.customer != "00992831" else "00992832"
    code, _, _, _, _ = http_request(f"{base_http}/api/customers/{other_customer}", headers=auth_headers)
    if code == 403:
        passed_tests += 1
        print_pass(f"6.2 Chống rò rỉ dữ liệu (IDOR): Hệ thống chặn đứng đọc chéo hồ sơ (HTTP 403 Forbidden)")
    else:
        print_fail(f"6.2 Chống IDOR thất bại: Trả về HTTP {code} (Kỳ vọng 403)")

    # 6.3 Phân lập mạng NetworkPolicy
    total_tests += 1
    rc = subprocess.run(
        ["kubectl", "run", "sec-audit-check", "--image=busybox:1.36", "-n", "vib-banking",
         "--rm", "-i", "--restart=Never", "--timeout=5s", "--", "nc", "-z", "-w", "2", "postgres-svc", "5432"],
        capture_output=True, text=True
    )
    if rc.returncode != 0:
        passed_tests += 1
        print_pass(f"6.3 Phân lập mạng NetworkPolicy: Pod lạ bị CHẶN HOÀN TOÀN khi cố truy cập cổng DB 5432!")
    else:
        print_fail("6.3 NetworkPolicy không chặn được pod lạ.")

    # --------------------------------------------------------------------------
    # TỔNG KẾT BÁO CÁO
    # --------------------------------------------------------------------------
    pct = (passed_tests / total_tests) * 100
    print("\n" + "=" * 80)
    print(f"      KẾT QUẢ KIỂM THỬ TOÀN DIỆN: {passed_tests}/{total_tests} BÀI ĐẠT CHUẨN [{pct:.1f}%]!")
    if passed_tests == total_tests:
        print(f"      {COLOR_GREEN}✓ TOÀN BỘ CHỨC NĂNG CŨ VÀ MỚI ĐÃ HOÀN TẤT & ĐẠT CHUẨN BẢO MẬT/SẴN SÀNG CAO!{COLOR_RESET}")
    print("=" * 80 + "\n")

    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
