# VIB SmartBanking — Backend (FastAPI + PostgreSQL + AI Engine)

Hệ thống REST API cho ứng dụng ngân hàng số VIB SmartBanking: xác thực JWT, bảo vệ IDOR, truy xuất dữ liệu tài chính, gợi ý sản phẩm thời gian thực (Next-Best-Action) với 3 mô hình XGBoost, xử lý **đăng ký dịch vụ từ xa chịu thảm họa (Outbox Pattern & Zero Data Loss)** và cung cấp bộ API **Quản trị Hạ tầng SRE (Cluster Ops & Chaos Testing)**.

```
React (Nginx / Ingress) ──/api──► FastAPI (8000) ──► PostgreSQL (5432)
                                       │                  └── (Tự động nạp bù đơn tồn)
                                       ├──► VIBRecommendationEngine (3 mô hình XGBoost)
                                       ├──► Local Outbox Buffer (/tmp/vib_outbox: JSON)
                                       └──► Kubernetes in-cluster API (/api/ops/cluster)
```

---

## 🚀 Chạy Local (Môi trường Phát triển)

Yêu cầu: Python 3.11+, Docker Desktop đang chạy.

```bash
cd web/backend

# 1. Khởi động PostgreSQL container
docker compose up -d db

# 2. Tạo môi trường ảo Python & cài đặt thư viện
python -m venv .venv
source .venv/bin/activate       # Trên Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Nạp dữ liệu mẫu demo (Tài khoản demo: 00992830 / 123456)
python seed.py

# 4. Khởi chạy máy chủ API
uvicorn app.main:app --reload --port 8000
```

- **Tài liệu Swagger UI tương tác trực tiếp**: `http://localhost:8000/docs`
- **Frontend kết nối**: Cấu hình `VITE_USE_MOCK=false` trong `web/frontend/.env.local`.

---

## 📂 Cấu Trúc Mã Nguồn

```
app/
├── main.py            # Khởi tạo FastAPI, Lifespan nạp model AI, khởi động daemon Outbox Reconciler
├── config.py          # Quản lý biến môi trường (Pydantic Settings)
├── database.py        # Cấu hình SQLAlchemy Session & Pool kết nối
├── models.py          # Định nghĩa ORM models (khách hàng, tài khoản, giao dịch, hồ sơ đăng ký, chaos)
├── schemas.py         # Định dạng Schema Request/Response (Pydantic v2)
├── auth.py            # Băm mật khẩu bcrypt, phát hành & kiểm định JWT token, chống IDOR
├── ai_engine.py       # Tích hợp VIBRecommendationEngine từ ai/predict.py
└── routers/
    ├── auth.py            # Đăng nhập & danh sách tài khoản demo
    ├── customers.py       # Thông tin cá nhân & lịch sử giao dịch (có bảo vệ IDOR)
    ├── recommendations.py # Gợi ý Next-Best-Action theo khách hàng
    ├── products.py        # Danh mục sản phẩm thẻ, khoản vay, tiết kiệm
    ├── applications.py    # Đăng ký từ xa: Idempotency, Rule Fallback, Outbox Buffer & Auto-reconcile
    ├── ops.py             # Quản trị Hạ tầng: Giám sát K8s Pods, Stress Test HPA, Chaos DB, Sao lưu
    └── ai.py              # Báo cáo training metrics & feature drivers
seed.py                # Nạp hồ sơ mẫu 290k khách hàng và tài khoản demo
Dockerfile             # Đóng gói image phục vụ triển khai Kubernetes
```

---

## 🗄️ Cấu Trúc Cơ Sở Dữ Liệu

| Bảng | Nội dung & Chức năng |
|---|---|
| `customers` | Hồ sơ khách hàng, mật khẩu đã mã hóa bcrypt |
| `accounts` | Tài khoản thanh toán (Current Account), sổ tiết kiệm, khoản vay, thẻ |
| `transactions` | Lịch sử giao dịch biến động số dư |
| `customer_features` | 77 đặc trưng hành vi tài chính (JSONB) — đầu vào mô hình AI |
| `applications` | Hồ sơ đăng ký mở thẻ / khoản vay / sổ tiết kiệm trực tuyến |
| `recommendation_logs` | Nhật ký mỗi lượt AI suy luận gợi ý sản phẩm |
| `system_chaos` | Lưu cờ giả lập sự cố hạ tầng (`db_down`) dùng chung đồng bộ cho mọi bản sao Pod |

---

## 🛡️ Cơ Chế Xử Lý Đăng Ký Từ Xa Chịu Lỗi Cao (Resilience Architecture)

Phân hệ `routers/applications.py` được thiết kế để đối phó với mọi tình huống thảm họa thực tế:

1. **Chống Trùng lặp (Idempotency Protection)**:
   - Tiếp nhận header `X-Idempotency-Key` (hoặc `Idempotency-Key`).
   - Kiểm tra khóa trong cơ sở dữ liệu. Nếu phát hiện yêu cầu gửi lặp (do lag mạng hoặc người dùng bấm đúp), trả về ngay kết quả hồ sơ đã tạo kèm cờ `is_duplicate: true` (`HTTP 200 OK`).
2. **Suy Giảm Mềm Dẻo khi AI Quá Tải (AI Fallback Engine)**:
   - Khi dịch vụ AI bị timeout quá 1.5 giây hoặc gặp lỗi ngoại lệ, hệ thống tự động kích hoạt bộ luật dự phòng (Rule-based Fallback) dựa trên thu nhập và lịch sử quan hệ tài chính để cấp hạn mức tạm thời hoặc đưa vào trạng thái `PENDING_REVIEW` (`HTTP 201 Created`).
3. **Mô hình Outbox khi Database Sập Vật Lý (Zero Data Loss)**:
   - Khi mất kết nối PostgreSQL, backend bắt ngoại lệ `OperationalError`, tuần tự hóa hồ sơ thành file JSON ghi an toàn vào bộ đệm tệp cục bộ `/tmp/vib_outbox` (`HTTP 202 Accepted`, `status: QUEUED_OFFLINE`).
   - **Tự động đối soát**: Luồng tiến trình ngầm `vib_outbox_reconciler` chạy song song mỗi 2 giây. Khi kết nối DB phục hồi, tiến trình tự động đọc các file tệp trong bộ đệm và chèn bù vào bảng `applications`.

---

## 📋 Danh Sách Endpoints API

Các endpoint đánh dấu 🔒 yêu cầu tiêu đề `Authorization: Bearer <token>`. Hệ thống kiểm định token và từ chối truy cập chéo dữ liệu của khách hàng khác (`HTTP 403 Forbidden`).

### 1. Nhóm Nghiệp Vụ Ngân Hàng Số (Core Banking & AI)
| Method | Endpoint | Mô tả chức năng |
|---|---|---|
| POST | `/api/auth/login` | Xác thực đăng nhập `{customer_number, password}` → `{access_token}` |
| GET | `/api/auth/demo-accounts` | Danh sách tài khoản mẫu (chỉ bật khi `DEMO_MODE=true`) |
| GET 🔒 | `/api/customers/{id}` | Lấy thông tin hồ sơ và danh sách tài khoản của khách hàng |
| GET 🔒 | `/api/customers/{id}/transactions` | Lịch sử giao dịch (mặc định lấy 100 bản ghi gần nhất) |
| GET 🔒 | `/api/recommendations/{id}` | Kích hoạt 3 mô hình XGBoost suy luận gợi ý sản phẩm real-time |
| GET | `/api/products` | Danh mục sản phẩm thẻ, khoản vay, tiết kiệm |
| POST 🔒 | `/api/applications` | Nộp hồ sơ đăng ký từ xa (hỗ trợ Idempotency, Fallback, Outbox) |
| GET 🔒 | `/api/applications` | Tra cứu toàn bộ danh sách hồ sơ đăng ký của khách hàng đăng nhập |
| GET | `/api/ai/metrics` | Chỉ số ROC-AUC, F1-Score và đặc trưng ảnh hưởng của 3 model |
| GET | `/health` | Liveness Probe kiểm tra trạng thái tiến trình |
| GET | `/ready` | Readiness Probe xác nhận 3 model AI đã nạp đủ vào RAM |

### 2. Nhóm Quản Trị Hạ Tầng SRE & Thử Nghiệm Sự Cố (DevOps Ops API)
| Method | Endpoint | Mô tả chức năng |
|---|---|---|
| GET | `/api/ops/cluster` | Truy vấn in-cluster K8s API trả về danh sách Pods, trạng thái Ready, số lần Restart, tuổi thọ, HPA và K8s Cluster Events |
| POST | `/api/ops/toggle-chaos-db` | Bật/tắt chế độ mô phỏng sập DB đồng bộ qua bảng `system_chaos` |
| POST | `/api/ops/stress-test` | Bơm đột biến 60 phép tính AI song song để kích hoạt CPU spike và kiểm chứng HPA |
| POST | `/api/ops/sync-outbox` | Kích hoạt cưỡng bức đối soát và nạp toàn bộ đơn tồn trong Outbox vào DB |
| POST | `/api/ops/trigger-backup` | Khởi tạo K8s Job từ CronJob `pg-backup` tạo bản snapshot `.sql.gz` On-demand |
