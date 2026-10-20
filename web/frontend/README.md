# VIB SmartBanking — Frontend (ReactJS + Vite)

## Chạy dự án

```bash
cd web/frontend
npm install
npm run dev        # http://localhost:5173
```

Mặc định dùng **dữ liệu giả** (`src/mock/data.js`), không cần backend — bấm mã khách hàng demo ở màn hình đăng nhập.

**Dùng backend thật** (xem [web/backend/README.md](../backend/README.md)): tạo file `.env.local`:

```
VITE_USE_MOCK=false
```

Vite sẽ proxy `/api/*` sang `http://localhost:8000`. Tài khoản demo hiện ở màn hình đăng nhập, mật khẩu `123456`.

## Màn hình

| Route | Trang |
| --- | --- |
| `/login` | Đăng nhập |
| `/` | Tổng quan: số dư, gợi ý AI, giao dịch gần đây |
| `/products` | Danh sách sản phẩm + độ phù hợp AI |
| `/products/:code` | Chi tiết sản phẩm, lý do AI gợi ý, form đăng ký |
| `/transactions` | Lịch sử giao dịch, lọc/tìm kiếm |
| `/ai-insights` | Metrics mô hình XGBoost |

## API contract (cho backend FastAPI)

Toàn bộ lời gọi API nằm trong [`src/api/client.js`](src/api/client.js).

| Method | Endpoint | Response |
| --- | --- | --- |
| POST | `/api/auth/login` | `{ access_token, customer_number }` |
| GET | `/api/customers/{id}` | `{ profile, accounts[] }` |
| GET | `/api/customers/{id}/transactions` | `[{ id, date, description, category, amount }]` |
| GET | `/api/recommendations/{id}` | Output của `VIBRecommendationEngine.predict_single()` |
| GET | `/api/products` · `/api/products/{code}` | Danh mục sản phẩm |
| POST | `/api/applications` | `{ application_id, status }` |
| GET | `/api/ai/metrics` | Nội dung `ai/models/training_metrics.json` |
