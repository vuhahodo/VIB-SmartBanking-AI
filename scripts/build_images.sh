#!/bin/bash
set -e

echo "🔨 [1/2] Đang build Docker image cho Backend (FastAPI + XGBoost)..."
docker build -f web/backend/Dockerfile -t vib-backend:v1 .

echo "🎨 [2/2] Đang build Docker image cho Frontend (ReactJS + Nginx)..."
docker build -f web/frontend/Dockerfile -t vib-frontend:v1 web/frontend

echo "✅ Build hoàn tất hai images:"
docker images | grep vib-

echo ""
echo "💡 Nếu dùng K3s trên máy cục bộ, bạn có thể import trực tiếp image vào K3s containerd:"
echo "   docker save vib-backend:v1 | sudo k3s ctr images import -"
echo "   docker save vib-frontend:v1 | sudo k3s ctr images import -"

