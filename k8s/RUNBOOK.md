# Runbook xử lý sự cố – VIB-SmartBanking (namespace `vib-banking`)

Mỗi mục: **triệu chứng → kiểm tra → xử lý → ghi chú**. Phần "tự động" do Kubernetes làm sẵn, phần "thủ công" người vận hành làm.

## Lệnh kiểm tra nhanh
```bash
kubectl get pods,hpa,ingress,pdb,networkpolicy,cronjob -n vib-banking
kubectl get events -n vib-banking --sort-by=.lastTimestamp | tail -20
kubectl logs deploy/backend-api -n vib-banking --tail=50
kubectl describe pod <ten-pod> -n vib-banking
python scripts/verify_cloud.py --url http://<node-ip>
```

## 1. Pod backend/frontend bị xoá hoặc crash
- **Tự động:** ReplicaSet tạo pod mới ngay. Vì luôn có tối thiểu 2 pod, người dùng vẫn được phục vụ.
- **Đo:** `python scripts/recovery_test.py --url http://<node-ip>` (thời gian hồi phục, số request lỗi).
- **Thủ công nếu pod cứ crash lặp lại:** `kubectl logs <pod> --previous`, `kubectl describe pod <pod>`.

## 2. Ứng dụng bị treo
- **Tự động:** liveness probe `/health` thất bại, kubelet khởi động lại container.
- **Thủ công:** xem số lần restart bằng `kubectl get pods`; nếu restart liên tục, xem log để tìm nguyên nhân.

## 3. Pod chưa sẵn sàng hoặc cơ sở dữ liệu chưa lên
- **Tự động:** readiness probe `/ready` thất bại, pod bị rút khỏi Service nên không nhận request; init container `wait-for-postgres` chờ DB mở cổng.
- **Thủ công:** `kubectl get pods -n vib-banking`, kiểm tra `postgres-0` đã Ready chưa.

## 4. Quá tải
- **Tự động:** HPA tăng pod khi CPU vượt 70% (backend 2 đến 8 pod).
- **Thủ công:** nếu đã đạt 8 pod mà vẫn chậm, tăng `maxReplicas` hoặc thêm node cho cụm. Theo dõi: `kubectl get hpa -n vib-banking -w`.

## 5. Pod PostgreSQL bị xoá
- **Tự động:** StatefulSet tạo lại `postgres-0` và gắn lại PVC `pgdata`, dữ liệu còn nguyên.
- **Ghi chú:** dịch vụ DB gián đoạn ngắn vì chỉ có 1 bản sao.

## 6. Mất hoặc hỏng dữ liệu (khôi phục từ sao lưu)
- **Tự động:** CronJob `pg-backup` chạy 02:00 mỗi ngày, ghi file `vib_db_<ngày>.sql.gz` vào PVC `pg-backups`, giữ 7 ngày.
- **Chạy sao lưu ngay:** `kubectl create job --from=cronjob/pg-backup pg-backup-manual -n vib-banking`
- **Xem các bản sao lưu:** log của Job sao lưu gần nhất kết thúc bằng `ls -lh /backup`: `kubectl logs job/<ten-job> -n vib-banking`.
- **Khôi phục (thủ công):** chạy một pod tạm gắn PVC `pg-backups`, rồi
  ```bash
  gunzip -c /backup/<file>.sql.gz | PGPASSWORD=<mat-khau> psql -h postgres-svc -U vib_admin -d vib_db
  ```
  Nếu dữ liệu hỏng nặng, tạo lại database trước khi nạp. Pod tạm phải có nhãn `app=pg-backup` để được NetworkPolicy cho phép.
- **Hạn chế:** sao lưu nằm cùng cụm; production đẩy ra object storage.

## 7. Cập nhật bản mới bị lỗi
- **Tự động:** rolling update với `maxUnavailable: 0`, readiness probe không cho pod lỗi nhận request nên bản cũ vẫn phục vụ.
- **Thủ công:** `kubectl rollout status deploy/backend-api -n vib-banking`; quay lại bản trước bằng `kubectl rollout undo deploy/backend-api -n vib-banking`.

## 8. Bảo trì node (drain)
- **Tự động:** PodDisruptionBudget giữ lại tối thiểu 1 pod backend và 1 pod frontend khi `kubectl drain`.

## Chưa xử lý (nói rõ khi trình bày)
- **Node hỏng:** phụ thuộc số node của cụm (`kubectl get nodes`). Nếu cụm chỉ có 1 node thì chưa sẵn sàng cao ở mức node.
- **Giám sát và cảnh báo:** chưa có Prometheus/Grafana, phát hiện sự cố bằng kubectl và probe.
- **HTTPS/TLS, Secret thật (Vault, Sealed Secrets), giới hạn tần suất request, quét lỗ hổng image.**
