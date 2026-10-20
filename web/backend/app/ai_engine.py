"""Cầu nối tới phân hệ AI (ai/predict.py) — dùng lại nguyên engine của nhóm AI."""

import sys

from fastapi import Request

from .config import settings

if str(settings.AI_DIR) not in sys.path:
    sys.path.insert(0, str(settings.AI_DIR))

from predict import VIBRecommendationEngine  # noqa: E402

# Bổ sung thông tin hiển thị cho trang chi tiết sản phẩm
HIGHLIGHTS = {
    "CREDIT_CARD": [
        "Hoàn tiền đến 15% theo danh mục tự chọn",
        "Miễn phí thường niên năm đầu",
        "Trả góp 0% tại 1000+ đối tác",
        "Mở thẻ online trong 5 phút",
    ],
    "TERM_DEPOSIT": [
        "Kỳ hạn linh hoạt 1 – 36 tháng",
        "Cộng thêm 0.5%/năm khi gửi online",
        "Rút trước hạn từng phần",
        "Số tiền gửi tối thiểu 1 triệu VND",
    ],
    "CONSUMER_LOAN": [
        "Hạn mức đến 100 triệu VND",
        "Lãi suất từ 0.8%/tháng",
        "Không cần tài sản đảm bảo",
        "Giải ngân trong 15 phút",
    ],
}

PRODUCTS = [
    {"target_key": key, **cfg, "highlights": HIGHLIGHTS.get(cfg["product_code"], [])}
    for key, cfg in VIBRecommendationEngine.PRODUCT_CATALOG.items()
]
PRODUCTS_BY_CODE = {p["product_code"]: p for p in PRODUCTS}


def load_engine() -> VIBRecommendationEngine:
    return VIBRecommendationEngine(models_dir=str(settings.AI_DIR / "models"))


def get_engine(request: Request) -> VIBRecommendationEngine:
    return request.app.state.engine
