import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .ai_engine import load_engine
from .config import settings
from .database import Base, engine
from .routers import ai, applications, auth, customers, products, recommendations

logger = logging.getLogger("vib")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo bảng nếu chưa có
    try:
        Base.metadata.create_all(engine)
    except Exception as exc:
        logger.warning("Không thể tạo schema database lúc khởi động: %s", exc)

    # Tự động nạp dữ liệu 5 khách hàng demo nếu database còn trống
    try:
        from seed import seed_if_empty
        seed_if_empty()
    except Exception as exc:
        logger.info("Bỏ qua hoặc không thể auto-seed: %s", exc)

    # Nạp 3 model XGBoost đúng 1 lần vào RAM, dùng chung cho mọi request
    app.state.engine = load_engine()
    logger.info("AI engine loaded: %s", list(app.state.engine.models))
    yield


app = FastAPI(title="VIB SmartBanking API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, customers, recommendations, products, applications, ai):
    app.include_router(r.router, prefix="/api")


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
def health():
    """Liveness probe cho Kubernetes: process còn sống."""
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
@app.get("/api/ready", tags=["health"])
def ready(request: Request):
    """Readiness probe: DB kết nối được và model AI đã nạp."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse({"status": "db_unavailable", "detail": str(exc)}, status_code=503)
    if getattr(request.app.state, "engine", None) is None:
        return JSONResponse({"status": "model_not_loaded"}, status_code=503)
    return {"status": "ready"}
