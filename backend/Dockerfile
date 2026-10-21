FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy file từ thư mục backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy models từ thư mục ai
COPY ai/models ./models

# Copy code backend
COPY backend/main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]