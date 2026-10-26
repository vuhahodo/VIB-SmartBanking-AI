# ☁️ Hướng Dẫn Kiến Trúc & Xây Dựng Hạ Tầng Cloud (Cloud Architecture & Deployment Guide)

Tài liệu này giải thích chi tiết tư duy thiết kế, cách thức đóng gói các thành phần microservices và quy trình triển khai tự động hạ tầng đám mây cho dự án **VIB-SmartBanking-AI** trên nền tảng **K3s (Lightweight Kubernetes)**.

---

## 🧭 1. Tư Duy Thiết Kế Kiến Trúc Cloud-Native

Dự án phục vụ bài toán **Next-Best-Action (AI Cross-sell)** thời gian thực trên tập dữ liệu lớn (290K+ khách hàng). Do đó, hạ tầng đám mây được xây dựng xoay quanh 4 nguyên tắc cốt lõi:

1. **Decoupled Architecture (Tách biệt thành phần)**: Phân rã độc lập UI (ReactJS), API/AI Engine (FastAPI) và Storage (PostgreSQL) thành các microservices riêng biệt.
2. **Ephemeral & Stateless Backend**: Backend API không lưu trạng thái phiên đăng nhập trong bộ nhớ cục bộ của Pod; mô hình AI được nạp sẵn vào RAM khi Pod khởi động (`lifespan`) để phục vụ suy luận tức thì.
3. **Single Entry Point (Cổng vào duy nhất)**: Toàn bộ lưu lượng truy cập từ người dùng và client bên ngoài được kiểm soát và định tuyến tập trung qua một Ingress Controller duy nhất.
4. **Elastic Scaling (Co giãn linh hoạt)**: Tự động nhân bản số lượng Pod xử lý AI theo thời gian thực dựa trên tải trọng CPU (Horizontal Pod Autoscaler - HPA).

---

## 🏛️ 2. Sơ Đồ Luồng Hạ Tầng (Infrastructure Topology)

```text
                     [ Người dùng / HTTP Traffic ]
                                  │
                                  ▼
                    [ Nginx Ingress Controller ]
                    (Địa chỉ IP Node: 172.17.242.190)
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │ [Đường dẫn: /*]                                   │ [Đường dẫn: /api/*]
        ▼                                                   ▼
 [ Service: frontend ]                             [ Service: backend-api ]
 (ClusterIP: Port 80)                              (ClusterIP: Port 8000)
        │                                                   │
        ▼                                         ┌─────────┴─────────┐
 [ Pod: ReactJS Web UI ]                          ▼                   ▼
                                         [ Pod: backend-1 ]   [ Pod: backend-2 ] ... [ Pod: backend-N ]
                                         (FastAPI + Model)    (FastAPI + Model)      (Tự co giãn qua HPA)
                                                  │                   │
                                                  └─────────┬─────────┘
                                                            │
                                                            ▼
                                                   [ Service: postgres ]
                                                   (ClusterIP: Port 5432)
                                                            │
                                                            ▼
                                                [ StatefulSet: postgres-0 ]
                                                (Bảng customer_features - 290k dòng)
```

---

## 📦 3. Các Lớp Thành Phần & Cách Thức Xây Dựng

### 3.1. Lớp Định Danh & Bảo Mật (Namespace & Secrets)
* **File cấu hình**: `k8s/00-namespace-secrets.yaml`
* **Nhiệm vụ**:
  * Tạo riêng Namespace `vib-banking` để cô lập tài nguyên CPU/RAM và tránh xung đột với các ứng dụng hệ thống khác của cụm.
  * Mã hóa chuỗi kết nối cơ sở dữ liệu, mật khẩu quản trị thông qua `Kubernetes Secret` dạng base64 thay vì hardcode trong code.

### 3.2. Lớp Lưu Trữ Dữ Liệu (Data Layer - PostgreSQL StatefulSet)
* **File cấu hình**: `k8s/01-postgres.yaml`
* **Tại sao dùng StatefulSet thay vì Deployment?**
  * Cơ sở dữ liệu cần đảm bảo tính toàn vẹn dữ liệu và tên pod cố định (`postgres-0`).
  * Gắn kèm ổ đĩa bền vững (`PersistentVolumeClaim`) để dữ liệu 290.000 hồ sơ khách hàng không bị mất khi Pod bị khởi động lại.
* **Cơ chế Feature Store tối giản**:
  * Lưu trữ toàn bộ vector đặc trưng của khách hàng trong một cột `data` định dạng `JSONB`.
  * Truy vấn trực tiếp theo khóa chính `customer_number` với độ phức tạp **O(1)**, loại bỏ hoàn toàn các câu lệnh JOIN bảng tốn tài nguyên.

### 3.3. Lớp Xử Lý & Suy Luận AI (Compute Layer - Backend API)
* **File cấu hình**: `k8s/02-backend.yaml` và `k8s/01.5-backend-override.yaml`
* **Đặc tính kỹ thuật**:
  * **Zero-Cold-Start AI**: 3 mô hình XGBoost (Thẻ tín dụng, Khoản vay, Tiết kiệm) được nạp trực tiếp vào bộ nhớ trong tiến trình khởi chạy ứng dụng.
  * **Kiểm tra sức khỏe chủ động (Probes)**:
    * `readinessProbe`: Ingress chỉ dẫn traffic vào Pod khi mô hình AI đã hoàn tất nạp vào RAM.
    * `livenessProbe`: Tự động khởi động lại container nếu tiến trình backend bị treo hoặc rò rỉ bộ nhớ.
  * **Cấu hình động (ConfigMap Override)**: Router được liên kết qua VolumeMounts, cho phép tinh chỉnh luồng xử lý hoặc bypass xác thực mà không cần tốn thời gian build lại Docker Image.

### 3.4. Lớp Giao Diện Người Dùng (Presentation Layer - Frontend)
* **File cấu hình**: `k8s/03-frontend.yaml`
* **Đặc tính kỹ thuật**:
  * Ứng dụng ReactJS được biên dịch tĩnh (production build) và phục vụ qua một Web Server Nginx dung lượng siêu nhẹ (Alpine-based).
  * Giao diện gọi trực tiếp đến tiền tố `/api` mà không cần quan tâm IP backend, Ingress sẽ tự động điều phối phía sau.

### 3.5. Lớp Cổng Vào & Cân Bằng Tải (Ingress & Load Balancing)
* **File cấu hình**: `k8s/04-ingress.yaml`
* **Đặc tính kỹ thuật**:
  * Sử dụng **Nginx Ingress** tích hợp sẵn của K3s.
  * **Path-based Routing**:
    * `http://<NODE_IP>/api/*` chuyển tiếp tới cụm Backend API.
    * `http://<NODE_IP>/*` chuyển tiếp tới giao diện Frontend UI.
  * Tự động cân bằng tải luân phiên giữa các bản sao Pod backend đang sẵn sàng.

### 3.6. Lớp Tự Động Co Giãn Đàn Hồi (Auto-scaling Layer - HPA)
* **File cấu hình**: `k8s/05-hpa.yaml`
* **Nguyên lý vận hành**:
  * `backend-api` được gán định mức tài nguyên: `requests` (CPU 200m, RAM 512Mi) và `limits` (CPU 1000m, RAM 1Gi).
  * **Metrics Server** liên tục thu thập mức tiêu thụ CPU thực tế của các Pod.
  * **Quy tắc co giãn**:
    * Số lượng Pod tối thiểu: **2 Pods** (đảm bảo tính sẵn sàng cao).
    * Số lượng Pod tối đa: **5–6 Pods**.
    * Khi mức sử dụng CPU trung bình vượt ngưỡng **70%**, HPA phát lệnh cho Deployment tự động sinh thêm Pod mới để chia tải tính toán suy luận AI. Khi tải giảm, hệ thống tự động thu hẹp về 2 Pods để tiết kiệm tài nguyên.

---

## ⚡ 4. Quy Trình Khởi Chạy Tự Động (One-Click Deployment Workflow)

Toàn bộ hạ tầng được tự động hóa thông qua kịch bản `deploy.sh` theo thứ tự tuần tự nghiêm ngặt để tránh lỗi phụ thuộc:

```text
[BƯỚC 1] Khởi tạo Namespace & Secret
    │
    ▼
[BƯỚC 2] Triển khai PostgreSQL & Chờ Storage sẵn sàng (Rollout Status)
    │
    ▼
[BƯỚC 3] Nạp ConfigMap ghi đè cấu hình Router tối ưu
    │
    ▼
[BƯỚC 4] Khởi tạo đồng thời Backend API & Frontend UI
    │
    ▼
[BƯỚC 5] Đợi Probes xác nhận AI Engine sẵn sàng (Backend Ready)
    │
    ▼
[BƯỚC 6] Áp dụng Ingress Gateway & Kích hoạt chính sách HPA
    │
    ▼
[BƯỚC 7] Seed tài khoản demo mẫu và hiển thị trạng thái hoàn tất
```

---

## 🛠️ 5. Các Câu Lệnh Vận Hành & Giám Sát Cốt Lõi

```bash
# 1. Khởi chạy toàn bộ hạ tầng bằng một lệnh duy nhất
./deploy.sh

# 2. Xem toàn bộ trạng thái tài nguyên trong Namespace
kubectl get all,ing,hpa,cm -n vib-banking

# 3. Theo dõi mức tiêu thụ tài nguyên thời gian thực (Cần Metrics Server)
kubectl top pods -n vib-banking

# 4. Giám sát hành vi tự động co giãn của HPA trong lúc thử tải (Stress Test)
kubectl get hpa -n vib-banking -w
```