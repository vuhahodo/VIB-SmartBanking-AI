#!/bin/bash
set -e

NAMESPACE="vib-banking"
echo "🚀 Triển khai hạ tầng VIB-SmartBanking lên K3s..."

# 1. Namespace & Secrets
kubectl apply -f k8s/00-namespace-secrets.yaml

# 2. Database
echo "📦 Khởi tạo PostgreSQL..."
kubectl apply -f k8s/01-postgres.yaml
kubectl rollout status statefulset/postgres -n $NAMESPACE

# 3. Backend & Frontend
echo "⚙️ Triển khai Backend API & Frontend UI..."
kubectl apply -f k8s/02-backend.yaml
kubectl apply -f k8s/03-frontend.yaml

# 4. Ingress & HPA
echo "⚖️ Cấu hình Ingress và HPA..."
kubectl apply -f k8s/04-ingress.yaml
kubectl apply -f k8s/05-hpa.yaml

echo "✅ Hoàn tất! Trạng thái hệ thống:"
kubectl get pods -n $NAMESPACE
kubectl get hpa -n $NAMESPACE
kubectl get ingress -n $NAMESPACE
