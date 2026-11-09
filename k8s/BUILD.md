# ☁️ Hướng Dẫn Kiến Trúc & Xây Dựng Hạ Tầng Cloud (Cloud Architecture & Deployment Guide)

Tài liệu này giải thích chi tiết tư duy thiết kế, cách thức đóng gói các thành phần microservices và quy trình triển khai tự động hạ tầng đám mây cho dự án **VIB-SmartBanking-AI** trên nền tảng **K3s (Lightweight Kubernetes)**, kết hợp kiến trúc **chịu thảm họa không mất dữ liệu (Disaster Recovery & Zero Data Loss)** và **bảng điều khiển SRE vận hành thời gian thực**.

---

## 🧭 1. Tư Duy Thiết Kế Kiến Trúc Cloud-Native

Dự án phục vụ bài toán **Next-Best-Action (AI Cross-sell)** và **Đăng ký dịch vụ ngân hàng từ xa (Remote Service Registration)** thời gian thực trên tập dữ liệu lớn (290K+ khách hàng). Do đó, hạ tầng đám mây được xây dựng xoay quanh 6 nguyên tắc cốt lõi:

1. **Decoupled Architecture (Tách biệt thành phần)**: Phân rã độc lập UI (ReactJS), API/AI Engine (FastAPI) và Storage (PostgreSQL) thành các microservices riêng biệt.
2. **Ephemeral & Stateless Backend**: Backend API không lưu trạng thái phiên đăng nhập trong bộ nhớ cục bộ của Pod; mô hình AI được nạp sẵn vào RAM khi Pod khởi động (`lifespan`) để phục vụ suy luận tức thì.
3. **Single Entry Point & Multi-layer Defense**: Toàn bộ lưu lượng truy cập được định tuyến qua Nginx Ingress Controller tích hợp mã hóa **HTTPS TLSv1.3**, tiêu đề **HSTS** và cơ chế **Rate Limiting (25 RPS / Burst 50)**.
4. **Elastic Scaling (Co giãn linh hoạt)**: Tự động nhân bản số lượng Pod xử lý AI theo thời gian thực dựa trên tải trọng CPU (Horizontal Pod Autoscaler - HPA: 2 đến 8 Pods @ 70% CPU).
5. **Zero Data Loss Resilience (Khả năng chịu thảm họa)**: Áp dụng **Outbox Pattern** cục bộ kết hợp tiến trình ngầm **Auto-Reconciliation Daemon** để tiếp nhận hồ sơ đăng ký an toàn ngay cả khi PostgreSQL gặp sự cố sập kết nối vật lý.
6. **Observability & SRE Incident Response**: Tích hợp bảng điều khiển SRE chuyên dụng (`/admin/infrastructure`) kết nối trực tiếp K8s in-cluster API cho phép theo dõi nhịp tim hệ thống và chủ động kích hoạt các thao tác ứng phó thảm họa tức thì.

---

## 🏛️ 2. Sơ Đồ Luồng Hạ Tầng (Infrastructure Topology)

```text
                     [ Người dùng / Kỹ sư SRE ]
                                  │
                                  ▼
                [ Nginx Ingress Controller (172.17.242.190) ]
                (HTTPS TLSv1.3 | Rate Limiting: 25 RPS)
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │ [Đường dẫn: /*]                                   │ [Đường dẫn: /api/*]
        ▼                                                   ▼
 [ Service: frontend ]                             [ Service: backend-api ]
 (ClusterIP: Port 80)                              (ClusterIP: Port 8000)
        │                                                   │
        ▼                                         ┌─────────┴─────────┐
 [ Pod: ReactJS Web UI ]                          ▼                   ▼
 (Nginx Production Serve)                [ Pod: backend-1 ]   [ Pod: backend-2 ] ... [ Pod: backend-N ]
                                         (FastAPI + Model)    (FastAPI + Model)      (Tự co giãn qua HPA)
                                                  │                   │
                                                  ├───────────────────┤
                                                  │ (Khi DB online)   │ (Khi DB sập vật lý)
                                                  ▼                   ▼
                                         [ Service: postgres ]  [ Local Outbox Buffer ]
                                         (ClusterIP: Port 5432) (/tmp/vib_outbox: JSON)
                                                  │                   │
                                                  ▼                   │ (Tự động nạp bù khi DB sống lại)
                                        [ StatefulSet: postgres-0 ] ◄─┘
                                        (Gắn PVC postgres-pvc 5Gi)
                                                  ▲
                                                  │ (Sao lưu định kỳ 02:00)
                                        [ CronJob: pg-backup ]
                                        (Gắn PVC pg-backups)
```

---

## 📦 3. Các Lớp Thành Phần & Cách Thức Xây Dựng

### 3.1. Lớp Định Danh & Bảo Mật (Namespace & Secrets)
* **File cấu hình**: `k8s/00-namespace-secrets.yaml`
* **Nhiệm vụ**:
  * Tạo riêng Namespace `vib-banking` để cô lập tài nguyên CPU/RAM và tránh xung đột với các ứng dụng hệ thống khác của cụm.
  * Mã hóa chuỗi kết nối cơ sở dữ liệu, mật khẩu quản trị thông qua `Kubernetes Secret` dạng base64 thay vì hardcode trong code.
  * Cung cấp Secret TLS `vib-tls-secret` chứa cặp chứng chỉ SSL để Ingress kích hoạt HTTPS an toàn.

### 3.2. Lớp Lưu Trữ Dữ Liệu Bền Vững (Data Layer - PostgreSQL StatefulSet)
* **File cấu hình**: `k8s/01-postgres.yaml`
* **Tại sao dùng StatefulSet thay vì Deployment?**
  * Cơ sở dữ liệu cần đảm bảo tính toàn vẹn dữ liệu và tên pod cố định (`postgres-0`).
  * Gắn kèm ổ đĩa bền vững (`PersistentVolumeClaim`: `postgres-pvc` 5Gi) để dữ liệu 290.000 hồ sơ khách hàng không bị mất khi Pod bị khởi động lại.
* **Cơ chế Feature Store tối giản**:
  * Lưu trữ toàn bộ vector đặc trưng của khách hàng trong một cột `data` định dạng `JSONB`.
  * Truy vấn trực tiếp theo khóa chính `customer_number` với độ phức tạp **O(1)**, loại bỏ hoàn toàn các câu lệnh JOIN bảng tốn tài nguyên.

### 3.3. Lớp Xử Lý & Suy Luận AI (Compute Layer - Backend API)
* **File cấu hình**: `k8s/02-backend.yaml` và `k8s/01.5-backend-override.yaml`
* **Đặc tính kỹ thuật**:
  * **Zero-Cold-Start AI**: 3 mô hình XGBoost (Thẻ tín dụng, Khoản vay, Tiết kiệm) được nạp trực tiếp vào bộ nhớ trong tiến trình khởi chạy ứng dụng (`lifespan`).
  * **Kiểm tra sức khỏe chủ động (Probes)**:
    * `readinessProbe`: Ingress chỉ dẫn traffic vào Pod khi mô hình AI đã hoàn tất nạp vào RAM.
    * `livenessProbe`: Tự động khởi động lại container nếu tiến trình backend bị treo hoặc rò rỉ bộ nhớ.
  * **Cấu hình động (ConfigMap Override)**: Router được liên kết qua VolumeMounts, cho phép cập nhật router AI, Auth, Applications (Outbox) và SRE Ops mà không cần tốn thời gian build lại Docker Image.

### 3.4. Lớp Giao Diện Người Dùng (Presentation Layer - Frontend)
* **File cấu hình**: `k8s/03-frontend.yaml` và `ConfigMap frontend-assets`
* **Đặc tính kỹ thuật**:
  * Ứng dụng ReactJS được biên dịch tĩnh (production build) và phục vụ qua một Web Server Nginx dung lượng siêu nhẹ (Alpine-based).
  * Tích hợp trang **Bảng điều khiển Quản trị Hạ tầng Cloud (`/admin/infrastructure`)** giúp kỹ sư vận hành thao tác trực quan.
  * Tích hợp theo dõi danh sách **Hồ sơ đăng ký từ xa** ngay trên Dashboard người dùng (`/`).

### 3.5. Lớp Cổng Vào & Điều Tiết Bảo Mật (Ingress, TLS & Rate Limiting)
* **File cấu hình**: `k8s/04-ingress.yaml`
* **Đặc tính kỹ thuật**:
  * Sử dụng **Nginx Ingress** tích hợp sẵn của K3s.
  * **Path-based Routing**: `http://<NODE_IP>/api/*` chuyển tiếp tới Backend API; `http://<NODE_IP>/*` chuyển tiếp tới Frontend UI.
  * **Mã hóa TLSv1.3**: Bật SSL Termination và tiêu đề bắt buộc HSTS.
  * **Rate Limiting**: Giới hạn 25 RPS (Burst 50 requests) bảo vệ hệ thống khỏi tấn công DDoS và vét cạn.

### 3.6. Lớp Tự Động Co Giãn Đàn Hồi (Auto-scaling Layer - HPA)
* **File cấu hình**: `k8s/05-hpa.yaml`
* **Nguyên lý vận hành**:
  * `backend-api` được gán định mức tài nguyên: `requests` (CPU 200m, RAM 512Mi) và `limits` (CPU 1000m, RAM 1Gi).
  * **Metrics Server** liên tục thu thập mức tiêu thụ CPU thực tế của các Pods.
  * Co giãn tự động từ **2 đến 8 Pods** khi mức CPU vượt ngưỡng **70%**.

### 3.7. Lớp Cô Lập Mạng & Sao Lưu Dự Phòng (Security & Disaster Recovery)
* **File cấu hình**: `k8s/07-network-policy.yaml`, `k8s/08-pdb.yaml`, `k8s/09-backup.yaml`, `k8s/rbac-ops.yaml`
* **Đặc tính kỹ thuật**:
  * **NetworkPolicy**: Cô lập triệt để cổng PostgreSQL 5432, chỉ chấp nhận kết nối từ `backend-api` và `pg-backup`.
  * **PodDisruptionBudget**: Đảm bảo luôn duy trì tối thiểu 1 Pod hoạt động trong suốt quá trình nâng cấp hoặc bảo trì.
  * **CronJob Sao Lưu**: Tạo bản nén `.sql.gz` tự động lúc 02:00 sáng hàng ngày và giữ 7 ngày; hỗ trợ khởi chạy Job sao lưu On-demand.
  * **In-Cluster RBAC**: Cấp quyền `backend-k8s-viewer` cho ServiceAccount `default` để Backend API truy xuất pods, events, cronjobs cho SRE Dashboard.

---

## ⚡ 4. Quy Trình Khởi Chạy Tự Động (One-Click Deployment Workflow)

Toàn bộ hạ tầng được tự động hóa thông qua kịch bản `deploy.sh` theo thứ tự tuần tự nghiêm ngặt để tránh lỗi phụ thuộc:

```text
[BƯỚC 1] Khởi tạo Namespace & Secret (Bao gồm Secret mật khẩu DB và Secret TLS)
    │
    ▼
[BƯỚC 2] Triển khai PostgreSQL StatefulSet & Chờ PVC 5Gi sẵn sàng
    │
    ▼
[BƯỚC 3] Nạp ConfigMap ghi đè cấu hình Router Backend (AI, Outbox, SRE Ops) & Frontend Assets
    │
    ▼
[BƯỚC 4] Cấu hình RBAC in-cluster (Role & RoleBinding cho SRE Dashboard)
    │
    ▼
[BƯỚC 5] Khởi tạo đồng thời Backend API & Frontend UI Deployments
    │
    ▼
[BƯỚC 6] Đợi Probes xác nhận AI Engine sẵn sàng (Backend Ready - 3 models loaded)
    │
    ▼
[BƯỚC 7] Áp dụng Ingress Gateway (TLS & Rate Limit), NetworkPolicy, PDB, CronJob Backup
    │
    ▼
[BƯỚC 8] Kích hoạt chính sách HPA và chạy seed dữ liệu mẫu hoàn tất
```

---

## 🛠️ 5. Các Câu Lệnh Vận Hành & Giám Sát Cốt Lõi

```bash
# 1. Khởi chạy toàn bộ hạ tầng bằng một lệnh duy nhất
./scripts/deploy.sh

# 2. Xem toàn bộ trạng thái tài nguyên trong Namespace
kubectl get all,ing,hpa,cm,secret,pdb,netpol,cronjob -n vib-banking

# 3. Theo dõi mức tiêu thụ tài nguyên thời gian thực
kubectl top pods -n vib-banking

# 4. Giám sát hành vi tự động co giãn của HPA trong lúc thử tải
kubectl get hpa -n vib-banking -w

# 5. Chạy bộ kiểm thử tự động toàn diện 22 bài
python3 scripts/test_master.py --url http://172.17.242.190
```
