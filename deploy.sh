#!/bin/bash
set -e

# Chuyển về đúng thư mục chứa script (thư mục gốc dự án)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

bash scripts/deploy.sh
