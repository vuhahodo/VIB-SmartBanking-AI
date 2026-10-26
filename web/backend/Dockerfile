# Build từ thư mục gốc repo (cần cả ai/ lẫn web/backend/):
#   docker build -f web/backend/Dockerfile -t vib-backend .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AI_DIR=/app/ai

# libgomp1: XGBoost cần OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai/predict.py ai/predict.py
COPY ai/models ai/models
COPY web/backend/app app
COPY web/backend/seed.py .

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fs http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
