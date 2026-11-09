# VIB SmartBanking — Frontend (ReactJS + Vite + TailwindCSS)

Giao diện người dùng cho ứng dụng ngân hàng số VIB SmartBanking, tích hợp phân hệ gợi ý sản phẩm AI thời gian thực, bảng theo dõi hồ sơ mở thẻ/vay vốn từ xa và **Bảng điều khiển Quản trị Hạ tầng Điện toán Đám mây (SRE / DevOps Cloud Management Dashboard)**.

---

## 🚀 Khởi Chạy Local (Môi Trường Phát Triển)

```bash
cd web/frontend
npm install
npm run dev        # Ứng dụng chạy tại http://localhost:5173
```

- **Chế độ Mock (Dữ liệu giả lập)**: Tạo môi trường test nhanh độc lập không cần backend (`VITE_USE_MOCK=true`).
- **Chế độ Real API (Kết nối Backend thật)**: Tạo file `web/frontend/.env.local`:
  ```ini
  VITE_USE_MOCK=false
  ```
  Vite sẽ tự động chuyển tiếp (proxy) các lời gọi `/api/*` tới máy chủ backend tại `http://localhost:8000` (hoặc Ingress gateway `http://172.17.242.190`).
- **Tài khoản đăng nhập demo**: Mã khách hàng `00992830`, Mật khẩu `123456`.

---

## 🖥️ Các Màn Hình Ứng Dụng (Page Routes)

| Tuyến Đường (Route) | Tên Màn Hình | Mô Tả Chức Năng |
|---|---|---|
| `/login` | Đăng nhập | Đăng nhập tài khoản bằng mã khách hàng và mật khẩu, cấp JWT token |
| `/` | Tổng quan (Dashboard) | Số dư khả dụng, biểu đồ chi tiêu, gợi ý sản phẩm AI Next-Best-Action, giao dịch gần nhất và **bảng theo dõi trạng thái các hồ sơ đăng ký từ xa** |
| `/products` | Danh sách sản phẩm | Hiển thị danh mục thẻ tín dụng, tiền gửi kỳ hạn, khoản vay kèm tỷ lệ phù hợp tính toán bởi AI |
| `/products/:code` | Chi tiết sản phẩm | Thông tin chi tiết sản phẩm, các yếu tố đặc trưng thúc đẩy AI gợi ý, và biểu mẫu nộp đơn đăng ký trực tuyến |
| `/transactions` | Lịch sử giao dịch | Danh sách biến động số dư, bộ lọc theo danh mục chi tiêu và tìm kiếm |
| `/ai-insights` | AI MLOps Insights | Bảng đo lường chất lượng 3 mô hình XGBoost (ROC-AUC, Precision, Recall, Confusion Matrix) |
| `/admin/infrastructure` | **Quản trị Hạ tầng Cloud** | **Bảng điều khiển SRE/DevOps**: Giám sát Pods K8s, độ trễ PostgreSQL, bộ đệm Outbox, HPA, K8s Events và Interactive Chaos Lab |

---

## ⚡ Tính Năng Mới Nổi Bật

### 1. Bảng Điều Khiển Quản Trị Hạ Tầng SRE (`/admin/infrastructure`)
Được thiết kế dành riêng cho kỹ sư vận hành hệ thống đám mây để theo dõi và phản ứng kịp thời khi hạ tầng gặp sự cố:
- **Card Trạng thái Trực quan**:
  - *PostgreSQL*: Đo độ trễ kết nối round-trip (ms), trạng thái ổ đĩa PVC 5Gi, trạng thái cô lập NetworkPolicy.
  - *Bộ đệm Outbox Phục hồi*: Số đơn tồn đọng trong hàng đợi `/tmp/vib_outbox`, chu kỳ quét của tiến trình đối soát tự động.
  - *Co giãn HPA Backend*: Số lượng bản sao Pods hiện tại (2 - 8 pods), phần trăm CPU sử dụng thực tế so với ngưỡng 70%.
  - *Bảo mật & Ingress*: Xác nhận TLSv1.3 HTTPS, cấu hình Rate Limiting (25 RPS / Burst 50) và chống rò rỉ dữ liệu IDOR.
- **Danh Sách Workloads Kubernetes**:
  - Đọc trực tiếp danh sách 5 Pods (`backend-api`, `frontend-ui`, `postgres-0`) từ K8s in-cluster API.
  - Hiển thị IP nội bộ, trạng thái Ready, số lần restart và tuổi thọ Pod.
- **Nhật Ký Sự Kiện Cụm (Cluster Events)**:
  - Hiển thị các sự kiện phát sinh trong namespace `vib-banking` (Pod scaling, Job completed, Image pulled) phục vụ điều tra nguyên nhân gốc rễ (RCA).
- **Phòng Thử Nghiệm Tác Động Hạ Tầng & Phản Ứng Nhanh (Interactive Chaos Lab)**:
  - *Mô phỏng sập Database (Chaos Test)*: Ngắt kết nối DB trên toàn cụm để kiểm tra cơ chế nộp đơn Outbox.
  - *Khôi phục kết nối Database*: Kích hoạt DB online trở lại và nạp bù toàn bộ đơn tồn.
  - *Bơm Tải Đột Biến (Stress Test)*: Bơm 60 phép suy luận AI song song để kích hoạt co giãn HPA.
  - *Ép buộc đối soát Outbox ngay*: Quét bộ nhớ đệm và nạp toàn bộ đơn tồn vào PostgreSQL lập tức.
  - *Kích hoạt Sao lưu Database On-demand*: Khởi tạo Job sao lưu tức thì từ CronJob `pg-backup`.
- **Live Terminal Console Tích hợp**:
  - Hiển thị kết quả trả về thời gian thực gồm HTTP Status Code, thời gian phản hồi (ms) và JSON response.

### 2. Theo Dõi Hồ Sơ Đăng Ký Từ Xa Trên Dashboard (`/`)
- Hiển thị danh sách toàn bộ hồ sơ do người dùng nộp từ xa.
- Hiển thị rõ mã đơn, ngày nộp, hạn mức sơ bộ được duyệt, điểm rủi ro AI và chế độ xử lý của hệ thống:
  - `DIRECT_AI_APPROVED`: Thẩm định trực tiếp qua mô hình AI XGBoost (`HTTP 201 Created`).
  - `RULE_BASED_FALLBACK`: Thẩm định qua luật dự phòng khi dịch vụ AI bị quá tải/timeout (`HTTP 201 Created`).
  - `OUTBOX_OFFLINE_SAVED`: Tiếp nhận vào bộ đệm tệp an toàn khi Database gặp sự cố sập kết nối (`HTTP 202 Accepted`).

---

## 📡 API Client Contract (`src/api/client.js`)

| Phương thức | Endpoint | Mô tả chức năng |
|---|---|---|
| `login(customer_number, password)` | `/api/auth/login` | Đăng nhập nhận JWT token |
| `getCustomer(id)` | `/api/customers/{id}` | Lấy thông tin cá nhân và tài khoản |
| `getTransactions(id)` | `/api/customers/{id}/transactions` | Lịch sử giao dịch |
| `getRecommendations(id)` | `/api/recommendations/{id}` | Lấy kết quả AI Next-Best-Action |
| `getProducts()` | `/api/products` | Danh mục sản phẩm tài chính |
| `submitApplication(data)` | `/api/applications` | Nộp hồ sơ đăng ký từ xa kèm `X-Idempotency-Key` |
| `getMyApplications()` | `/api/applications` | Lấy danh sách hồ sơ đăng ký của người dùng |
| `getClusterStatus()` | `/api/ops/cluster` | Lấy thông tin Pods, Events, HPA từ cụm K8s |
| `toggleChaosDB()` | `/api/ops/toggle-chaos-db` | Bật/tắt chế độ mô phỏng sự cố Database |
| `triggerStressTest()` | `/api/ops/stress-test` | Kích hoạt stress test 60 AI calls |
| `syncOutbox()` | `/api/ops/sync-outbox` | Kích hoạt đối soát cưỡng bức bộ đệm Outbox |
| `triggerOnDemandBackup()` | `/api/ops/trigger-backup` | Khởi chạy K8s Job sao lưu dữ liệu tức thì |
| `getAIMetrics()` | `/api/ai/metrics` | Lấy thông số huấn luyện mô hình XGBoost |
