# VIB-SmartBanking-AI

Nghiên cứu và triển khai ứng dụng VIB-SmartBanking, web ngân hàng số tích hợp AI gợi ý sản phẩm tài chính thời gian thực sử dụng ReactJS, FastAPI, triển khai lên cụm Kubernetes với cơ chế cân bằng tải và tự động co giãn, database lên PostgreSQL.

## 📂 Cấu trúc Dự án

```
VIB-SmartBanking-AI/
├── VIB_DATA_ANALYSIS_CONTEXT.md    # Phân tích dữ liệu & ngữ cảnh AI (đọc file này trước)
├── Track 1 Datarathon/             # Thư mục data (không push lên GitHub)
│   ├── 0.Data VIB Hackathon Guidline.xlsx
│   ├── 1.Data_Customer.csv         (290K khách hàng)
│   ├── 2.Data_MyVIB_Transaction.csv (1.4M giao dịch)
│   ├── 3.Data_MyVIB_Activity.csv   (16M activity logs - 713MB)
│   ├── 4.Data_Deposit.csv          (1.2M snapshot tiền gửi)
│   ├── 5.Data_Lending.csv          (576K snapshot khoản vay)
│   └── 6.Data_Card.csv             (871K snapshot thẻ)
└── README.md
```

## 🎯 Bài toán AI

**Next-Best-Action / Cross-Sell**: Dự đoán khách hàng nào có khả năng cao mở thêm Thẻ tín dụng, Sổ tiết kiệm kỳ hạn, hoặc Khoản vay — từ đó hiển thị gợi ý cá nhân hóa trên giao diện web SmartBanking.

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | ReactJS |
| Backend / AI API | FastAPI (Python) |
| AI Model | XGBoost / LightGBM |
| Database | PostgreSQL |
| Container | Docker |
| Orchestration | Kubernetes (K8s) |
| Auto-scaling | Horizontal Pod Autoscaler (HPA) |
| Load Balancing | Nginx Ingress |

## 📊 Nguồn dữ liệu

Bộ dữ liệu thực tế từ cuộc thi **VIB Hackathon 2021: "Hack the Future of Banking"** (Track 1: Datarathon), tổ chức bởi Ngân hàng TMCP Quốc Tế Việt Nam (VIB) phối hợp Amazon Web Services (AWS).

> **Lưu ý:** Dữ liệu CSV không được push lên GitHub do dung lượng lớn (~905MB). Xem chi tiết phân tích trong file `VIB_DATA_ANALYSIS_CONTEXT.md`.
