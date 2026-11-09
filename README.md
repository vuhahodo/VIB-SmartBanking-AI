# 🏦 VIB-SmartBanking-AI: Hệ Thống Ngân Hàng Số & Hạ Tầng Điện Toán Đám Mây Chịu Lỗi Cao

[![Kubernetes](https://img.shields.io/badge/Kubernetes-K3s-blue.svg?logo=kubernetes)](https://k3s.io)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-ReactJS-61DAFB.svg?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2015-336791.svg?logo=postgresql)](https://www.postgresql.org)
[![XGBoost](https://img.shields.io/badge/AI%20Engine-XGBoost-orange.svg)](https://xgboost.readthedocs.io)
[![Tests](https://img.shields.io/badge/Tests-22%2F22%20PASS%20(100%25)-brightgreen.svg)]()

> Nghiên cứu, phát triển và vận hành hệ thống ngân hàng số **VIB SmartBanking** tích hợp trí tuệ nhân tạo (AI Next-Best-Action Cross-Sell) thời gian thực trên tập dữ liệu thực tế **290.223 khách hàng** (VIB Hackathon Datarathon). Toàn bộ hệ thống được triển khai trên nền tảng **Kubernetes (K3s)** với cơ chế cân bằng tải, tự động co giãn đàn hồi (HPA), bảo mật toàn diện và kiến trúc **đăng ký dịch vụ từ xa chịu lỗi thảm họa (Disaster Recovery & Zero Data Loss)**.

---

## 📑 Mục lục
1. [Tổng quan Kiến trúc Hệ thống](#-tổng-quan-kiến-trúc-hệ-thống)
2. [Các Chức Năng Mới & Giải Pháp Kỹ Thuật Đột Phá](#-các-chức-năng-mới--giải-pháp-kỹ-thuật-đột-phá)
   - [Đăng ký Dịch vụ Từ xa Chịu lỗi Cao (Remote Registration Resilience)](#1-đăng-ký-dịch-vụ-từ-xa-chịu-lỗi-cao-remote-registration-resilience)
   - [Bảng Điều Khiển Quản Trị Hạ Tầng SRE / DevOps (/admin/infrastructure)](#2-bảng-điều-khiển-quản-trị-hạ-tầng-sre--devops-admininfrastructure)
   - [Bảo Mật & An Ninh Hạ Tầng Toàn Diện (PCI-DSS Ready)](#3-bảo-mật--an-ninh-hạ-tầng-toàn-diện-pci-dss-ready)
   - [Theo dõi Hồ sơ Đăng ký trên Dashboard Khách hàng](#4-theo-dõi-hồ-sơ-đăng-ký-trên-dashboard-khách-hàng)
3. [Công nghệ Sử dụng (Tech Stack)](#-công-nghệ-sử-dụng-tech-stack)
4. [Cấu trúc Thư mục Dự án](#-cấu-trúc-thư-mục-dự-án)
5. [Hướng Dẫn Cài Đặt & Vận Hành Cụm Kubernetes](#-hướng-dẫn-cài-đặt--vận-hành-cụm-kubernetes)
6. [Tài Khoản Demo & Truy Cập Dịch Vụ](#-tài-khoản-demo--truy-cập-dịch-vụ)
7. [Kiểm Thử Toàn Diện (Master Test Suite 22/22 Pass)](#-kiểm-thử-toàn-diện-master-test-suite-2222-pass)

---

## 🏛️ Tổng quan Kiến trúc Hệ thống

Toàn bộ dịch vụ được triển khai và cô lập trong namespace Kubernetes `vib-banking`:

```mermaid
graph TD
    Client["Client Browser / SRE Admin<br/>(172.17.242.190)"] -->|HTTP / HTTPS TLSv1.3| Ingress["Nginx Ingress Controller<br/>Rate Limiting: 25 RPS (Burst 50)"]

    Ingress -->|/* (UI Traffic)| SvcFrontend["Service: frontend<br/>(ClusterIP: 80)"]
    Ingress -->|/api/* (API Traffic)| SvcBackend["Service: backend-api<br/>(ClusterIP: 8000)"]

    SvcFrontend --> PodFrontend1["Pod: frontend-ui-1"]
    SvcFrontend --> PodFrontend2["Pod: frontend-ui-2"]

    SvcBackend --> PodBackend1["Pod: backend-api-1 (FastAPI)"]
    SvcBackend --> PodBackend2["Pod: backend-api-2 (FastAPI)"]
    
    HPA["HPA: backend-api-hpa<br/>(2 - 8 Pods @ 70% CPU)"] -.->|Co giãn đàn hồi| PodBackend1
    HPA -.->|Co giãn đàn hồi| PodBackend2

    PodBackend1 --> SvcDB["Service: postgres<br/>(ClusterIP: 5432)"]
    PodBackend2 --> SvcDB

    SvcDB --> StatefulDB["StatefulSet: postgres-0<br/>(PVC 5Gi Persistent Storage)"]

    Backup["CronJob: pg-backup<br/>(02:00 Hàng ngày / On-Demand)"] --> StatefulDB
    OutboxBuffer["Local Outbox Buffer<br/>(/tmp/vib_outbox)"] -.->|Đồng bộ tự động khi DB sống lại| StatefulDB

    NetPol["NetworkPolicy<br/>Cô lập DB Port 5432"] --- StatefulDB
```

---

## 🚀 Các Chức Năng Mới & Giải Pháp Kỹ Thuật Đột Phá

### 1. Đăng ký Dịch vụ Từ xa Chịu lỗi Cao (Remote Registration Resilience)
Đáp ứng bài toán thực tế của ngân hàng số khi khách hàng mở thẻ/vay vốn trực tuyến trong các điều kiện mạng chập chờn, dịch vụ AI quá tải hoặc cơ sở dữ liệu gặp sự cố:

- **Luồng Chuẩn (Happy Path - Trực tiếp)**:
  - Tiếp nhận đầy đủ hồ sơ định danh (`full_name`, `phone`, `email`, thu nhập, hạn mức đề xuất).
  - Hệ thống AI thẩm định tức thì với 3 mô hình XGBoost, xếp hạng rủi ro tín dụng và gán hạn mức sơ bộ (`PRE_APPROVED`).
  - Phản hồi tức thì `HTTP 201 Created` kèm hạn mức và mã hồ sơ.
- **Cơ chế Chống Trùng lặp (Idempotency Protection)**:
  - Header `X-Idempotency-Key` (hoặc `Idempotency-Key`) bắt trọn các yêu cầu gửi trùng do khách hàng nhấn đúp hoặc mạng rớt gửi lại.
  - Trả về ngay hồ sơ đã tạo (`HTTP 200 OK`, `is_duplicate: true`), bảo vệ hệ thống khỏi việc tạo đơn trùng lặp và tránh chạy lại AI tốn tài nguyên.
- **Cơ chế Suy giảm Mềm dẻo (Graceful Degradation - AI Fallback)**:
  - Circuit Breaker giám sát dịch vụ AI. Khi suy luận AI bị timeout (> 1.5s) hoặc lỗi, hệ thống tự động kích hoạt **Rule-based Fallback Engine** (thẩm định dựa trên tập luật thu nhập và thâm niên).
  - Hồ sơ được chuyển trạng thái `PENDING_REVIEW` hoặc phê duyệt sơ bộ hạn mức an toàn, đảm bảo giao dịch đăng ký của người dùng **không bao giờ bị gián đoạn hay trả về lỗi 500**.
- **Mô hình Outbox Đảm bảo Không Mất Dữ Liệu (Physical DB Crash - Zero Data Loss)**:
  - Khi PostgreSQL gặp sự cố vật lý hoặc mất kết nối:
    - Backend bắt ngoại lệ kết nối, tự động chuyển đơn vào hàng đợi **Local Outbox Buffer** (`/tmp/vib_outbox`).
    - Phản hồi khách hàng với mã `HTTP 202 Accepted` (`status: QUEUED_OFFLINE`), thông báo hồ sơ đã được tiếp nhận an toàn trong bộ nhớ đệm.
    - Tiến trình chạy ngầm **Auto-Reconciliation Daemon (`vib_outbox_reconciler`)** liên tục thăm dò trạng thái DB mỗi 2 giây. Khi DB phục hồi kết nối, toàn bộ đơn trong bộ đệm được nạp bù tự động vào PostgreSQL với đầy đủ tính toàn vẹn dữ liệu.
    - Hỗ trợ đối soát cưỡng bức thông qua API `POST /api/ops/sync-outbox`.

---

### 2. Bảng Điều Khiển Quản Trị Hạ Tầng SRE / DevOps (`/admin/infrastructure`)
Trang chuyên biệt dành riêng cho kỹ sư vận hành (DevOps / SRE) để giám sát nhịp tim hệ thống và chủ động ứng phó tức thì trước các sự cố thảm họa:

* **Đường dẫn truy cập**: `http://172.17.242.190/admin/infrastructure` (Hoặc menu **Hạ tầng Cloud** với huy hiệu `DevOps` trên thanh điều hướng).
* **Giám sát Sức Khỏe Thời Gian Thực (Live Health Vitals)**:
  - **PostgreSQL**: Đo độ trễ kết nối thực tế round-trip latency (ms), trạng thái ổ đĩa PVC (5Gi), trạng thái cô lập NetworkPolicy.
  - **Bộ đệm Outbox**: Đếm số lượng đơn tồn đọng trong bộ đệm `/tmp/vib_outbox`, trạng thái luồng tiến trình tự động đối soát (Running / Paused).
  - **Co giãn HPA**: Giám sát số Pod backend hiện tại (2 - 8 pods), phần trăm sử dụng CPU trung bình theo thời gian thực (so với ngưỡng 70%), chính sách RollingUpdate không gián đoạn.
  - **Bảo mật & Cổng vào Ingress**: Trạng thái TLSv1.3 HTTPS, cấu hình Rate Limiting (25 RPS / Burst 50), bảo vệ IDOR (HTTP 403 Forbidden).
* **Giám sát Workloads Kubernetes Trực Tiếp**:
  - Truy vấn trực tiếp Kubernetes API in-cluster qua quyền RBAC `backend-k8s-viewer`.
  - Hiển thị danh sách đầy đủ 5 Pods (`backend-api`, `frontend-ui`, `postgres-0`) với IP nội bộ, trạng thái Ready, số lần khởi động lại (Restarts), Node và tuổi thọ Pod.
* **Nhật Ký Sự Kiện Cụm (Cluster Events)**:
  - Bắt luồng Kubernetes Events phục vụ điều tra nguyên nhân gốc rễ (Root Cause Analysis - RCA), theo dõi các sự kiện Pod scaling, sao lưu hoàn thành, Image pulling.
* **Bảng Thử Nghiệm Tác Động Hạ Tầng & Phản Ứng Nhanh (Interactive Cloud Test Lab)**:
  - 🔴 **Giả lập Sập Database (Chaos Test)**: Chủ động ngắt kết nối DB thông qua bảng `system_chaos` dùng chung cho toàn bộ các bản sao Backend để kiểm chứng cơ chế nộp đơn Outbox.
  - 🟢 **Khôi phục Kết Nối Database**: Bật lại DB và kích hoạt luồng đối soát tự động đồng bộ đơn tồn đọng.
  - ⚡ **Bơm Tải Đột Biến (CPU Stress Test)**: Bơm đồng loạt 60 phép tính AI XGBoost song song để đẩy CPU vượt ngưỡng 70% và kích hoạt HPA co giãn lên 5-8 Pods.
  - 🔄 **Ép buộc Đối soát Outbox Ngay**: Quét bộ nhớ đệm và nạp toàn bộ đơn tồn vào DB ngay lập tức.
  - 💾 **Kích hoạt Sao lưu Database On-demand**: Khởi tạo K8s Job từ CronJob `pg-backup` tạo file nén snapshot an toàn `.sql.gz`.
* **Live Terminal Console Tích hợp**:
  - Hiển thị trực tiếp kết quả trả về của các thao tác SRE (HTTP Status Code, Độ trễ phản hồi ms, Payload JSON) ngay trên giao diện web.

---

### 3. Bảo Mật & An Ninh Hạ Tầng Toàn Diện (PCI-DSS Ready)
Đã hoàn tất kiểm định an ninh và phòng thủ đa tầng:
- **Mã hóa Toàn Trình (Full-Transit Encryption)**: Cấu hình Ingress Nginx TLSv1.3 với chứng chỉ Secret `vib-tls-secret`, ép buộc chuẩn HSTS (`Strict-Transport-Security: max-age=31536000`).
- **Bảo vệ Chống Tấn Công Từ Chối Dịch Vụ (Rate Limiting)**: Nginx Ingress giới hạn tốc độ 25 requests/giây (Burst 50 requests), tự động trả mã `HTTP 503 / 429` khi có dấu hiệu bùng nổ traffic bất thường.
- **Cô Lập Mạng Cơ Sở Dữ Liệu (NetworkPolicy Isolation)**: Thiết lập Kubernetes NetworkPolicy chặn đứng 100% mọi truy cập vào cổng PostgreSQL 5432 từ các Pod lạ hoặc bị xâm nhập; chỉ chấp thuận Pod có nhãn `app=backend-api` và `app=pg-backup`.
- **Phòng Ngừa Rò Rỉ Dữ Liệu Ngang (Anti-IDOR Protection)**: Xác thực nghiêm ngặt JWT Claims, khách hàng bị chặn truy cập dữ liệu của khách hàng khác (`HTTP 403 Forbidden`).

---

### 4. Theo dõi Hồ sơ Đăng ký trên Dashboard Khách hàng
Tại màn hình Tổng quan (`/`), bổ sung phân khu **"Hồ sơ đăng ký từ xa của bạn"**:
- Khách hàng theo dõi danh sách tất cả các hồ sơ đã nộp từ xa kèm mã hồ sơ, thời gian nộp, hạn mức đề xuất và điểm rủi ro AI.
- Huy hiệu trạng thái trực quan: `PRE_APPROVED` (Phê duyệt trước), `PENDING_REVIEW` (Chờ thẩm định), `QUEUED_OFFLINE` (Đã lưu bộ đệm).
- Thể hiện rõ chế độ xử lý của hệ thống: `DIRECT_AI_APPROVED`, `RULE_BASED_FALLBACK`, `OUTBOX_OFFLINE_SAVED`.

---

## 🛠️ Công nghệ Sử dụng (Tech Stack)

| Tầng | Công nghệ | Chi tiết sử dụng |
|---|---|---|
| **Frontend** | ReactJS, Vite, TailwindCSS | Giao diện SmartBanking, trang quản trị SRE Dashboard, biểu đồ AI Insights |
| **Backend** | FastAPI, Python 3.11, Pydantic | API không trạng thái, nạp sẵn model vào RAM (Lifespan), Ops router |
| **AI / ML** | XGBoost, Scikit-learn, Joblib | 3 mô hình phân loại nhị phân Next-Best-Action (Thẻ, Tiết kiệm, Khoản vay) |
| **Database** | PostgreSQL 15 (Alpine) | StatefulSet gắn PVC 5Gi, Feature Store JSONB (290K+ hồ sơ khách hàng) |
| **Orchestration** | K3s (Lightweight Kubernetes) | Quản trị tài nguyên, Service, Deployment, StatefulSet, NetworkPolicy |
| **Load Balancing** | Nginx Ingress Controller | Cân bằng tải, định tuyến đường dẫn, Rate Limiting, SSL Termination |
| **Auto-scaling** | Kubernetes Metrics Server + HPA | Tự động co giãn backend từ 2 đến 8 replicas dựa trên CPU utilization (70%) |
| **Resilience & DR** | Outbox Pattern, CronJob pg-backup | Chống mất mát dữ liệu khi sập DB vật lý, sao lưu định kỳ hàng ngày |

---

## 📂 Cấu trúc Thư mục Dự án

```
VIB-SmartBanking-AI/
├── ai/                              # Phân hệ Trí tuệ Nhân tạo
│   ├── models/                      # 3 mô hình XGBoost .joblib + metrics
│   ├── predict.py                   # VIBRecommendationEngine suy luận thời gian thực
│   └── train_model.py               # Pipeline huấn luyện tự động
├── docs/                            # Tài liệu báo cáo & bàn giao
│   ├── HANDOFF_CLOUD.md             # Tài liệu bàn giao hạ tầng Cloud chi tiết
│   └── presentation/                # Slide thuyết trình và kịch bản demo
├── k8s/                             # Toàn bộ cấu hình Kubernetes Manifests
│   ├── 00-namespace-secrets.yaml    # Namespace & Secret bảo mật
│   ├── 01-postgres.yaml             # PostgreSQL StatefulSet & PVC 5Gi
│   ├── 01.5-backend-override.yaml   # ConfigMap nạp đè router backend
│   ├── 02-backend.yaml              # Deployment Backend API & Health Probes
│   ├── 03-frontend.yaml             # Deployment Frontend UI Nginx
│   ├── 04-ingress.yaml              # Ingress Nginx, TLS & Rate Limiting
│   ├── 05-hpa.yaml                  # Horizontal Pod Autoscaler (2 - 8 Pods)
│   ├── 07-network-policy.yaml       # Cô lập DB cổng 5432
│   ├── 08-pdb.yaml                  # PodDisruptionBudget đảm bảo HA
│   ├── 09-backup.yaml               # CronJob sao lưu pg_dump mỗi ngày
│   ├── rbac-ops.yaml                # RBAC cho phép Backend truy vấn K8s API
│   ├── README.md                    # Kiến trúc K8s chi tiết
│   ├── RUNBOOK.md                   # Sổ tay xử lý sự cố cho kỹ sư SRE
│   └── BUILD.md                     # Hướng dẫn đóng gói và triển khai
├── scripts/                         # Bộ kịch bản tự động hóa & kiểm thử
│   ├── test_master.py               # Master Test Suite kiểm thử 22 bài toàn diện
│   ├── test_security.py             # Bộ kiểm tra an ninh hạ tầng 4 bài
│   ├── test_registration.py         # Kiểm tra đăng ký từ xa chịu lỗi
│   ├── chaos_real_world_test.py     # Kiểm tra thảm họa sập DB & Outbox
│   ├── load_test.py                 # Kịch bản thử tải hệ thống
│   ├── recovery_test.py             # Kịch bản đo RTO phục hồi cụm
│   └── deploy.sh                    # Triển khai hạ tầng 1 chạm
├── web/
│   ├── backend/                     # FastAPI Backend Application
│   │   ├── app/routers/
│   │   │   ├── applications.py      # Router Đăng ký từ xa & Outbox Buffer
│   │   │   └── ops.py               # Router Quản trị Hạ tầng & Chaos API
│   │   └── README.md
│   └── frontend/                    # ReactJS Frontend Application
│       ├── src/pages/
│       │   ├── Infrastructure.jsx   # Giao diện SRE Dashboard Quản trị Cloud
│       │   └── Dashboard.jsx        # Giao diện Ngân hàng số & Theo dõi Hồ sơ
│       └── README.md
└── README.md
```

---

## ⚡ Hướng Dẫn Cài Đặt & Vận Hành Cụm Kubernetes

### 1. Triển khai hạ tầng lên K8s (Một chạm)
```bash
# Cấp quyền thực thi và chạy kịch bản deploy tự động
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 2. Kiểm tra trạng thái toàn bộ cụm
```bash
kubectl get all,ing,hpa,cronjob,pdb,netpol -n vib-banking
```

Toàn bộ 5 Pods phải ở trạng thái `1/1 Running`:
- `postgres-0`: 1/1 Running
- `backend-api-...`: 2 pods 1/1 Running
- `frontend-ui-...`: 2 pods 1/1 Running

---

## 🔑 Tài Khoản Demo & Truy Cập Dịch Vụ

- **Cổng vào Web Người dùng**: `http://172.17.242.190/` hoặc `https://172.17.242.190/`
- **Trang Quản trị Hạ tầng SRE**: `http://172.17.242.190/admin/infrastructure`
- **Tài liệu API Swagger**: `http://172.17.242.190/api/docs`

| Thông tin | Giá trị đăng nhập |
|---|---|
| **Mã khách hàng (Username)** | `00992830` |
| **Mật khẩu (Password)** | `123456` |
| **Chủ tài khoản** | Nguyễn Thị Minh Anh |
| **Số dư khả dụng** | 45.200.000 VNĐ |

---

## 🧪 Kiểm Thử Toàn Diện (Master Test Suite 22/22 Pass)

Dự án cung cấp bộ kịch bản kiểm thử tự động toàn diện bao quát tất cả các bài toán:

```bash
# Chạy toàn bộ 22 bài kiểm định tự động
python3 scripts/test_master.py --url http://172.17.242.190
```

### Bảng Kết Quả Kiểm Thử Thực Tế:
```text
========================================================================================
                  KẾT QUẢ TỔNG HỢP KIỂM ĐỊNH TOÀN DIỆN HẠ TẦNG VIB-SMARTBANKING
========================================================================================
 [PASS] 1. Kiểm tra Liveness Probe (/health)
 [PASS] 2. Kiểm tra Readiness Probe (/ready)
 [PASS] 3. Đăng nhập JWT Khách hàng Demo (00992830)
 [PASS] 4. Truy xuất Hồ sơ & Tài khoản Khách hàng
 [PASS] 5. Truy xuất Lịch sử Giao dịch
 [PASS] 6. Kiểm tra Danh mục Sản phẩm
 [PASS] 7. Kiểm tra Thẩm định AI Gợi ý Cá nhân hóa
 [PASS] 8. Kiểm tra Chỉ số Huấn luyện AI Model
 [PASS] 9. Đăng ký Dịch vụ: Luồng Chuẩn (Happy Path - HTTP 201)
 [PASS] 10. Đăng ký Dịch vụ: Chống Trùng lặp Yêu cầu (Idempotency - HTTP 200)
 [PASS] 11. Đăng ký Dịch vụ: Thẩm định Dự phòng khi AI Timeout (Rule Fallback)
 [PASS] 12. Đăng ký Dịch vụ: Cơ chế Outbox khi Sập DB (Chaos Test - HTTP 202)
 [PASS] 13. Đăng ký Dịch vụ: Tự động Đối soát & Phục hồi Đơn khi DB Sống lại
 [PASS] 14. Quản trị Hạ tầng: API Giám sát Pods & Workloads K8s (/api/ops/cluster)
 [PASS] 15. Quản trị Hạ tầng: API Kích hoạt Sao lưu DB Tức thì (/api/ops/trigger-backup)
 [PASS] 16. Quản trị Hạ tầng: API Thử Tải Đột biến CPU HPA (/api/ops/stress-test)
 [PASS] 17. Quản trị Hạ tầng: API Ép buộc Đối soát Bộ đệm Outbox (/api/ops/sync-outbox)
 [PASS] 18. An ninh & Bảo mật: Kiểm thử Mã hóa TLS/HTTPS & HSTS
 [PASS] 19. An ninh & Bảo mật: Kiểm thử Điều tiết Tần suất (Rate Limiting)
 [PASS] 20. An ninh & Bảo mật: Kiểm thử Cô lập Mạng Database (NetworkPolicy)
 [PASS] 21. An ninh & Bảo mật: Chống Rò rỉ Dữ liệu Khách hàng Ngang (Anti-IDOR)
 [PASS] 22. Kiểm thử Tải Đồng thời (Concurrency Load Test 10 Users)

>>> TỔNG KẾT: 22/22 BÀI KIỂM TRA ĐẠT (100.0%)!
>>> HỆ THỐNG VIB-SMARTBANKING-AI SẴN SÀNG VẬN HÀNH TRÊN MÔI TRƯỜNG CLOUD PRODUCTION!
========================================================================================
```
