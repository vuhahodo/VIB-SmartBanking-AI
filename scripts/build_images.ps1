# Script build Docker images tren Windows PowerShell
$ErrorActionPreference = "Stop"

Write-Host "🔨 [1/2] Dang build Docker image cho Backend (FastAPI + XGBoost)..." -ForegroundColor Cyan
docker build -f web/backend/Dockerfile -t vib-backend:v1 .

Write-Host "🎨 [2/2] Dang build Docker image cho Frontend (ReactJS + Nginx)..." -ForegroundColor Cyan
docker build -f web/frontend/Dockerfile -t vib-frontend:v1 web/frontend

Write-Host "✅ Build hoan tat hai images:" -ForegroundColor Green
docker images | Select-String "vib-"

Write-Host "`n💡 Neu ban dung K3s trong WSL hoac may ao Linux, export thanh file tar:" -ForegroundColor Yellow
Write-Host "   docker save vib-backend:v1 -o vib-backend.tar"
Write-Host "   docker save vib-frontend:v1 -o vib-frontend.tar"
Write-Host "   (Tren node K3s): sudo k3s ctr images import vib-backend.tar"

