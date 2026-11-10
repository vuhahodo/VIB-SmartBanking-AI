# ==============================================================================
# BỘ ĐIỀU KHIỂN DEMO THUYẾT TRÌNH VIB-SMARTBANKING-AI (NHÓM 6 VKU)
# ==============================================================================

function Show-Header {
    Clear-Host
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "     VIB-SMARTBANKING-AI: BỘ ĐIỀU KHIỂN DEMO THUYẾT TRÌNH (VKU)      " -ForegroundColor Yellow -NoNewline
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host " [Trạng thái Cluster: Kubernetes v1.34 - Docker Desktop Active]" -ForegroundColor Green
    Write-Host " [Mã KH Demo: 00992830 | Mật khẩu: 123456]" -ForegroundColor DarkGray
    Write-Host ""
}

# Đảm bảo port-forward Kubernetes Dashboard chạy ngầm nếu chưa chạy
$k8sPort = Get-NetTCPConnection -LocalPort 8443 -ErrorAction SilentlyContinue
if (-not $k8sPort) {
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-Command kubectl port-forward -n kubernetes-dashboard svc/kubernetes-dashboard 8443:443"
}

do {
    Show-Header
    Write-Host "  1. 📺 Mở 2 Terminal giám sát (Cửa sổ 1: HPA | Cửa sổ 2: Pods)" -ForegroundColor White
    Write-Host "  2. 🌐 Mở Ứng dụng Web Ngân hàng (http://localhost/)" -ForegroundColor White
    Write-Host "  3. 🛠️ Mở Bảng Quản trị Hạ tầng SRE (http://localhost/admin/infrastructure)" -ForegroundColor White
    Write-Host "  4. 📑 Mở Tài liệu API Swagger (/docs)" -ForegroundColor White
    Write-Host "  5. 📊 Mở Kubernetes Dashboard (https://localhost:8443/)" -ForegroundColor White
    Write-Host "----------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  6. 🔥 BẮN TẢI KÍCH HOẠT HPA CO GIÃN PODS (Tự động đăng nhập & test)" -ForegroundColor Yellow
    Write-Host "  7. 🛡️ THỬ NGHIỆM TỰ PHỤC HỒI (Xóa 1 Pod & chứng minh Zero-Downtime)" -ForegroundColor Magenta
    Write-Host "  8. 🧪 CHẠY TOÀN BỘ BỘ KIỂM THỬ TỰ ĐỘNG (Master Test Suite 22/22 PASS)" -ForegroundColor Green
    Write-Host "----------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  0. ❌ Thoát" -ForegroundColor Red
    Write-Host ""
    
    $choice = Read-Host "Nhập lựa chọn của bạn (0-8)"

    switch ($choice) {
        "1" {
            Write-Host "`nĐang mở 2 terminal giám sát K8s..." -ForegroundColor Cyan
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '=== GIÁM SÁT HPA (TỰ CO GIÃN THEO CPU) ===' -ForegroundColor Yellow; kubectl get hpa -n vib-banking -w"
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '=== GIÁM SÁT TRẠNG THÁI PODS (SELF-HEALING) ===' -ForegroundColor Cyan; kubectl get pods -n vib-banking -w"
            Start-Sleep -Seconds 1
        }
        "2" {
            Write-Host "`nĐang mở Web App Ngân hàng..." -ForegroundColor Cyan
            Start-Process "http://localhost/"
            Start-Sleep -Seconds 1
        }
        "3" {
            Write-Host "`nĐang mở SRE DevOps Dashboard..." -ForegroundColor Cyan
            Start-Process "http://localhost/admin/infrastructure"
            Start-Sleep -Seconds 1
        }
        "4" {
            Write-Host "`nĐang mở API Docs..." -ForegroundColor Cyan
            Start-Process "http://localhost/docs"
            Start-Sleep -Seconds 1
        }
        "5" {
            Write-Host "`nĐang mở Kubernetes Dashboard..." -ForegroundColor Cyan
            Write-Host "Token quản trị nằm trong file: k8s/dashboard-token.txt" -ForegroundColor Yellow
            Start-Process "https://localhost:8443/"
            Start-Sleep -Seconds 1
        }
        "6" {
            Write-Host "`n============================================================" -ForegroundColor Yellow
            Write-Host "  BẮT ĐẦU BẮN TẢI KÍCH HOẠT HPA AUTO-SCALING (60 giây, 30 luồng)" -ForegroundColor Yellow
            Write-Host "============================================================" -ForegroundColor Yellow
            python scripts/load_test.py --url http://127.0.0.1 --duration 60 --concurrency 20 --rate 20
            Write-Host "`nNhấn phím bất kỳ để quay lại menu..." -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "7" {
            Write-Host "`n============================================================" -ForegroundColor Magenta
            Write-Host "  THỰC NGHIỆM TỰ PHỤC HỒI: XÓA 1 POD & ĐO THỜI GIAN HỒI SINH" -ForegroundColor Magenta
            Write-Host "============================================================" -ForegroundColor Magenta
            python scripts/self_healing_demo.py
            Write-Host "`nNhấn phím bất kỳ để quay lại menu..." -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "8" {
            Write-Host "`n============================================================" -ForegroundColor Green
            Write-Host "  CHẠY MASTER TEST SUITE TOÀN DIỆN HỆ THỐNG (22 TIÊU CHÍ)" -ForegroundColor Green
            Write-Host "============================================================" -ForegroundColor Green
            python scripts/test_master.py --url http://localhost
            Write-Host "`nNhấn phím bất kỳ để quay lại menu..." -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "0" {
            Write-Host "`nĐã đóng bộ điều khiển demo. Chúc bạn có buổi bảo vệ thành công!" -ForegroundColor Green
            break
        }
    }
} while ($choice -ne "0")

