# Bàn giao phần Điện toán đám mây (đã kiểm chứng ngày 10/11/2026)

Tài liệu này ghi những gì **đã chạy và đo thật** trên cụm, những lỗi đã sửa, và những gì còn thiếu. Mọi con số dưới đây đến từ lần chạy thật, không phải ước lượng.

## 1. Môi trường kiểm chứng
- Cụm: **K3s v1.37.2+k3s1** trong WSL2 Ubuntu 26.04 (1 node `desktop-pm1qg34`, containerd), Nginx Ingress (bare-metal, Service kiểu LoadBalancer qua ServiceLB của K3s), metrics-server và local-path có sẵn của K3s. Cài bằng `scripts/k3s_wsl_setup.sh`.
- Trước đó nhóm cũng đã đo trên Kubernetes của Docker Desktop; kết quả tương tự (HPA 2→8 sau ~55 giây, tự phục hồi 19,2–19,6 giây).
- Đăng nhập demo: `00992830` / `123456` (`DEMO_MODE=false` nên màn hình đăng nhập không liệt kê tài khoản).
- Image: `vib-backend:v4`, `vib-frontend:v2` (build trên Docker Desktop, nạp vào K3s bằng `docker save | k3s ctr images import -`; image không nằm trong git).
- Chạy các script kiểm tra/đo **trong WSL** (`python3 scripts/...`, địa chỉ `http://127.0.0.1`).

## 2. Kết quả kiểm thử đã chạy
| Bộ kiểm thử | Kết quả |
|---|---|
| `python scripts/test_master.py --url http://127.0.0.1` | 22/22 đạt |
| `python scripts/test_security.py --url http://127.0.0.1` | 4/4 đạt (HTTPS, rate limit, NetworkPolicy, IDOR) |
| `python scripts/test_registration.py --url http://127.0.0.1` | 5/5 đạt (AI chạy online, idempotency, AI lỗi, DB sập) |
| `python scripts/verify_cloud.py --url http://127.0.0.1 --run-backup` | 19/19 đạt (xem lưu ý NetworkPolicy ở mục 4) |

## 3. Số đo thật (K3s, qua Ingress, 1 node, ngày 10/11/2026)
| Chỉ số | Giá trị |
|---|---|
| Tải nhẹ (5 req/s) | p50 28 ms, p95 75 ms, 100% thành công |
| Tải 20 req/s trong 60 giây | 1.218 request, 100% thành công, p50 373 ms, p95 574 ms, p99 731 ms |
| HPA backend (mục tiêu 70% CPU) | 2 → 4 pod sau ~40 giây, 8 pod sau ~65 giây; CPU 151–294% rồi giảm về 86% |
| Tự phục hồi khi xoá 1 pod backend (2 lần đo) | pod mới Ready sau 19,65 s và 19,0 s; 0 request lỗi (49/49 và 48/48) |

Lệnh đo (trong WSL): `python3 scripts/load_test.py --url http://127.0.0.1 --duration 60 --concurrency 20 --rate 20` và `python3 scripts/self_healing_demo.py`. Chờ HPA về 2 pod (khoảng 5 phút) giữa các lần đo.

**Lưu ý khi đo:**
1. Ingress giới hạn 25 request/giây mỗi IP. Không có `--rate`, một luồng trên WSL (độ trễ ~0,4 ms) cũng bắn hàng trăm req/s và ~93–97% request bị 503. Luôn dùng `--rate` dưới 25.
2. Trên Windows dùng `127.0.0.1`, không dùng `localhost` (thêm ~2 giây trễ kết nối).

## 4. Lỗi đã sửa trong lần kiểm chứng này
- `applications.py`: biến `SIMULATED_CHAOS_MODE` được dùng nhưng chưa khai báo (`NameError`), nên mọi đơn đăng ký rơi vào dự phòng theo luật và **AI chưa từng được dùng**. Đã khai báo; giờ đơn có `Mode: ONLINE` và điểm AI thật.
- `ops.py`: các endpoint `/api/ops/*` (bật sập DB, tạo tải, sao lưu, đối soát) trước đây không cần đăng nhập. Nay yêu cầu JWT. `test_master.py` đã cập nhật gửi token.
- `vib-tls-secret` không có trong repo nên HTTPS dùng chứng chỉ giả mặc định của Nginx. Thêm `scripts/gen_tls_secret.sh` tạo Secret chứng chỉ tự ký cho `smartbanking.vib.vn`.
- `self_healing_demo.py` luôn in "0% lỗi" bất kể kết quả; nay in theo số đo thật.
- `demo_launcher.ps1` dùng `localhost` và 30 luồng không giới hạn; nay dùng `127.0.0.1`, 20 luồng, `--rate 20`.
- **NetworkPolicy:** sau khi Docker Desktop khởi động lại, bộ điều khiển NetworkPolicy của kindnet có thể lỗi (log: `could not open nfqueue socket`) và chính sách không có hiệu lực. Khắc phục: `kubectl delete pod -n kube-system -l app=kindnet`, rồi chạy lại `verify_cloud.py`.

## 5. Chưa có / hạn chế (đã nói rõ trên slide)
- Chưa ép chuyển HTTP sang HTTPS; chứng chỉ tự ký; Secret trong repo là giá trị mẫu (base64 không phải mã hoá).
- Chưa phân vai admin: khách đăng nhập nào cũng gọi được `/api/ops`. RBAC (`k8s/10-rbac.yaml`) gắn cho ServiceAccount mặc định.
- Tham số `simulate_failure` và công tắc chaos còn trong API production.
- Outbox nằm trong `/tmp` của pod: mất nếu pod chết trước khi đối soát. "Không mất dữ liệu" chỉ đúng khi pod còn sống; production cần hàng đợi bền.
- 1 node, PostgreSQL 1 bản sao, sao lưu cùng cụm, chưa có giám sát, CI/CD.
- Không còn khẳng định nào trong tài liệu cũ về "100% tiêu chí", HSTS, hay RTO 44 giây: các số đó không khớp với lần đo thật.

## 6. Cài và chạy lại từ đầu (K3s trong WSL)
Trong WSL (có thể mở bằng `wsl -d Ubuntu -u root` để khỏi cần mật khẩu sudo), tại thư mục gốc dự án:
```bash
bash scripts/k3s_wsl_setup.sh     # cài K3s + Nginx Ingress, nạp image, TLS, deploy, verify_cloud
python3 scripts/test_master.py --url http://127.0.0.1
python3 scripts/test_security.py --url http://127.0.0.1
```
Cần Docker Desktop đang chạy để lấy hai image (build trước bằng `scripts/build_images.*`; backend cần tag `v4`).

**Các lỗi đã gặp khi cài trên WSL:**
- `curl` thất bại im lặng vì WSL không có đường IPv6: script tự ép IPv4 (`~/.curlrc`).
- Lệnh `docker` trong WSL có thể chỉ là bản giả của Docker Desktop: script dùng `docker.exe`.
- Script `.sh` phải ở dạng LF; `.gitattributes` đã ép `eol=lf`.
- Docker Desktop đang giữ cổng 80/443 của Windows: muốn vào `http://127.0.0.1` từ Windows thì tắt "Enable Kubernetes" trong Docker Desktop. Truy cập từ trong WSL không bị ảnh hưởng.
- `kubectl` trên Windows muốn trỏ vào K3s: `$env:KUBECONFIG="$HOME\.kube\config-k3s"` (file do `k3s_wsl_setup.sh` tạo).

## 7. Tài liệu thuyết trình
`docs/presentation/VIB_SmartBanking_Nhom6_Slides_5phut.pptx` (8 slide, Hà trình bày, Trung demo) và `..._KichBan_ThuyetTrinh_5phut.docx` (script đọc, kịch bản demo, hỏi đáp). Bản 12 slide cũ trong cùng thư mục là bản trước khi có số đo thật: không dùng.
