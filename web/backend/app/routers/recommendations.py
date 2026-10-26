from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..ai_engine import VIBRecommendationEngine, get_engine
from ..auth import ensure_self, get_current_customer
from ..database import get_db
from ..models import CustomerFeature, RecommendationLog
from ..schemas import PredictionOut

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/{customer_number}", response_model=PredictionOut)
def recommend(
    customer_number: str,
    db: Session = Depends(get_db),
    current: str = Depends(get_current_customer),
    engine: VIBRecommendationEngine = Depends(get_engine),
):
    """Chạy 3 mô hình XGBoost trên đặc trưng của khách hàng và trả về Next-Best-Action."""
    ensure_self(customer_number, current)
    row = db.get(CustomerFeature, customer_number)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chưa có dữ liệu đặc trưng cho khách hàng này")

    result = engine.predict_single({**row.features, "CUSTOMER_NUMBER": customer_number})

    db.add(
        RecommendationLog(
            customer_number=customer_number,
            top_product_code=result["top_product"]["code"],
            top_score=result["top_product"]["score"],
            result=result,
        )
    )
    db.commit()
    return result
