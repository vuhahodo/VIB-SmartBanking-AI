# 📘 Runbook Vận Hành & Xử Lý Sự Cố Hạ Tầng Cloud (VIB-SmartBanking-AI)

> **Namespace**: `vib-banking`  
> **Ingress IP**: `172.17.242.190`  
> **Trang Quản Trị SRE**: `http://172.17.242.190/admin/infrastructure`  
> **Tài liệu dành cho**: Kỹ sư Vận hành Hạ tầng Cloud (DevOps / SRE)

---

## ⚡ Các Lệnh Kiểm Tra & Phản Ứng Nhanh (SRE Quick Reference)

```bash
# 1. Kiểm tra tổng quan toàn bộ tài nguyên trong namespace
kubectl get all,ing,hpa,pdb,netpol,cronjob -n vib-banking

# 2. Xem 20 sự kiện gần nhất của cụm (Root Cause Analysis)
kubectl get events -n vib-banking --sort-by=.lastTimestamp | tail -20

# 3. Xem log thời gian thực của backend API
kubectl logs deploy/backend-api -n vib-banking --tail=50 -f

# 4. Kiểm tra mức tiêu thụ CPU/RAM thực tế (Metrics Server)
kubectl top pods -n vib-banking

# 5. Chạy bộ kiểm định toàn diện 22 bài tự động
python3 scripts/test_master.py --url http://172.17.242.190
```

---

## 🖥️ 1. Sử Dụng Bảng Điều Khiển SRE (`/admin/infrastructure`) Để Xử Lý Nhanh

Kỹ sư vận hành không nhất thiết phải dùng CLI trong mọi tình huống. Bảng điều khiển SRE cung cấp các công cụ trực quan:
- **Kiểm tra nhịp tim cơ sở dữ liệu**: Xem độ trễ PostgreSQL roundtrip latency (bình thường < 5ms). Nếu hiện **Offline (Mô phỏng đứt gãy)** hoặc độ trễ > 100ms, cần can thiệp.
- **Giám sát hàng đợi Outbox**: Số đơn tồn đọng trong bộ đệm `/tmp/vib_outbox`. Bình thường là `0 đơn`. Nếu DB gặp sự cố, số đơn sẽ tăng lên. Khi DB online trở lại, bộ đếm tự động giảm về `0` nhờ tiến trình `vib_outbox_reconciler`.
- **Nút "Ép buộc đối soát Outbox ngay"**: Dùng khi DB vừa được phục hồi và SRE muốn đồng bộ ngay lập tức mà không cần chờ chu kỳ quét 2s.
- **Nút "Kích hoạt Sao lưu Database On-demand"**: Khởi chạy ngay lập tức một K8s Job từ CronJob `pg-backup` tạo file nén `.sql.gz` trước các đợt bảo trì lớn.
- **Nút "Bơm Tải Đột Biến (Stress Test)"**: Bơm 60 phép tính AI đồng thời để kiểm chứng phản ứng co giãn của HPA.

---

## 🚨 2. Các Kịch Bản Sự Cố & Quy Trình Khắc Phục Chuẩn (SOP)

### Sự Cố 1: Pod Backend hoặc Frontend bị Crash / Xóa nhầm
* **Triệu chứng**: Một hoặc nhiều pod backend chuyển sang `Terminating`, `Error` hoặc biến mất khỏi danh sách.
* **Cơ chế tự động của K8s**:
  - `Deployment` và `ReplicaSet` tự động sinh Pod thay thế ngay lập tức.
  - Nhờ cấu hình `maxUnavailable: 0` và `PodDisruptionBudget` (tối thiểu 1 pod hoạt động), Ingress Nginx định tuyến 100% traffic sang pod còn lại. Người dùng **không bị gián đoạn hay lỗi 502**.
* **Đo lường thời gian hồi phục (RTO)**:
  ```bash
  python3 scripts/recovery_test.py --url http://172.17.242.190
  ```
  *(Thời gian RTO thực tế ghi nhận: ~44.3 giây để Pod mới unpickle đủ 3 mô hình XGBoost và vượt qua readiness probe).*
* **Xử lý thủ công (Nếu Pod rơi vào CrashLoopBackOff)**:
  ```bash
  kubectl logs -l app=backend-api -n vib-banking --tail=100 --previous
  kubectl describe pod -l app=backend-api -n vib-banking
  ```

---

### Sự Cố 2: Cơ Sở Dữ Liệu PostgreSQL Mất Kết Nối / Crash Vật Lý
* **Triệu chứng**:
  - PostgreSQL Pod bị xóa hoặc crash.
  - Trên SRE Dashboard: Card Cơ sở dữ liệu chuyển màu đỏ `Offline (Mất kết nối)`.
  - Backend API log báo: `OperationalError: could not connect to server`.
* **Cơ chế tự động chịu thảm họa (Zero Data Loss)**:
  - Các request đăng ký dịch vụ từ xa không bị văng lỗi 500. Backend tự động chuyển đơn vào **Local Outbox Buffer** (`/tmp/vib_outbox`) và phản hồi `HTTP 202 Accepted` (`status: QUEUED_OFFLINE`).
  - `StatefulSet` tự động khởi động lại `postgres-0` và gắn lại PVC `postgres-pvc` (5Gi), dữ liệu 290.000 khách hàng vẫn còn nguyên vẹn.
* **Quy trình phục hồi & Đối soát bù (Reconciliation)**:
  - Khi Pod `postgres-0` chuyển trạng thái `1/1 Running`:
    - Tiến trình ngầm `vib_outbox_reconciler` tự động quét các file JSON trong bộ đệm và nạp bù vào PostgreSQL.
    - Hoặc SRE có thể bấm nút **"Ép buộc đối soát Outbox ngay"** trên giao diện `/admin/infrastructure` hoặc gọi API:
      ```bash
      curl -X POST http://172.17.242.190/api/ops/sync-outbox
      ```
  - Kiểm tra số lượng đơn trong bộ đệm trở về `0`.

---

### Sự Cố 3: Dịch Vụ AI Thẩm Định Quá Tải hoặc Timeout (> 1.5s)
* **Triệu chứng**: Thời gian tính toán đặc trưng và suy luận XGBoost vượt quá 1.5 giây do tài nguyên CPU tăng cao.
* **Cơ chế tự động phòng hộ (Graceful Degradation)**:
  - Circuit Breaker tự động ngắt luồng AI, kích hoạt **Rule-based Fallback Engine**.
  - Đánh giá dựa trên quy tắc thu nhập và thâm niên để cấp hạn mức tạm thời hoặc đưa vào trạng thái `PENDING_REVIEW`.
  - Khách hàng nhận được phản hồi `HTTP 201 Created` kèm ghi chú chế độ phục hồi, không xảy ra treo hay timeout kết nối.
* **Xử lý vận hành**:
  - Kiểm tra tải CPU của cụm: `kubectl top pods -n vib-banking`.
  - HPA sẽ tự động phát hiện CPU > 70% và scale thêm bản sao backend để giảm tải.

---

### Sự Cố 4: Khách Hàng Gửi Trùng Lặp Yêu Cầu (Duplicate Retries / Double-Click)
* **Triệu chứng**: Mạng khách hàng chập chờn hoặc người dùng bấm liên tục nhiều lần nút "Gửi hồ sơ".
* **Cơ chế bảo vệ (Idempotency Key)**:
  - Request mang header `X-Idempotency-Key`.
  - Backend kiểm tra khóa định danh trong DB. Nếu đã tồn tại đơn cùng khóa, trả về ngay hồ sơ trước đó với `is_duplicate: true` (HTTP 200).
  - Không sinh bản ghi rác và không kích hoạt lại tiến trình AI tốn tài nguyên.

---

### Sự Cố 5: Tăng Đột Biến Lưu Lượng Truy Cập (Traffic Surge / Quá Tải HPA)
* **Triệu chứng**: Số lượng request AI tăng đột biến, CPU backend vượt ngưỡng 70%.
* **Cơ chế tự động co giãn đàn hồi**:
  - HPA phát hiện CPU vượt ngưỡng 70%, tự động nâng số lượng Pods từ **2** lên tối đa **8 Pods**.
  - Khi lưu lượng giảm trở lại, HPA tự động thu gọn Pods về mức tối thiểu 2 Pods sau chu kỳ làm nguội (cool-down period).
* **Theo dõi hành vi co giãn**:
  ```bash
  kubectl get hpa -n vib-banking -w
  ```
* **Xử lý thủ công nếu tải vượt quá 8 Pods**:
  ```bash
  # Tăng ngưỡng tối đa của HPA lên 12 Pods
  kubectl patch hpa backend-api-hpa -n vib-banking -p '{"spec":{"maxReplicas":12}}'
  ```

---

### Sự Cố 6: Mất Mát Dữ Liệu Nặng (Khôi Phục Từ Bản Sao Lưu Backup)
* **Cơ chế sao lưu**:
  - CronJob `pg-backup` tự động dump toàn bộ database lúc 02:00 hàng ngày, nén `.sql.gz` lưu vào PVC `pg-backups`, tự động dọn dẹp các bản ghi cũ hơn 7 ngày.
* **Tạo bản sao lưu ngay lập tức (On-demand)**:
  - Bấm nút **"Kích hoạt Sao lưu Database"** trên SRE Dashboard hoặc chạy lệnh:
    ```bash
    kubectl create job --from=cronjob/pg-backup pg-backup-manual-$(date +%s) -n vib-banking
    ```
* **Quy trình khôi phục dữ liệu**:
  ```bash
  # 1. Xem danh sách các bản sao lưu có sẵn
  kubectl logs job/<ten-job-backup-gan-nhat> -n vib-banking

  # 2. Chạy Pod tạm thời có quyền truy cập NetworkPolicy (nhãn app=pg-backup)
  # và nạp lại snapshot vào PostgreSQL
  gunzip -c /backup/vib_db_<ngay>.sql.gz | PGPASSWORD=vib_secret_2026 psql -h postgres-svc -U vib_admin -d vib_db
  ```

---

### Sự Cố 7: Số Lần Restart Pod PostgreSQL Tăng Cao
* **Triệu chứng**: Cột Restarts của `postgres-0` hiển thị số lớn (ví dụ: 30 lần).
* **Nguyên nhân cốt lõi**:
  - Trường `restartCount` trong Kubernetes là **số đếm tích lũy trong toàn bộ tuổi thọ của Pod** (ví dụ: Pod đã sống 495 giờ / 20 ngày qua nhiều lần máy trạm sleep/wake hoặc restart service k3s với exit code 0).
  - Đây **không phải là CrashLoopBackOff**. Trạng thái thực tế vẫn là `1/1 Running`.
* **Quy trình chuẩn hóa lại số đếm nếu cần thiết**:
  ```bash
  # Xóa Pod để StatefulSet tự tạo lại Pod mới (PVC 5Gi bảo toàn dữ liệu, restarts reset về 0)
  kubectl delete pod postgres-0 -n vib-banking
  ```

---

## 🛡️ 3. Kiểm Tra An Ninh & Tuân Thủ (Security Audit Runbook)

Để đảm bảo cụm không bị xâm nhập hoặc rò rỉ dữ liệu, chạy bộ kiểm định bảo mật định kỳ:

```bash
python3 scripts/test_security.py --url http://172.17.242.190
```

Các tiêu chí được xác minh tự động:
1. **HTTPS / TLSv1.3 & HSTS**: Kiểm tra mã hóa đường truyền, cổng 443 với chứng chỉ TLS Ingress.
2. **Rate Limiting**: Bơm chuỗi 60 requests/giây để xác nhận Ingress Nginx trả mã `HTTP 503 / 429` ngăn chặn tấn công vét cạn / từ chối dịch vụ.
3. **NetworkPolicy Isolation**: Khởi tạo Pod lạ `security-audit` cố tình quét cổng PostgreSQL 5432 và xác nhận kết nối bị chặn hoàn toàn.
4. **Anti-IDOR**: Thử dùng token của khách hàng này để đọc dữ liệu khách hàng khác và xác nhận nhận về `HTTP 403 Forbidden`.
