#!/bin/bash
# Script chạy load test nhanh trên Linux / macOS / WSL
# Có thể truyền URL của node: ./scripts/load_test.sh http://172.17.242.190 60 40

TARGET_URL=${1:-"http://localhost"}
DURATION=${2:-60}
CONCURRENCY=${3:-30}
CUSTOMER_ID=${4:-"00992830"}

echo "🚀 Bắt đầu chạy kiểm thử tải VIB-SmartBanking..."
echo "Target: $TARGET_URL | Thời gian: ${DURATION}s | Đồng thời: ${CONCURRENCY} threads"

python3 scripts/load_test.py \
  --url "$TARGET_URL" \
  --duration "$DURATION" \
  --concurrency "$CONCURRENCY" \
  --customer "$CUSTOMER_ID"

