# Script chay kiem thu tai nhanh tren Windows PowerShell
# Cach dung:
#   .\scripts\load_test.ps1 -Url "http://172.17.242.190" -Duration 60 -Concurrency 30
param(
    [string]$Url = "http://localhost",
    [int]$Duration = 60,
    [int]$Concurrency = 30,
    [string]$Customer = "00992830"
)

Write-Host "🚀 Bat dau chay kiem thu tai VIB-SmartBanking..." -ForegroundColor Cyan
Write-Host "Target: $Url | Thoi gian: ${Duration}s | Dong thoi: ${Concurrency} threads" -ForegroundColor Yellow

python scripts/load_test.py `
  --url "$Url" `
  --duration $Duration `
  --concurrency $Concurrency `
  --customer "$Customer"

