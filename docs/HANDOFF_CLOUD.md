# Bàn giao phần Điện toán đám mây (cập nhật 03/11/2026)

Dành cho team tiếp tục phát triển để hoàn thiện bài môn Điện toán đám mây. Đọc file này trước, sau đó xem `k8s/RUNBOOK.md`.

## 1. Đã làm và đã kiểm chứng
Kiểm chứng trên Kubernetes của **Docker Desktop** (1 node), 19 PASS / 0 FAIL bằng `python scripts/verify_cloud.py --run-backup`.

| Nội dung | File |
|---|---|
| Namespace, Secret (đã tắt `DEMO_MODE`) | `k8s/00-namespace-secrets.yaml` |
| PostgreSQL StatefulSet, PVC 5Gi | `k8s/01-postgres.yaml` |
| Job nạp dữ liệu mẫu | `k8s/01.5-seed-job.yaml` |
| Backend: probe, requests/limits, rolling update `maxUnavailable: 0`, bỏ đặc quyền | `k8s/02-backend.yaml` |
| Frontend: probe, rolling update | `k8s/03-frontend.yaml` |
| Ingress theo đường dẫn | `k8s/04-ingress.yaml` |
| HPA backend 2→8 (70% CPU), frontend 2→5 (80%) | `k8s/05-hpa.yaml` |
| Job tạo tải trong cụm | `k8s/06-load-generator.yaml` |
| NetworkPolicy: chỉ backend và job nạp, sao lưu vào PostgreSQL | `k8s/07-network-policy.yaml` |
| PodDisruptionBudget (giữ tối thiểu 1 pod mỗi tầng) | `k8s/08-pdb.yaml` |
| CronJob sao lưu `pg_dump` 02:00 mỗi ngày, giữ 7 ngày | `k8s/09-backup.yaml` |
| Quy trình xử lý sự cố | `k8s/RUNBOOK.md` |
| Build, deploy, tải, kiểm tra, đo phục hồi | `scripts/` |
| Slide và script thuyết trình bản cuối | `docs/presentation/` |

## 2. Cách chạy
```bash
bash scripts/build_images.sh        # hoặc build_images.ps1; nạp image vào cụm nếu cụm không dùng chung kho image
bash scripts/deploy.sh              # hoặc deploy.ps1 (đã gồm 07, 08, 09)
python scripts/verify_cloud.py --url http://<địa-chỉ-vào-cụm> --run-backup
```
Đăng nhập demo: `00992830` / `123456`. Vì `DEMO_MODE=false`, màn hình đăng nhập không liệt kê tài khoản.

## 3. Việc còn lại để hoàn thiện (theo thứ tự)
1. **Cài Ingress controller (nginx) và metrics-server** trên cụm của team. Chưa cài được ở máy bàn giao nên HPA hiện `cpu: <unknown>`. Với cụm kind hoặc Docker Desktop, metrics-server cần thêm `--kubelet-insecure-tls`.
2. **Chạy đo tải và tự phục hồi thật** rồi điền số vào các ô `[SỐ ĐO]` ở slide 10:
   ```bash
   python scripts/load_test.py --url http://<địa-chỉ> --duration 90 --concurrency 30
   python scripts/recovery_test.py --url http://<địa-chỉ>
   ```
   `recovery_test.py` cần đi qua Ingress (không dùng `kubectl port-forward` vì nó chỉ bám một pod).
3. **Thống nhất tên nền tảng.** Slide và Word đang ghi "K3s", trong khi máy bàn giao chạy Kubernetes của Docker Desktop. Nếu team dùng K3s thì giữ nguyên, nếu không thì sửa chữ trong slide.
4. **Ghi số node** (`kubectl get nodes`) để trả lời câu hỏi "mất node thì sao".
5. Nếu mục nào trong `verify_cloud.py` báo FAIL trên máy team, sửa slide theo bảng ở mục 8 của file Word kịch bản.

## 4. Chưa có (đã nói rõ trên slide, có thể làm thêm để mạnh hơn)
- HTTPS/TLS (Ingress đang HTTP), Secret thật (Vault hoặc Sealed Secrets), giới hạn tần suất request, quét lỗ hổng image.
- Giám sát (Prometheus/Grafana), CI/CD (ArgoCD), PostgreSQL nhiều bản sao, đẩy sao lưu ra object storage, xử lý node hỏng (cần nhiều node).
- Lưu ý bảo mật: `web/backend/app/config.py` đang để mặc định mật khẩu DB và khoá JWT dạng mẫu; Secret trong `k8s/00-namespace-secrets.yaml` cũng là giá trị mẫu. Không dùng cho production.

## 5. Không commit
`k8s/dashboard-token.txt` (token Dashboard), video, ảnh chụp, file `.db`.
