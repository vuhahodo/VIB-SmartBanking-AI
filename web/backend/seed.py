"""
Nạp dữ liệu demo vào PostgreSQL.

- Đặc trưng AI (customer_features) lấy NGUYÊN từ ai/models/sample_customers.json
  (khách hàng thật trong bộ dữ liệu VIB Hackathon 2021).
- Họ tên, email, SĐT, số tài khoản, lịch sử giao dịch là dữ liệu giả lập
  (bộ dữ liệu gốc đã ẩn danh), được sinh nhất quán với đặc trưng của khách.

Chạy:  python seed.py            # thêm khách chưa có
       python seed.py --reset    # xóa toàn bộ bảng rồi nạp lại
"""

import argparse
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone

from app.auth import hash_password
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Account, Customer, CustomerFeature, Transaction

DEMO_PASSWORD = "123456"

NAMES = {
    "F": ["Nguyễn Thị Minh Anh", "Lê Thu Hà", "Phạm Ngọc Lan", "Trần Bảo Ngọc", "Võ Thanh Hương"],
    "M": ["Trần Văn Hùng", "Phạm Quốc Bảo", "Hoàng Minh Tuấn", "Đỗ Đức Long", "Bùi Gia Huy"],
}

TX_TEMPLATES = [
    ("Chuyển khoản", "Chuyển khoản đến {name}", (-0.9, -0.2)),
    ("QR", "Thanh toán QR - {shop}", (-0.15, -0.01)),
    ("Ví điện tử", "Thanh toán {app} qua ví điện tử", (-0.3, -0.02)),
    ("Hóa đơn", "Hóa đơn {bill}", (-0.1, -0.02)),
    ("Nạp tiền", "Nạp tiền điện thoại {telco}", (-0.05, -0.01)),
    ("Chuyển khoản", "Nhận chuyển khoản từ {name}", (0.2, 1.0)),
]
FILL = {
    "name": ["Lê Thu Hà", "Phạm Quốc Bảo", "Ngô Thanh Tâm", "Vũ Hải Đăng"],
    "shop": ["Highlands Coffee", "Circle K", "Bách Hóa Xanh", "WinMart", "Phúc Long"],
    "app": ["Shopee", "Grab", "Tiki", "Lazada"],
    "bill": ["điện EVN", "nước Sawaco", "Internet FPT", "truyền hình K+"],
    "telco": ["Viettel", "Mobifone", "Vinaphone"],
}


def make_transactions(rng: random.Random, features: dict) -> list[dict]:
    """Sinh giao dịch giả lập theo tần suất & giá trị trung bình trong đặc trưng."""
    now = datetime.now(timezone.utc)
    n = min(int(features.get("total_transactions") or 0), 40)
    avg = float(features.get("avg_trans_amount") or 0) or 500_000
    # Giới hạn để số liệu hiển thị hợp lý trên UI
    avg = min(max(avg, 200_000), 20_000_000)

    txs = []
    for _ in range(n):
        category, tpl, (lo, hi) = rng.choice(TX_TEMPLATES)
        desc = tpl.format(**{k: rng.choice(v) for k, v in FILL.items()})
        amount = round(avg * rng.uniform(lo, hi) * 2, -3)
        when = now - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        txs.append({"date": when, "description": desc, "category": category, "amount": amount})

    # Khách ít dùng MyVIB vẫn có vài giao dịch tại quầy để UI không trống
    if n == 0:
        for d in (3, 17, 34):
            txs.append({
                "date": now - timedelta(days=d, hours=rng.randint(1, 8)),
                "description": "Nộp tiền mặt tại quầy giao dịch VIB",
                "category": "Tại quầy",
                "amount": round(rng.uniform(1, 5), 1) * 1_000_000,
            })
    return txs


def make_accounts(rng: random.Random, cust_no: str, f: dict) -> list[Account]:
    def acc_no() -> str:
        return " ".join(f"{rng.randint(0, 9999):04d}" for _ in range(3))

    accounts = [Account(type="Tài khoản thanh toán", number=acc_no(), balance=round(float(f.get("avg_ca_balance_last") or 0), 0))]
    if f.get("has_term_deposit"):
        accounts.append(Account(type="Tiền gửi có kỳ hạn", number=acc_no(), balance=round(float(f.get("avg_td_balance_mean") or 0), 0)))
    if f.get("has_debitcard"):
        accounts.append(Account(type="Thẻ ghi nợ VIB Online Plus", number=f"**** **** **** {cust_no[-4:]}", balance=None))
    if f.get("has_creditcard"):
        accounts.append(Account(type="Thẻ tín dụng VIB", number=f"**** **** **** {cust_no[-5:-1]}", balance=None))
    if f.get("has_loan"):
        accounts.append(Account(type="Khoản vay", number=acc_no(), balance=-round(float(f.get("avg_loan_amount_mean") or 0), 0)))
    return accounts


def main(reset: bool) -> None:
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    samples_path = settings.AI_DIR / "models" / "sample_customers.json"
    samples = json.loads(samples_path.read_text(encoding="utf-8"))
    password_hash = hash_password(DEMO_PASSWORD)
    used = {"F": 0, "M": 0}
    added = 0

    with SessionLocal() as db:
        for raw in samples:
            cust_no = str(raw["CUSTOMER_NUMBER"])
            if db.get(Customer, cust_no):
                continue
            # Bỏ mã KH và nhãn target_* (nhãn huấn luyện, không phải đầu vào model)
            features = {k: v for k, v in raw.items() if k != "CUSTOMER_NUMBER" and not k.startswith("target_")}
            rng = random.Random(cust_no)
            g = "F" if raw.get("is_female") else "M"
            name = NAMES[g][used[g] % len(NAMES[g])]
            used[g] += 1

            customer = Customer(
                customer_number=cust_no,
                full_name=name,
                gender="Nữ" if g == "F" else "Nam",
                age=int(raw.get("age") or 30),
                email=f"kh{cust_no}@example.com",
                phone=f"09{rng.randint(10_000_000, 99_999_999)}",
                joined_date=date.today() - timedelta(days=int(raw.get("tenure_days") or 0)),
                password_hash=password_hash,
                accounts=make_accounts(rng, cust_no, features),
                features=CustomerFeature(features=features),
            )
            db.add(customer)
            db.add_all(Transaction(customer_number=cust_no, **t) for t in make_transactions(rng, features))
            added += 1
        db.commit()

    print(f"Seed xong: thêm {added} khách hàng (mật khẩu demo: {DEMO_PASSWORD}).")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Xóa và tạo lại toàn bộ bảng")
    main(parser.parse_args().reset)
