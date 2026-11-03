# Script trien khai VIB-SmartBanking len Kubernetes bang Windows PowerShell
$ErrorActionPreference = "Stop"
$Namespace = "vib-banking"

Write-Host "🚀 [1/5] Trien khai Namespace va Secrets..." -ForegroundColor Cyan
kubectl apply -f k8s/00-namespace-secrets.yaml

Write-Host "📦 [2/5] Khoi tao PostgreSQL StatefulSet..." -ForegroundColor Cyan
kubectl apply -f k8s/01-postgres.yaml
Write-Host "   Dang cho PostgreSQL san sang..." -ForegroundColor Gray
kubectl rollout status statefulset/postgres -n $Namespace --timeout=120s

Write-Host "🌱 [3/5] Nap du lieu dac trung khach hang demo (Seed Job)..." -ForegroundColor Cyan
kubectl apply -f k8s/01.5-seed-job.yaml

Write-Host "⚙️ [4/5] Trien khai Backend API & Frontend UI..." -ForegroundColor Cyan
kubectl apply -f k8s/02-backend.yaml
kubectl apply -f k8s/03-frontend.yaml
Write-Host "   Dang cho Backend API san sang..." -ForegroundColor Gray
kubectl rollout status deployment/backend-api -n $Namespace --timeout=180s
Write-Host "   Dang cho Frontend UI san sang..." -ForegroundColor Gray
kubectl rollout status deployment/frontend-ui -n $Namespace --timeout=120s

Write-Host "⚖️ [5/5] Cau hinh Nginx Ingress Controller va HPA..." -ForegroundColor Cyan
kubectl apply -f k8s/04-ingress.yaml
kubectl apply -f k8s/05-hpa.yaml

Write-Host "🛡️ [6/6] Bao mat mang, san sang cao va sao luu..." -ForegroundColor Cyan
kubectl apply -f k8s/07-network-policy.yaml
kubectl apply -f k8s/08-pdb.yaml
kubectl apply -f k8s/09-backup.yaml

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "✅ TRIEN KHAI HOAN TAT TREN K8S!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
kubectl get pods,hpa,ingress,pdb,networkpolicy,cronjob -n $Namespace
Write-Host "`nKiem tra toan bo:  python scripts/verify_cloud.py --url http://<node-ip> --run-backup" -ForegroundColor Gray

