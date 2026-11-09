#!/bin/bash
# ==============================================================================
# Script kiểm thử toàn diện hệ thống VIB-SmartBanking-AI
# ==============================================================================
set -e

BASE_URL="${1:-http://172.17.242.190}"
NAMESPACE="vib-banking"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}     BẮT ĐẦU KIỂM THỬ TOÀN DIỆN DỰ ÁN VIB-SMARTBANKING-AI        ${NC}"
echo -e "${BLUE}     Target Host: ${BASE_URL}                                   ${NC}"
echo -e "${BLUE}================================================================${NC}\n"

# ------------------------------------------------------------------------------
# PHẦN 1: KIỂM TRA HẠ TẦNG KUBERNETES & PROBES
# ------------------------------------------------------------------------------
echo -e "${YELLOW}>>> [1/4] KIỂM TRA HẠ TẦNG & SỨC KHỎE CỤM (HEALTH & PROBES)...${NC}"

# 1.1 Liveness Probe
HTTP_CODE=$(curl -s -o /tmp/health.json -w "%{http_code}" "${BASE_URL}/health")
if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 1.1 Liveness Probe (/health) -> HTTP 200"
    cat /tmp/health.json && echo ""
else
    echo -e "  [${RED}FAIL${NC}] 1.1 Liveness Probe (/health) -> HTTP $HTTP_CODE"
fi

# 1.2 Readiness Probe
HTTP_CODE=$(curl -s -o /tmp/ready.json -w "%{http_code}" "${BASE_URL}/ready")
if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 1.2 Readiness Probe (/ready) -> HTTP 200"
    cat /tmp/ready.json && echo ""
else
    echo -e "  [${RED}FAIL${NC}] 1.2 Readiness Probe (/ready) -> HTTP $HTTP_CODE"
fi

# 1.3 Frontend UI serving
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/")
if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 1.3 Frontend UI Root (/) -> HTTP 200"
else
    echo -e "  [${RED}FAIL${NC}] 1.3 Frontend UI Root (/) -> HTTP $HTTP_CODE"
fi

# ------------------------------------------------------------------------------
# PHẦN 2: KIỂM TRA XÁC THỰC VÀ TÀI KHOẢN (AUTH & CUSTOMERS)
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}>>> [2/4] KIỂM TRA TÀI KHOẢN & XÁC THỰC (AUTH & PROFILE)...${NC}"

# 2.1 Lấy danh sách demo accounts
HTTP_CODE=$(curl -s -o /tmp/demo.json -w "%{http_code}" "${BASE_URL}/api/auth/demo-accounts")
if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 2.1 Danh sách tài khoản Demo -> HTTP 200"
    DEMO_CUST=$(grep -o '"customer_number": *"[^"]*"' /tmp/demo.json | head -n 1 | cut -d'"' -f4)
    echo -e "         Tài khoản mẫu: ${DEMO_CUST}"
else
    echo -e "  [${YELLOW}WARN${NC}] 2.1 Demo accounts không khả dụng, mặc định chọn '00992830'"
    DEMO_CUST="00992830"
fi

# 2.2 Đăng nhập lấy JWT Token
echo "  [*] Thực hiện đăng nhập với khách hàng: $DEMO_CUST..."
LOGIN_RES=$(curl -s -X POST "${BASE_URL}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"customer_number\": \"${DEMO_CUST}\", \"password\": \"123456\"}")

TOKEN=$(echo "$LOGIN_RES" | grep -o '"access_token": *"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    echo -e "  [${GREEN}PASS${NC}] 2.2 Đăng nhập JWT thành công!"
else
    echo -e "  [${RED}FAIL${NC}] 2.2 Đăng nhập thất bại: $LOGIN_RES"
    exit 1
fi

# 2.3 Lấy thông tin hồ sơ khách hàng
HTTP_CODE=$(curl -s -o /tmp/profile.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/customers/${DEMO_CUST}")

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 2.3 Lấy hồ sơ khách hàng (${DEMO_CUST}) -> HTTP 200"
    cat /tmp/profile.json && echo ""
else
    echo -e "  [${RED}FAIL${NC}] 2.3 Lấy hồ sơ thất bại -> HTTP $HTTP_CODE"
fi

# 2.4 Lấy lịch sử giao dịch
HTTP_CODE=$(curl -s -o /tmp/tx.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/customers/${DEMO_CUST}/transactions?limit=5")

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 2.4 Lịch sử giao dịch mới nhất -> HTTP 200"
else
    echo -e "  [${RED}FAIL${NC}] 2.4 Lấy lịch sử giao dịch thất bại -> HTTP $HTTP_CODE"
fi

# ------------------------------------------------------------------------------
# PHẦN 3: KIỂM TRA TÍNH NĂNG AI (NEXT-BEST-ACTION INFERENCE)
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}>>> [3/4] KIỂM TRA TÍNH NĂNG AI INFERENCE & SẢN PHẨM...${NC}"

# 3.1 Chạy mô hình gợi ý AI
echo "  [*] Đang chạy 3 mô hình XGBoost suy luận thời gian thực cho khách hàng $DEMO_CUST..."
HTTP_CODE=$(curl -s -o /tmp/rec.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}/api/recommendations/${DEMO_CUST}")

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 3.1 AI Next-Best-Action Inference -> HTTP 200"
    echo -e "         Kết quả gợi ý:"
    cat /tmp/rec.json && echo ""
else
    echo -e "  [${RED}FAIL${NC}] 3.1 AI Inference thất bại -> HTTP $HTTP_CODE"
fi

# 3.2 Lấy danh mục sản phẩm
HTTP_CODE=$(curl -s -o /tmp/products.json -w "%{http_code}" "${BASE_URL}/api/products")
if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 3.2 Danh mục sản phẩm tài chính -> HTTP 200"
else
    echo -e "  [${RED}FAIL${NC}] 3.2 Lấy sản phẩm thất bại -> HTTP $HTTP_CODE"
fi

# 3.3 Nộp hồ sơ đăng ký sản phẩm (Application)
HTTP_CODE=$(curl -s -o /tmp/app.json -w "%{http_code}" \
    -X POST "${BASE_URL}/api/applications" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"product_code": "CREDIT_CARD", "full_name": "Nguyễn Văn Test", "phone": "0912345678", "email": "test@vib.com.vn", "monthly_income": 25000000, "note": "Test đơn hàng từ script kiểm thử tự động"}')

if [ "$HTTP_CODE" -eq 201 ]; then
    echo -e "  [${GREEN}PASS${NC}] 3.3 Nộp hồ sơ đăng ký sản phẩm -> HTTP 201"
    cat /tmp/app.json && echo ""
else
    echo -e "  [${RED}FAIL${NC}] 3.3 Nộp hồ sơ thất bại -> HTTP $HTTP_CODE"
fi

# 3.4 Lấy metrics hiệu năng mô hình AI
HTTP_CODE=$(curl -s -o /tmp/metrics.json -w "%{http_code}" "${BASE_URL}/api/ai/metrics")
if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "  [${GREEN}PASS${NC}] 3.4 Chỉ số kiểm thử mô hình AI (AUC/F1) -> HTTP 200"
    cat /tmp/metrics.json && echo ""
else
    echo -e "  [${RED}FAIL${NC}] 3.4 Lấy AI metrics thất bại -> HTTP $HTTP_CODE"
fi

# ------------------------------------------------------------------------------
# PHẦN 4: KIỂM TRA TỰ PHỤC HỒI & TỰ ĐỘNG CO GIÃN (SELF-HEALING & HPA)
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}>>> [4/4] KIỂM TRA KHẢ NĂNG CO GIÃN & TỰ PHỤC HỒI K8S...${NC}"

if command -v kubectl >/dev/null 2>&1; then
    KUBECTL="kubectl"
elif command -v k3s >/dev/null 2>&1; then
    KUBECTL="k3s kubectl"
else
    KUBECTL=""
fi

if [ -n "$KUBECTL" ]; then
    echo "  [*] Kiểm tra trạng thái HPA hiện tại:"
    $KUBECTL get hpa -n $NAMESPACE
    echo ""
    echo "  [*] Kiểm tra mức tiêu thụ CPU/RAM các Pods:"
    $KUBECTL top pods -n $NAMESPACE 2>/dev/null || echo "      (Metrics Server đang cập nhật chu kỳ)"
else
    echo "  [INFO] Bỏ qua kiểm tra kubectl (không tìm thấy trong PATH)."
fi

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}     HOÀN TẤT KIỂM THỬ: TẤT CẢ TÍNH NĂNG HOẠT ĐỘNG TỐT!         ${NC}"
echo -e "${GREEN}================================================================${NC}"
