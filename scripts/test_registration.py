#!/usr/bin/env python3
"""
Kịch bản kiểm thử toàn diện: BÀI TOÁN ĐĂNG KÝ TỪ XA (REMOTE REGISTRATION)
  1. Trường hợp KHÔNG CÓ SỰ CỐ (Happy Path):
     - Gửi đăng ký mở thẻ / vay / tiết kiệm.
     - Thẩm định AI thời gian thực (XGBoost Scoring) -> Tự động phê duyệt sơ bộ & cấp hạn mức.
  2. Trường hợp CÓ SỰ CỐ (Incidents & Resilience Patterns):
     - Sự cố 1 (Mạng lag / Double click): Idempotency Pattern chống tạo đơn trùng lặp.
     - Sự cố 2 (AI Service lỗi / timeout): Circuit Breaker & Graceful Degradation chuyển sang Rule-based Fallback.
     - Sự cố 3 (Database lỗi / failover): Outbox Buffer đệm an toàn, trả về QUEUED_OFFLINE (HTTP 202) không mất đơn.
  3. Kiểm tra danh sách hồ sơ đã đăng ký (Audit Trail).

Cách dùng:
  python scripts/test_registration.py --url http://172.17.242.190
  python scripts/test_registration.py --url http://localhost
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def http(url, data=None, token=None, headers=None, method=None, timeout=10):
    all_headers = headers.copy() if headers else {}
    req_data = None
    if data is not None:
        all_headers["Content-Type"] = "application/json"
        req_data = json.dumps(data).encode("utf-8")
    if token:
        all_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=req_data, headers=all_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return e.code, parsed
    except Exception as e:
        return 0, {"error": str(e)}


def login(base, customer, password):
    url = f"{base}/api/auth/login"
    status, res = http(url, data={"customer_number": customer, "password": password})
    if status == 200 and "access_token" in res:
        return res["access_token"]
    raise RuntimeError(f"Đăng nhập thất bại (HTTP {status}): {res}")


def main():
    p = argparse.ArgumentParser(description="Kiểm thử bài toán đăng ký từ xa: có sự cố và không sự cố")
    p.add_argument("--url", default="http://172.17.242.190", help="Địa chỉ API / Ingress")
    p.add_argument("--customer", default="00992830", help="Mã khách hàng demo")
    p.add_argument("--password", default="123456", help="Mật khẩu demo")
    args = p.parse_args()

    base = args.url.rstrip("/")
    print(f"{BLUE}================================================================{NC}")
    print(f"{BLUE}  KIỂM THỬ BÀI TOÁN ĐĂNG KÝ TỪ XA: CÓ SỰ CỐ & KHÔNG SỰ CỐ       {NC}")
    print(f"{BLUE}  Địa chỉ kiểm thử: {base}                                     {NC}")
    print(f"{BLUE}================================================================{NC}\n")

    # 0. Đăng nhập lấy JWT Token
    print(f"[*] 0. Đăng nhập khách hàng {args.customer}...")
    try:
        token = login(base, args.customer, args.password)
        print(f"  [{GREEN}PASS{NC}] Đăng nhập thành công, đã cấp JWT Token.\n")
    except Exception as e:
        print(f"  [{RED}FAIL{NC}] {e}")
        return 1

    passed_count = 0
    total_tests = 5

    # --------------------------------------------------------------------------
    # BÀI TOÁN 1: KHÔNG CÓ SỰ CỐ (HAPPY PATH)
    # --------------------------------------------------------------------------
    print(f"{YELLOW}>>> [TEST 1/5] KỊCH BẢN CHUẨN: ĐĂNG KÝ THÀNH CÔNG (KHÔNG SỰ CỐ)...{NC}")
    payload_happy = {
        "product_code": "CREDIT_CARD",
        "full_name": "Nguyễn Thị Minh Anh",
        "phone": "0941790088",
        "email": "kh00992830@example.com",
        "monthly_income": 25000000,
        "amount": 50000000,
        "idempotency_key": f"IDEM-HAPPY-{int(time.time()*1000)}",
    }
    status, res = http(f"{base}/api/applications", data=payload_happy, token=token)
    if status == 201:
        passed_count += 1
        print(f"  [{GREEN}PASS{NC}] HTTP 201 Created!")
        print(f"         Mã hồ sơ: {res.get('application_id')}")
        print(f"         Trạng thái: {res.get('status')}")
        print(f"         AI Score: {res.get('ai_score')}")
        print(f"         Hạn mức cấp: {res.get('assigned_limit'):,} VND" if res.get('assigned_limit') else "")
        print(f"         Quyết định: {res.get('decision_reason')}\n")
    else:
        print(f"  [{RED}FAIL{NC}] Thất bại (HTTP {status}): {res}\n")

    # --------------------------------------------------------------------------
    # BÀI TOÁN 2A: SỰ CỐ MẠNG LAG / GỬI TRÙNG LẶP (IDEMPOTENCY PATTERN)
    # --------------------------------------------------------------------------
    print(f"{YELLOW}>>> [TEST 2/5] SỰ CỐ MẠNG: GỬI LẶP 2 LẦN CÙNG IDEMPOTENCY KEY (CHỐNG DUPLICATE)...{NC}")
    idem_key = f"IDEM-DOUBLE-{int(time.time()*1000)}"
    payload_dup = {
        "product_code": "CONSUMER_LOAN",
        "full_name": "Nguyễn Thị Minh Anh",
        "phone": "0941790088",
        "email": "kh00992830@example.com",
        "monthly_income": 25000000,
        "amount": 40000000,
        "idempotency_key": idem_key,
    }
    # Lần 1
    s1, r1 = http(f"{base}/api/applications", data=payload_dup, token=token)
    app_id_1 = r1.get("application_id")
    print(f"  [*] Lần 1: Gửi đơn vay thành công -> Mã {app_id_1} (HTTP {s1})")

    # Lần 2 (Ngay lập tức gửi lại cùng Idempotency Key)
    s2, r2 = http(f"{base}/api/applications", data=payload_dup, token=token)
    app_id_2 = r2.get("application_id")
    is_dup = r2.get("is_duplicate", False)

    if s2 == 200 and is_dup and (app_id_1 == app_id_2):
        passed_count += 1
        print(f"  [{GREEN}PASS{NC}] Idempotency hoạt động hoàn hảo!")
        print(f"         Lần 2 trả về HTTP 200 OK (is_duplicate={is_dup})")
        print(f"         Mã hồ sơ trùng khớp ({app_id_2}), không sinh đơn rác trong DB.\n")
    else:
        print(f"  [{RED}FAIL{NC}] Chống trùng lặp thất bại (HTTP {s2}): {r2}\n")

    # --------------------------------------------------------------------------
    # BÀI TOÁN 2B: SỰ CỐ MÔ HÌNH AI GẶP LỖI (CIRCUIT BREAKER & RULE-BASED FALLBACK)
    # --------------------------------------------------------------------------
    print(f"{YELLOW}>>> [TEST 3/5] SỰ CỐ TẦNG AI: MÔ PHỎNG AI TIMEOUT/CRASH -> KÍCH HOẠT FALLBACK...{NC}")
    payload_ai_err = {
        "product_code": "CREDIT_CARD",
        "full_name": "Nguyễn Thị Minh Anh",
        "phone": "0941790088",
        "email": "kh00992830@example.com",
        "monthly_income": 30000000,
        "amount": 60000000,
        "idempotency_key": f"IDEM-AI-ERR-{int(time.time()*1000)}",
    }
    # Gọi kèm query simulate_failure=ai_error
    s_ai, r_ai = http(f"{base}/api/applications?simulate_failure=ai_error", data=payload_ai_err, token=token)
    if s_ai == 201 and r_ai.get("mode") == "FALLBACK_RULE_BASED":
        passed_count += 1
        print(f"  [{GREEN}PASS{NC}] Circuit Breaker & Graceful Degradation thành công!")
        print(f"         Hệ thống không sập 500, tự động chuyển chế độ: {r_ai.get('mode')}")
        print(f"         Trạng thái: {r_ai.get('status')}")
        print(f"         Lý do: {r_ai.get('decision_reason')}\n")
    else:
        print(f"  [{RED}FAIL{NC}] Xử lý sự cố AI thất bại (HTTP {s_ai}): {r_ai}\n")

    # --------------------------------------------------------------------------
    # BÀI TOÁN 2C: SỰ CỐ CƠ SỞ DỮ LIỆU BỊ NGẮT KẾT NỐI (OUTBOX BUFFER RESILIENCE)
    # --------------------------------------------------------------------------
    print(f"{YELLOW}>>> [TEST 4/5] SỰ CỐ TẦNG DATABASE: MÔ PHỎNG DB CRASH -> LƯU VÀO OUTBOX BUFFER...{NC}")
    payload_db_err = {
        "product_code": "TERM_DEPOSIT",
        "full_name": "Nguyễn Thị Minh Anh",
        "phone": "0941790088",
        "email": "kh00992830@example.com",
        "monthly_income": 20000000,
        "amount": 50000000,
        "idempotency_key": f"IDEM-DB-ERR-{int(time.time()*1000)}",
    }
    # Gọi kèm query simulate_failure=db_error
    s_db, r_db = http(f"{base}/api/applications?simulate_failure=db_error", data=payload_db_err, token=token)
    if s_db == 202 and r_db.get("status") == "QUEUED_OFFLINE":
        passed_count += 1
        print(f"  [{GREEN}PASS{NC}] Storage Resilience (Outbox Pattern) thành công!")
        print(f"         Hệ thống phản hồi HTTP 202 Accepted (Không trả lỗi 500).")
        print(f"         Mã đơn đệm an toàn: {r_db.get('application_id')}")
        print(f"         Trạng thái: {r_db.get('status')}")
        print(f"         Cơ chế: {r_db.get('mode')} -> Đơn không bị mất, sẵn sàng retry đồng bộ khi DB online.\n")
    else:
        print(f"  [{RED}FAIL{NC}] Xử lý sự cố Database thất bại (HTTP {s_db}): {r_db}\n")

    # --------------------------------------------------------------------------
    # BÀI TOÁN 3: TRA CỨU DANH SÁCH HỒ SƠ ĐÃ ĐĂNG KÝ (AUDIT TRAIL)
    # --------------------------------------------------------------------------
    print(f"{YELLOW}>>> [TEST 5/5] KIỂM TRA LỊCH SỬ HỒ SƠ ĐÃ NỘP (GET /api/applications)...{NC}")
    s_list, r_list = http(f"{base}/api/applications", token=token)
    if s_list == 200 and isinstance(r_list, list) and len(r_list) > 0:
        passed_count += 1
        print(f"  [{GREEN}PASS{NC}] Lấy danh sách thành công! Tìm thấy {len(r_list)} hồ sơ trong lịch sử:")
        for item in r_list[:3]:
            print(f"         - [{item.get('status')}] Mã: {item.get('application_id')} | Sản phẩm: {item.get('product_code')} | Mode: {item.get('mode', 'ONLINE')}")
        print()
    else:
        print(f"  [{RED}FAIL{NC}] Tra cứu hồ sơ thất bại (HTTP {s_list}): {r_list}\n")

    # --------------------------------------------------------------------------
    # TỔNG KẾT
    # --------------------------------------------------------------------------
    print(f"{BLUE}================================================================{NC}")
    if passed_count == total_tests:
        print(f"{GREEN}  HOÀN TẤT: {passed_count}/{total_tests} BÀI TEST ĐẠT [PASS] 100%!{NC}")
        print(f"{GREEN}  Hệ thống xử lý xuất sắc cả 2 kịch bản: KHÔNG CÓ SỰ CỐ & CÓ SỰ CỐ.{NC}")
    else:
        print(f"{YELLOW}  KẾT QUẢ: {passed_count}/{total_tests} PASS. Kiểm tra lại các mục thất bại.{NC}")
    print(f"{BLUE}================================================================{NC}")

    return 0 if passed_count == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
