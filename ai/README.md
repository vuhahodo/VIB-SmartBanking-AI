# VIB-SmartBanking AI — Phân hệ Trí tuệ Nhân tạo Gợi ý Sản phẩm (Next-Best-Action)

## 📌 Tổng quan
Phân hệ AI phục vụ bài toán **Next-Best-Action (NBA) & Bán chéo sản phẩm tài chính (Cross-Sell)** cho ngân hàng số VIB SmartBanking:
- **Thẻ tín dụng**: [VIB Super Card](file:///ai/models/model_target_creditcard.joblib) (hoàn tiền đến 15%)
- **Tiết kiệm trực tuyến**: [iDepo](file:///ai/models/model_target_term_deposit.joblib) (tiền gửi có kỳ hạn)
- **Khoản vay tiêu dùng**: [Consumer Loan](file:///ai/models/model_target_loan.joblib) (thấu chi, tiêu dùng tín chấp)

Toàn bộ mô hình được huấn luyện trên dữ liệu 290,223 khách hàng thực tế từ cuộc thi **VIB Hackathon 2021 Datarathon**.

---

## 📊 Kết quả Huấn luyện (Evaluation Metrics)

| Sản phẩm | Thuật toán | ROC-AUC | F1-Score | Precision | Recall | Kích thước Model |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Thẻ tín dụng (Super Card)** | XGBoost | **0.9891** | **0.8915** | 0.8640 | 0.9207 | 118 KB |
| **Tiết kiệm trực tuyến (iDepo)** | XGBoost | **0.9716** | **0.7642** | 0.6662 | 0.8961 | 99 KB |
| **Vay tiêu dùng tín chấp** | XGBoost | **0.9711** | **0.8930** | 0.8718 | 0.9152 | 122 KB |

> [!NOTE]
> **Chống rò rỉ dữ liệu (Data Leakage Prevention)**: Mỗi mô hình được cô lập đặc trưng nghiêm ngặt, loại bỏ hoàn toàn các trường sở hữu trực tiếp của sản phẩm mục tiêu (ví dụ: mô hình Thẻ tín dụng không sử dụng số lượng thẻ tín dụng làm đầu vào).

---

## 📂 Cấu trúc Thư mục

```
ai/
├── README.md                      # Tài liệu phân hệ AI
├── train_model.py                 # Pipeline huấn luyện tự động (XGBoost hist, multi-threaded)
├── predict.py                     # Inference engine thời gian thực phục vụ FastAPI & Web
├── models/
│   ├── model_target_creditcard.joblib    # Model thẻ tín dụng
│   ├── model_target_term_deposit.joblib  # Model gửi tiết kiệm
│   ├── model_target_loan.joblib          # Model vay tiêu dùng
│   ├── features_by_target.joblib         # Danh sách đặc trưng chuẩn hóa từng model
│   ├── training_metrics.json             # Báo cáo chi tiết metrics, top feature drivers
│   └── sample_customers.json             # 5 hồ sơ khách hàng mẫu kiểm thử API
└── kaggle_notebook/
    ├── kernel-metadata.json       # Metadata đẩy notebook lên Kaggle
    └── train_model.py             # Script chạy trên môi trường Kaggle
```

---

## 🚀 Hướng dẫn Sử dụng cho Nhánh `feature/web` (FastAPI)

Nhóm Web có thể import trực tiếp [VIBRecommendationEngine](file:///ai/predict.py) vào FastAPI service:

```python
from ai.predict import VIBRecommendationEngine

# Khởi tạo engine (load models vào RAM một lần duy nhất lúc khởi động app)
engine = VIBRecommendationEngine()

# Gọi gợi ý cho 1 khách hàng:
result = engine.predict_single(customer_dict)

# Kết quả trả về JSON chuẩn RESTful:
# {
#   "customer_number": "00992830",
#   "top_product": {
#     "code": "CONSUMER_LOAN",
#     "name": "Vay tiêu dùng tín chấp MyVIB",
#     "score": 0.9161,
#     "percent": 91.6
#   },
#   "summary_explanation": "Khách hàng có xác suất quan tâm cao nhất đến Vay tiêu dùng tín chấp MyVIB (91.6%), do...",
#   "recommendations": [...]
# }
```

---

## 🔄 Huấn luyện lại (Retrain)

### Cách 1: Chạy trực tiếp tại Local
```bash
python ai/train_model.py
```
Thời gian chạy: ~25 giây cho toàn bộ 6 file CSV (16+ triệu dòng dữ liệu).

### Cách 2: Chạy trên Kaggle
Notebook đã được publish lên Kaggle:
- URL: [https://www.kaggle.com/code/dophucvuha/vib-smartbanking-ai-training](https://www.kaggle.com/code/dophucvuha/vib-smartbanking-ai-training)
- Dataset: [https://www.kaggle.com/datasets/dophucvuha/vib-smartbanking-data](https://www.kaggle.com/datasets/dophucvuha/vib-smartbanking-data)
