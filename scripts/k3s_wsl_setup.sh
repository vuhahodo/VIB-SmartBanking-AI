#!/bin/bash
# Cài K3s trong WSL2 (Ubuntu) và triển khai VIB-SmartBanking lên đó.
# Chạy TRONG WSL, tại thư mục gốc dự án:
#   cd /mnt/d/HocTap/N4_K1/Cloud_Computing/Final_CloudComputing
#   bash scripts/k3s_wsl_setup.sh
# Cần: WSL2 có systemd, quyền sudo (sẽ hỏi mật khẩu), Docker Desktop đang chạy để lấy image
# vib-backend:v4 và vib-frontend:v2 (build bằng scripts/build_images.* nếu chưa có).
set -e

step() { echo; echo "=== $* ==="; }

[ -f k8s/00-namespace-secrets.yaml ] || { echo "Hãy chạy từ thư mục gốc dự án."; exit 1; }
[ "$(ps -p 1 -o comm=)" = "systemd" ] || { echo "WSL chưa bật systemd (thêm [boot] systemd=true vào /etc/wsl.conf rồi wsl --shutdown)."; exit 1; }

step "1/7 Cài K3s (tắt Traefik, dùng Nginx Ingress)"
if ! command -v k3s >/dev/null 2>&1; then
  # WSL thường không có đường IPv6 nên curl mặc định có thể thất bại im lặng: ép dùng IPv4.
  grep -qx "ipv4" ~/.curlrc 2>/dev/null || echo "ipv4" >> ~/.curlrc
  curl -fsSL -4 https://get.k3s.io -o /tmp/k3s-install.sh || { echo "LỖI: không tải được https://get.k3s.io (kiểm tra mạng/VPN/proxy của WSL)."; exit 1; }
  INSTALL_K3S_EXEC="server --disable traefik --write-kubeconfig-mode 644" sh /tmp/k3s-install.sh
  command -v k3s >/dev/null 2>&1 || { echo "LỖI: cài K3s chưa thành công."; exit 1; }
else
  echo "K3s đã có: $(k3s --version | head -n 1)"
fi
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
echo "Chờ node Ready..."
for i in $(seq 1 60); do
  kubectl get nodes 2>/dev/null | grep -q " Ready" && break
  sleep 3
done
kubectl get nodes -o wide

step "2/7 Cài Nginx Ingress (bare-metal) và mở cổng 80/443 qua ServiceLB của K3s"
if ! kubectl get ns ingress-nginx >/dev/null 2>&1; then
  kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.2/deploy/static/provider/baremetal/deploy.yaml
fi
kubectl patch svc ingress-nginx-controller -n ingress-nginx -p '{"spec":{"type":"LoadBalancer"}}'
kubectl rollout status deploy/ingress-nginx-controller -n ingress-nginx --timeout=240s

step "3/7 Nạp image vào K3s từ Docker Desktop"
# Trong WSL lệnh `docker` có thể chỉ là bản giả nhắc bật tích hợp WSL: dùng lệnh nào thật sự chạy được.
DOCKER=docker
$DOCKER info >/dev/null 2>&1 || DOCKER=docker.exe
$DOCKER info >/dev/null 2>&1 || { echo "LỖI: không chạy được docker. Hãy bật Docker Desktop."; exit 1; }
for img in vib-backend:v4 vib-frontend:v2; do
  if $DOCKER image inspect "$img" >/dev/null 2>&1; then
    echo "Nạp $img ..."
    $DOCKER save "$img" | sudo k3s ctr images import -
  else
    echo "THIẾU image $img trên Docker Desktop: chạy scripts/build_images.* trước (backend cần tag v4: docker build -f web/backend/Dockerfile -t vib-backend:v4 .)"
    exit 1
  fi
done

step "4/7 Namespace, Secret TLS tự ký"
kubectl apply -f k8s/00-namespace-secrets.yaml
bash scripts/gen_tls_secret.sh

step "5/7 Triển khai ứng dụng"
bash scripts/deploy.sh
kubectl apply -f k8s/10-rbac.yaml

step "6/7 Xuất kubeconfig cho kubectl trên Windows"
WINUSER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')
if [ -n "$WINUSER" ] && [ -d "/mnt/c/Users/$WINUSER" ]; then
  mkdir -p "/mnt/c/Users/$WINUSER/.kube"
  cp /etc/rancher/k3s/k3s.yaml "/mnt/c/Users/$WINUSER/.kube/config-k3s"
  echo "Đã chép tới C:\\Users\\$WINUSER\\.kube\\config-k3s"
  echo "Trên Windows dùng:  \$env:KUBECONFIG=\"\$HOME\\.kube\\config-k3s\""
fi

step "7/7 Kiểm tra"
sleep 5
curl -s -o /dev/null -w "GET /ready qua Ingress (trong WSL) -> %{http_code}\n" http://127.0.0.1/ready || true
python3 scripts/verify_cloud.py --url http://127.0.0.1 --run-backup || true

cat <<'MSG'

XONG. Việc cần làm tiếp:
  1. Docker Desktop đang chiếm cổng 80/443 của Windows. Muốn truy cập http://127.0.0.1 từ Windows:
     Docker Desktop > Settings > Kubernetes > bỏ chọn "Enable Kubernetes" > Apply.
  2. Kiểm tra nền tảng:  kubectl version   (phải thấy đuôi +k3s)
  3. Đo số liệu thật trên K3s (đợi HPA về 2 pod giữa hai lần đo):
       python3 scripts/load_test.py --url http://127.0.0.1 --duration 60 --concurrency 20 --rate 20
       python3 scripts/self_healing_demo.py
MSG
