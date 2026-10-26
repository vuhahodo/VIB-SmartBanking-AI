from fastapi import APIRouter, Depends

from ..ai_engine import VIBRecommendationEngine, get_engine

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/metrics")
def model_metrics(engine: VIBRecommendationEngine = Depends(get_engine)):
    """Nội dung ai/models/training_metrics.json (ROC-AUC, F1, top drivers...)."""
    return engine.metrics
