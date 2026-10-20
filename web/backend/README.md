# VIB SmartBanking — Backend (FastAPI + PostgreSQL)

REST API cho web SmartBanking: đăng nhập JWT, dữ liệu khách hàng, và gợi ý sản phẩm
real-time bằng 3 mô hình XGBoost của phân hệ AI (`ai/predict.py`).

```
React (5173) ──/api──► FastAPI (8000) ──► PostgreSQL (5432)
                            └──► VIBRecommendationEngine (nạp 1 lần lúc khởi động)
```

## Chạy local (lần đầu)

Yêu cầu: Python 3.11+, Docker Desktop đang chạy.

```bash
cd web/backend

# 1. Bật PostgreSQL
docker compose up -d db

# 2. Tạo môi trường Python + cài thư viện
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 3. Nạp dữ liệu demo (5 khách hàng, mật khẩu 123456)
python seed.py

# 4. Chạy API
uvicorn app.main:app --reload --port 8000
```

- Tài liệu API + test trực tiếp: http://localhost:8000/docs
- Frontend: tạo `web/frontend/.env.local` với `VITE_USE_MOCK=false`, rồi `npm run dev`.

Những lần sau chỉ cần: `docker compose up -d db` → `.venv\Scripts\activate` → `uvicorn app.main:app --reload`.

**Chạy toàn bộ bằng Docker** (không cần venv): `docker compose up -d --build` → API ở cổng 8000.

## Cấu trúc

```
app/
├── main.py            # tạo app, nạp model AI, /health, /ready
├── config.py          # biến môi trường
├── database.py        # kết nối SQLAlchemy
├── models.py          # bảng DB
├── schemas.py         # định dạng request/response (Pydantic)
├── auth.py            # bcrypt + JWT
├── ai_engine.py       # import ai/predict.py, danh mục sản phẩm
└── routers/           # auth, customers, recommendations, products, applications, ai
seed.py                # nạp dữ liệu demo
Dockerfile             # build từ gốc repo
docker-compose.yml     # Postgres (+ backend)
```

## Database

| Bảng | Nội dung |
| --- | --- |
| `customers` | Thông tin khách hàng, mật khẩu đã hash bcrypt |
| `accounts` | Tài khoản thanh toán, tiền gửi, thẻ, khoản vay |
| `transactions` | Lịch sử giao dịch |
| `customer_features` | 77 đặc trưng hành vi (JSONB) — đầu vào mô hình AI |
| `applications` | Hồ sơ đăng ký sản phẩm |
| `recommendation_logs` | Lịch sử mỗi lần AI gợi ý |

Bảng được tạo tự động khi khởi động. Dữ liệu demo: đặc trưng AI lấy nguyên từ
`ai/models/sample_customers.json` (khách hàng thật trong bộ dữ liệu); họ tên, SĐT, giao dịch là giả lập.
`python seed.py --reset` để xóa và nạp lại.

## API

Các endpoint đánh dấu 🔒 cần header `Authorization: Bearer <token>`; khách hàng chỉ đọc được dữ liệu của chính mình (403 nếu khác).

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| POST | `/api/auth/login` | `{customer_number, password}` → `{access_token, customer_number}` |
| GET | `/api/auth/demo-accounts` | Danh sách tài khoản demo (tắt khi `DEMO_MODE=false`) |
| GET 🔒 | `/api/customers/{id}` | `{profile, accounts[]}` |
| GET 🔒 | `/api/customers/{id}/transactions?limit=100` | Giao dịch mới nhất trước |
| GET 🔒 | `/api/recommendations/{id}` | Chạy AI, trả output của `predict_single()` |
| GET | `/api/products`, `/api/products/{code}` | Danh mục sản phẩm |
| POST 🔒 | `/api/applications` | Gửi hồ sơ đăng ký → `{application_id, status}` |
| GET 🔒 | `/api/applications` | Hồ sơ của tôi |
| GET | `/api/ai/metrics` | `training_metrics.json` |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe (kiểm tra DB + model) |

## Bàn giao cho nhóm Cloud

```bash
# Build từ thư mục gốc repo
docker build -f web/backend/Dockerfile -t vib-backend .
```

| Biến môi trường | Ý nghĩa |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/db` |
| `JWT_SECRET` | **Bắt buộc đổi** khi deploy (đưa vào K8s Secret), ≥ 32 ký tự |
| `JWT_EXPIRE_MINUTES` | Thời hạn token, mặc định 120 |
| `CORS_ORIGINS` | JSON list, vd. `["https://vib.example.com"]` (không cần nếu Ingress dùng chung domain) |
| `DEMO_MODE` | `false` trên production |

- Container lắng nghe cổng **8000**, probe: `livenessProbe` → `/health`, `readinessProbe` → `/ready`.
- API **stateless** (JWT, không session) → scale ngang bằng HPA thoải mái.
- Ingress: route `/api` → backend service, còn lại → frontend.
- Seed dữ liệu lần đầu: `kubectl exec <pod> -- python seed.py` (hoặc Job).
