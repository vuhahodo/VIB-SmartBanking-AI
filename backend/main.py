import os
import time
import json
import joblib
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI(title="VIB SmartBanking AI Service", version="1.0")

# Cấu hình kết nối DB nội bộ K8s
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vib_admin:SecureVIBPassword2026!@postgres-svc.vib-banking.svc.cluster.local:5432/vib_db")
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Load các Model AI khi khởi động Container
MODELS = {}
MODEL_FILES = {
    "creditcard": "models/model_target_creditcard.joblib",
    "loan": "models/model_target_loan.joblib",
    "term_deposit": "models/model_target_term_deposit.joblib"
}

for key, path in MODEL_FILES.items():
    if os.path.exists(path):
        try:
            MODELS[key] = joblib.load(path)
            print(f"Loaded model: {key}")
        except Exception as e:
            print(f"Error loading {key}: {e}")
    else:
        print(f"Model file not found: {path}")

# Load danh sách features tương ứng
FEATURES_BY_TARGET = {}
if os.path.exists("models/features_by_target.joblib"):
    try:
        FEATURES_BY_TARGET = joblib.load("models/features_by_target.joblib")
    except Exception as e:
        print(f"Error loading features mapping: {e}")

class RecommendationItem(BaseModel):
    product: str
    product_name: str
    score: float
    confidence: str
    reason: str

class RecommendationResponse(BaseModel):
    customer_id: str
    recommendations: list[RecommendationItem]
    model_version: str
    inference_time_ms: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "healthy", "loaded_models": list(MODELS.keys())}

@app.get("/api/v1/recommendation/{customer_id}", response_model=RecommendationResponse)
def get_recommendation(customer_id: str, db: Session = Depends(get_db)):
    start_time = time.time()
    cif = customer_id.zfill(8)

    # Truy vấn dữ liệu features từ bảng customer_features trong PostgreSQL
    query = text("SELECT data FROM customer_features WHERE customer_number = :cif")
    result = db.execute(query, {"cif": cif}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin khách hàng")

    cust_data = result[0]
    if isinstance(cust_data, str):
        cust_data = json.loads(cust_data)

    recs = []
    product_meta = {
        "creditcard": ("Credit Card", "VIB Cash Back", "Khách hàng có tần suất giao dịch và chi tiêu phù hợp"),
        "loan": ("Loan", "VIB Vay Tiêu Dùng", "Hồ sơ tín dụng đạt điều kiện xét duyệt nhanh"),
        "term_deposit": ("Term Deposit", "VIB Tiết Kiệm Online", "Số dư tài khoản thanh toán duy trì ổn định")
    }

    # Suy luận AI trên từng model
    for target_key, model in MODELS.items():
        feat_cols = FEATURES_BY_TARGET.get(f"target_{target_key}", [])
        if feat_cols:
            x_input = [[cust_data.get(col, 0) for col in feat_cols]]
        else:
            # Fallback nếu không có mapping: lấy toàn bộ numeric values
            num_vals = [v for k, v in cust_data.items() if isinstance(v, (int, float))]
            x_input = [num_vals]

        try:
            score = float(model.predict_proba(x_input)[0][1])
        except Exception:
            score = 0.5

        if score >= 0.4:
            p_type, p_name, p_reason = product_meta.get(target_key, (target_key, target_key, "Gợi ý tự động"))
            confidence = "HIGH" if score >= 0.7 else "MEDIUM"
            recs.append(
                RecommendationItem(
                    product=p_type,
                    product_name=p_name,
                    score=round(score, 2),
                    confidence=confidence,
                    reason=p_reason
                )
            )

    # Sắp xếp theo điểm số score giảm dần
    recs.sort(key=lambda x: x.score, reverse=True)
    inference_time = int((time.time() - start_time) * 1000)

    return RecommendationResponse(
        customer_id=cif,
        recommendations=recs,
        model_version="v1.0",
        inference_time_ms=inference_time
    )