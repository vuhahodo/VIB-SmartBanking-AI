#!/bin/bash
set -e

NAMESPACE="vib-banking"
echo "🚀 [1/5] Triển khai Namespace và Secrets..."
kubectl apply -f k8s/00-namespace-secrets.yaml

echo "📦 [2/5] Khởi tạo PostgreSQL StatefulSet..."
kubectl apply -f k8s/01-postgres.yaml
echo "   Đang chờ PostgreSQL sẵn sàng..."
kubectl rollout status statefulset/postgres -n $NAMESPACE --timeout=120s

echo "🌱 [3/5] Nạp dữ liệu đặc trưng khách hàng demo (Seed Job)..."
kubectl apply -f k8s/01.5-seed-job.yaml

echo "⚙️ [4/5] Triển khai Backend API & Frontend UI..."
kubectl apply -f k8s/02-backend.yaml
kubectl apply -f k8s/03-frontend.yaml
echo "   Đang chờ Backend API sẵn sàng..."
kubectl rollout status deployment/backend-api -n $NAMESPACE --timeout=180s
echo "   Đang chờ Frontend UI sẵn sàng..."
kubectl rollout status deployment/frontend-ui -n $NAMESPACE --timeout=120s

echo "⚖️ [5/5] Cấu hình Nginx Ingress Controller và HPA..."
kubectl apply -f k8s/04-ingress.yaml
kubectl apply -f k8s/05-hpa.yaml

echo "🛡️ [6/6] Bảo mật mạng, sẵn sàng cao và sao lưu..."
kubectl apply -f k8s/07-network-policy.yaml
kubectl apply -f k8s/08-pdb.yaml
kubectl apply -f k8s/09-backup.yaml

echo ""
echo "============================================================"
echo "✅ TRIỂN KHAI HOÀN TẤT TRÊN K3S!"
echo "============================================================"
kubectl get pods,hpa,ingress,pdb,networkpolicy,cronjob -n $NAMESPACE
echo ""
echo "Kiểm tra toàn bộ:  python scripts/verify_cloud.py --url http://<node-ip> --run-backup"
