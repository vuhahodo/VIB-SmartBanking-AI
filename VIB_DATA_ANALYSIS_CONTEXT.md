# VIB-SmartBanking AI — Phân tích Dữ liệu & Ngữ cảnh Dự án

> **Mục đích file này:** Cung cấp toàn bộ ngữ cảnh, insight đã phân tích, cấu trúc dữ liệu chi tiết và hướng dẫn train AI cho bất kỳ AI/người nào đọc file này. Đọc xong file này là có thể viết code train model ngay mà không cần hỏi thêm.

---

## 1. Tổng quan Dự án

### 1.1 Đề tài
```
Nghiên cứu và triển khai ứng dụng VIB-SmartBanking, web ngân hàng số tích hợp AI gợi ý 
sản phẩm tài chính thời gian thực sử dụng ReactJS, FastAPI, triển khai lên cụm Kubernetes 
với cơ chế cân bằng tải và tự động co giãn, database lên PostgreSQL
```

### 1.2 Nguồn gốc dữ liệu
- **Cuộc thi:** VIB Hackathon 2021 — "Hack the Future of Banking" (Track 1: Datarathon / Data Science)
- **Tổ chức bởi:** Ngân hàng TMCP Quốc Tế Việt Nam (VIB) phối hợp Amazon Web Services (AWS)
- **Dữ liệu thực tế:** Toàn bộ khách hàng cá nhân mở tài khoản mới tại VIB trong năm 2019 (01/01/2019 – 31/12/2019)
- **Dữ liệu đã được mã hóa ẩn danh:** Mã khách hàng (`CUSTOMER_NUMBER`) là mã encoded, không thể truy ngược danh tính thật

### 1.3 Bài toán AI đã chọn
**Next-Best-Action / Cross-Sell — Gợi ý sản phẩm tài chính cá nhân hóa**

Mục tiêu: Dự đoán khách hàng nào có khả năng cao sẽ mở thêm:
- **Thẻ tín dụng (Credit Card)**
- **Sổ tiết kiệm có kỳ hạn (Term Deposit)**
- **Khoản vay (Loan)**

Từ đó hiển thị gợi ý cá nhân hóa trên giao diện web VIB-SmartBanking khi khách hàng đăng nhập.

### 1.4 Kiến trúc tổng thể (AI Service trong hệ thống)
```
[ReactJS Frontend] 
       │ 
       │  GET /api/v1/recommendation/{customer_id}
       ▼
[Nginx Ingress / Load Balancer trên K8s]
       │
       ▼
[FastAPI AI Service Pod(s)] ── K8s HPA: Auto-scale 1→5 pods khi CPU > 70%
       │
       ├── Load trained model (.pkl / .joblib)
       ├── Nhận customer_id → Query features từ PostgreSQL
       ├── Model inference (< 50ms)
       └── Return JSON: { "recommended_products": [...], "scores": {...} }
```

---

## 2. Cấu trúc Bộ Dữ liệu — 6 File CSV + 1 File Data Dictionary

### 2.1 Tổng quan các file

| STT | Tên File | Dung lượng | Số dòng | Số KH duy nhất | Mô tả |
|-----|----------|-----------|---------|-----------------|-------|
| 0 | `0.Data VIB Hackathon Guidline.xlsx` | 18 KB | — | — | Data Dictionary (7 sheets, mô tả từng cột) |
| 1 | `1.Data_Customer.csv` | 18.1 MB | 290,223 | **290,223** | Thông tin nhân khẩu học khách hàng (CIF Master) |
| 2 | `2.Data_MyVIB_Transaction.csv` | 83.1 MB | 1,418,030 | **52,488** | Giao dịch tài chính trên ứng dụng MyVIB |
| 3 | `3.Data_MyVIB_Activity.csv` | **713.2 MB** | **16,132,676** | **77,741** | Nhật ký hành vi / Clickstream trên app MyVIB |
| 4 | `4.Data_Deposit.csv` | 49.1 MB | 1,258,424 | **223,817** | Snapshot tiền gửi CASA & Tiết kiệm kỳ hạn theo tháng |
| 5 | `5.Data_Lending.csv` | 19.7 MB | 576,431 | **102,014** | Snapshot dư nợ vay theo tháng |
| 6 | `6.Data_Card.csv` | 21.3 MB | 871,589 | **150,459** | Snapshot thẻ tín dụng & thẻ ghi nợ theo tháng |

**Tổng dung lượng: ~905 MB**

### 2.2 Mối quan hệ giữa các bảng

Tất cả các bảng liên kết qua khóa chính **`CUSTOMER_NUMBER`** (Text, 8 ký tự, zero-padded).

```
DATA_CUSTOMER (290,223 KH — Bảng Master)
    ├── 1:N → DATA_MYVIB_TRANSACTION (52,488 KH có giao dịch — 18% tổng KH)
    ├── 1:N → DATA_MYVIB_ACTIVITY (77,741 KH có activity log — 27% tổng KH)  
    ├── 1:N → DATA_DEPOSIT (223,817 KH có tiền gửi — 77% tổng KH)
    ├── 1:N → DATA_LENDING (102,014 KH có khoản vay — 35% tổng KH)
    └── 1:N → DATA_CARD (150,459 KH có thẻ — 52% tổng KH)
```

**Quan trọng:** 100% khách hàng trong các bảng con đều tồn tại trong bảng `Data_Customer`. Không có orphan records.

---

## 3. Chi tiết Từng Bảng Dữ liệu

### 3.1 Bảng 1: `1.Data_Customer.csv` — Thông tin Khách hàng

**Schema:**
| Cột | Mô tả | Kiểu | Giá trị mẫu | Null count |
|-----|--------|------|-------------|------------|
| `CUSTOMER_NUMBER` | Mã KH (encoded, PK) | Text | `00639362` | 0 |
| `CLIENT_SEX` | Giới tính | Text | `M`, `F` | 4,283 |
| `CLIENT_CREATE_DATE` | Ngày mở CIF (tài khoản) | Date | `2019-04-23` | 0 |
| `DATE_OF_BIRTH` | Ngày sinh | Date | `1996-01-01` | 4,289 |
| `STAFF_VIB` | Có phải nhân viên VIB không | Text | `Y`, `N` | 0 |
| `IB_REGISTER_DATE` | Ngày đăng ký Internet Banking | Date | `2019-04-23` | **131,248** |
| `EB_REGISTER_CHANNEL` | Kênh đăng ký eBank | Text | `BRANCH`, `MYVIB`, `AUTO-JOB`, `WEBSITE` | **131,248** |
| `SMS` | Đăng ký nhận SMS thông báo | Text | `Y`, `N` | **131,248** |
| `VERIFY_METHOD` | Phương thức xác thực giao dịch | Text | `SMART_OTP`, `SMS`, `HARD_TOKEN` | **131,276** |

**Insight quan trọng:**
- **290,223 khách hàng duy nhất**, tất cả mở CIF trong năm 2019
- **131,248 KH (~45%) KHÔNG đăng ký eBank** (các cột `IB_REGISTER_DATE`, `EB_REGISTER_CHANNEL`, `SMS`, `VERIFY_METHOD` đều NULL cho nhóm này)
- **158,975 KH (~55%) CÓ đăng ký eBank**, trong đó:
  - Đăng ký qua chi nhánh (BRANCH): 117,161
  - Tự động (AUTO-JOB): 29,456
  - Qua app MyVIB: 12,254
  - Qua website: 104
- Giới tính: Nam 155,636 (54%) | Nữ 130,304 (45%) | NULL 4,283 (1%)
- Staff VIB: Chỉ 1,869 nhân viên (0.6%)
- Phương thức xác thực: SMART_OTP 130,722 (82%) | SMS 28,127 (18%) | HARD_TOKEN 98 (<0.1%)
- Năm sinh: min = 1900 (outlier/dummy), max = 2019 → cần xử lý outlier khi tính tuổi

### 3.2 Bảng 2: `2.Data_MyVIB_Transaction.csv` — Giao dịch Tài chính

**Schema:**
| Cột | Mô tả | Kiểu | Giá trị |
|-----|--------|------|---------|
| `TRANS_LV1` | Nhóm giao dịch cấp 1 | Text | `Transfer`, `Topup`, `Payment` |
| `TRANS_LV2` | Nhóm giao dịch cấp 2 (chi tiết) | Text | 14 loại (xem bên dưới) |
| `TRANS_DATE` | Ngày giao dịch | Date | `2019-01-02` đến `2019-12-31` |
| `DAY_OF_WEEK` | Thứ trong tuần | Text | `Mon`..`Sun` |
| `TRANS_HOUR` | Giờ giao dịch (0-23) | Number | 0–23 |
| `TRANS_NO` | Số lượng giao dịch | Number | min=1, max=148, mean=1.19 |
| `TRANS_AMOUNT` | Số tiền giao dịch (VNĐ) | Number | min=1, max=2.458 tỷ, mean=8.77 triệu |
| `CUSTOMER_NUMBER` | Mã KH | Text | FK → Data_Customer |

**Phân bổ TRANS_LV1 (cấp 1):**
| Loại | Số bản ghi | Tỷ lệ |
|------|-----------|-------|
| Transfer (Chuyển khoản) | 989,851 | 69.8% |
| Topup (Nạp tiền) | 348,766 | 24.6% |
| Payment (Thanh toán) | 79,413 | 5.6% |

**Phân bổ TRANS_LV2 (cấp 2):**
| Loại | Số bản ghi | Mô tả |
|------|-----------|-------|
| `Outside_VIB` | 759,815 | Chuyển khoản ra ngân hàng khác |
| `Within_VIB` | 229,191 | Chuyển khoản nội bộ VIB |
| `Mobile` | 177,812 | Nạp tiền điện thoại |
| `eWallet` | 170,529 | Nạp ví điện tử (MoMo, ZaloPay...) |
| `Credit_card_repayment` | 51,185 | Thanh toán dư nợ thẻ tín dụng |
| `Utilities_payment` | 21,145 | Thanh toán điện/nước/internet |
| `QR_payment` | 5,603 | Thanh toán QR Code |
| `VNDirect` | 845 | Nạp tiền chứng khoán VNDirect |
| `Insurance_payment` | 742 | Thanh toán bảo hiểm |
| `Lifestyle_payment` | 451 | Thanh toán dịch vụ lifestyle |
| `Lending_repayment` | 287 | Trả nợ khoản vay |
| `Game` | 260 | Nạp game |
| `Cable` | 160 | Thanh toán truyền hình cáp |
| `MCPP` | 5 | — |

**Insight:**
- Chỉ **52,488 KH (18%)** có phát sinh giao dịch tài chính trên MyVIB
- Số tiền giao dịch trung vị = **640,000 VNĐ**, trung bình = **8.77 triệu** (phân phối lệch phải mạnh — heavily right-skewed)
- Đại đa số giao dịch là chuyển khoản ra ngoài VIB (54%)

### 3.3 Bảng 3: `3.Data_MyVIB_Activity.csv` — Nhật ký Hành vi (Clickstream)

**Schema:**
| Cột | Mô tả | Kiểu |
|-----|--------|------|
| `ACTIVITY_DATE` | Ngày hoạt động | Date (format: `M/D/YYYY`) |
| `DAY_OF_WEEK` | Thứ trong tuần | Text |
| `ACTIVITY_HOUR` | Giờ hoạt động (0-23) | Number |
| `ACTIVITY_NO` | Mã hoạt động | Number |
| `CUSTOMER_NUMBER` | Mã KH | Text |
| `ACTIVITY_NAME` | Tên hoạt động | Text |

**Danh sách đầy đủ 45 loại ACTIVITY_NAME:**
```
ACCOUNT_ADDRESS_BOOK_DELETE          LOGIN_FACEID
ACCOUNT_ADDRESS_BOOK_UPDATE          LOGIN_FINGER
AUTHENTICATION                       LOGOUT
CARD_EGIFT_REGISTER_ANNUALFEE        MB_ACCOUNT_QUICK_BALANCE
CARD_EGIFT_REGISTER_CASHBACK         MB_BILLPAY
CARD_EGIFT_REGISTER_REDEEM           MB_CHANGE_PIN
CHANGE_PASSWORD                      MB_EXCHANGE_RATE_VIEW
EXPORT_ACCOUNT_STATEMENT_LOAN        MB_INTEREST_RATE_VIEW
LOGIN                                MB_LOCATION_ATM_VIEW
                                     MB_LOCATION_BRANCH_VIEW
MB_LOCATION_POS_VIEW                 TRANSFER_INTERNATIONAL
MB_RESET_PIN                         TRANSFER_VIA_PAYMENT_CENTER
MB_SET_PIN                           TRANSFER_VIA_PHONENO
QUERY_ACCOUNT_INFORMATION            TRANSFER_VIA_SML
QUERY_ACCOUNT_PORFOLIO               TRANSFER_VIA_SML_ACCOUNT
QUERY_CURRENT_ACCOUNT                TRANSFER_VIB_ACCOUNT
QUERY_LOAN_ACCOUNT                   TRANSFER_VIB_ACCOUNT_BULK
QUERY_MM_ACCOUNT                     
RB_BILLPAY_ADSL                      SET_PASSWORD
RB_BILLPAY_HOMEPHONE                 TOPUP_MOBILE
RB_BILLPAY_INSURANCE                 TRANSACTION_DETAIL_QUERY
RB_BILLPAY_MOBILE                    TRANSACTION_OVERVIEW_QUERY
RB_BILLPAY_PSTN
RB_BILLPAY_TELECOMMUNICATIONS
RB_BILLPAY_WATER
```

**Insight:**
- **16.1 triệu bản ghi** — File lớn nhất (713 MB), cần xử lý bằng chunked reading hoặc PySpark
- **77,741 KH** có activity log
- Các activity quan trọng cho feature engineering:
  - `MB_INTEREST_RATE_VIEW`: Khách hay xem lãi suất → Tín hiệu muốn gửi tiết kiệm
  - `QUERY_LOAN_ACCOUNT`: Khách tra cứu khoản nợ → Tín hiệu đang quan tâm vay
  - `CARD_EGIFT_REGISTER_*`: Khách đăng ký ưu đãi thẻ → Tín hiệu sử dụng thẻ tích cực
  - `LOGIN_FACEID`, `LOGIN_FINGER`: Phương thức đăng nhập sinh trắc học → Mức độ engagement cao

### 3.4 Bảng 4: `4.Data_Deposit.csv` — Tiền gửi (CASA & Tiết kiệm)

**Schema:**
| Cột | Mô tả | Kiểu |
|-----|--------|------|
| `MONTH` | Tháng báo cáo | Date (format: `M/DD/YYYY`, cuối tháng) |
| `COUNT_CA_ACCT` | Số tài khoản thanh toán (Current Account / CASA) | Number |
| `AVG_CA_BALANCE` | Số dư bình quân CASA trong tháng (VNĐ) | Number |
| `COUNT_TD_ACCT` | Số tài khoản tiết kiệm kỳ hạn (Term Deposit) | Number |
| `AVG_TD_BALANCE` | Số dư bình quân tiết kiệm kỳ hạn (VNĐ) | Number |
| `CUSTOMER_NUMBER` | Mã KH | Text |

**Insight:**
- **223,817 KH** có dữ liệu tiền gửi, snapshot 12 tháng (Jan–Dec 2019)
- Mỗi KH có tối đa 12 bản ghi (1 bản ghi/tháng)
- `AVG_CA_BALANCE`: trung bình = 4.7 triệu, trung vị = 290K → Phần lớn KH có số dư CASA rất thấp
- `AVG_TD_BALANCE`: trung bình = 49.6 triệu nhưng 75% KH = 0 → Chỉ thiểu số có tiết kiệm kỳ hạn
- **Feature quan trọng cho AI:** Khách có `AVG_CA_BALANCE` cao nhưng `COUNT_TD_ACCT = 0` → Tiềm năng gợi ý mở tiết kiệm kỳ hạn

### 3.5 Bảng 5: `5.Data_Lending.csv` — Dư nợ Vay

**Schema:**
| Cột | Mô tả | Kiểu |
|-----|--------|------|
| `MONTH` | Tháng báo cáo | Date |
| `COUNT_OF_LOAN` | Số khoản vay đang có | Number (min=1, max=121, mean=1.13) |
| `AVG_LOAN_AMOUNT` | Dư nợ vay bình quân (VNĐ) | Number (mean=468 triệu) |
| `CUSTOMER_NUMBER` | Mã KH | Text |

**Insight:**
- **102,014 KH (35%)** có khoản vay
- Dư nợ vay bình quân = 468 triệu VNĐ, trung vị = 345 triệu
- Đa số KH chỉ có 1 khoản vay (75th percentile = 1)
- Snapshot 12 tháng cho phép theo dõi xu hướng trả nợ theo thời gian

### 3.6 Bảng 6: `6.Data_Card.csv` — Thẻ Tín dụng & Ghi nợ

**Schema:**
| Cột | Mô tả | Kiểu |
|-----|--------|------|
| `MONTH` | Tháng báo cáo | Date |
| `COUNT_CREDITCARD` | Số thẻ tín dụng đang có | Number (min=0, max=13, mean=0.30) |
| `COUNT_DEBITCARD` | Số thẻ ghi nợ đang có | Number (min=0, max=19, mean=0.79) |
| `CUSTOMER_NUMBER` | Mã KH | Text |

**Insight:**
- **150,459 KH** có dữ liệu thẻ
- Trung bình chỉ 0.30 thẻ tín dụng/KH → **~70% KH chưa có thẻ tín dụng** → Đây là target chính cho bài toán gợi ý mở thẻ
- Trung bình 0.79 thẻ ghi nợ/KH → Phần lớn KH đã có thẻ ghi nợ (ATM)

---

## 4. Hướng dẫn Train AI — Bài toán Next-Best-Action / Cross-Sell

### 4.1 Định nghĩa Bài toán (Problem Formulation)

Xây dựng **3 mô hình phân loại nhị phân (Binary Classification)** hoặc **1 mô hình multi-label**:

| Target | Định nghĩa Label = 1 | Định nghĩa Label = 0 |
|--------|----------------------|----------------------|
| `target_creditcard` | KH có `COUNT_CREDITCARD > 0` tại bất kỳ tháng nào | KH luôn có `COUNT_CREDITCARD = 0` hoặc không có trong Data_Card |
| `target_term_deposit` | KH có `COUNT_TD_ACCT > 0` tại bất kỳ tháng nào | KH luôn có `COUNT_TD_ACCT = 0` hoặc không có trong Data_Deposit |
| `target_loan` | KH có trong Data_Lending (có khoản vay) | KH không có trong Data_Lending |

**Cách tinh vi hơn (Time-based split — Khuyến nghị):**
- Dùng dữ liệu các tháng 1–6 (H1-2019) làm **features** (đặc trưng đầu vào)
- Dùng dữ liệu các tháng 7–12 (H2-2019) để tạo **labels** (nhãn):
  - `target_creditcard = 1` nếu KH **bắt đầu** có thẻ tín dụng từ tháng 7 trở đi (mà tháng 1–6 chưa có)
  - Tương tự cho `target_term_deposit` và `target_loan`
- Cách này mô phỏng đúng bài toán thực tế: "Dựa trên hành vi 6 tháng đầu, dự đoán KH sẽ mở sản phẩm gì trong 6 tháng sau"

### 4.2 Feature Engineering — Các nhóm đặc trưng cần tạo

#### A. Demographic Features (từ `Data_Customer`)
```python
# Tuổi
age = 2019 - year(DATE_OF_BIRTH)  # Lưu ý lọc outlier DATE_OF_BIRTH < 1920 hoặc > 2005

# Tenure (số ngày từ khi mở CIF đến cuối kỳ phân tích)
tenure_days = (reference_date - CLIENT_CREATE_DATE).days

# Thời gian từ mở CIF đến đăng ký eBank
days_cif_to_ebank = (IB_REGISTER_DATE - CLIENT_CREATE_DATE).days  # NULL nếu chưa đăng ký eBank

# Binary/Categorical
gender_encoded          # M=1, F=0, NULL=fillna hoặc category riêng
is_staff_vib            # Y=1, N=0
has_ebank               # 1 nếu IB_REGISTER_DATE not null, 0 nếu null
eb_channel_encoded      # One-hot: BRANCH, MYVIB, AUTO-JOB, WEBSITE
sms_registered          # Y=1, N=0
verify_method_encoded   # One-hot: SMART_OTP, SMS, HARD_TOKEN
```

#### B. Transaction Features (từ `Data_MyVIB_Transaction`)
Aggregated per customer (groupby `CUSTOMER_NUMBER`):
```python
# Tổng quan giao dịch
total_transactions          # sum(TRANS_NO)
total_trans_amount          # sum(TRANS_AMOUNT)
avg_trans_amount            # mean(TRANS_AMOUNT)
max_trans_amount            # max(TRANS_AMOUNT)
median_trans_amount         # median(TRANS_AMOUNT)
std_trans_amount            # std(TRANS_AMOUNT) — Biến động số tiền
num_trans_days              # nunique(TRANS_DATE) — Số ngày có giao dịch
trans_frequency             # total_transactions / num_active_months

# Phân bổ theo loại giao dịch (TRANS_LV1)
pct_transfer                # % giao dịch Transfer
pct_topup                   # % giao dịch Topup
pct_payment                 # % giao dịch Payment

# Phân bổ theo loại chi tiết (TRANS_LV2)
amount_outside_vib          # Tổng tiền chuyển ra ngoài VIB
amount_within_vib           # Tổng tiền chuyển nội bộ
amount_ewallet              # Tổng tiền nạp ví điện tử
amount_credit_repayment     # Tổng tiền trả dư nợ thẻ tín dụng (RẤT QUAN TRỌNG cho target_creditcard)
has_qr_payment              # 1 nếu đã từng thanh toán QR
has_insurance_payment       # 1 nếu đã từng thanh toán bảo hiểm

# Thời gian giao dịch
avg_trans_hour              # Giờ giao dịch trung bình
pct_night_trans             # % giao dịch từ 22h–6h (nighttime)
pct_weekend_trans           # % giao dịch vào Sat/Sun
```

#### C. Activity Features (từ `Data_MyVIB_Activity`)

> **LƯU Ý:** File này 16 triệu dòng (713 MB). Nên đọc bằng `pd.read_csv(..., chunksize=2_000_000)` hoặc dùng PySpark/Dask.

Aggregated per customer:
```python
# Tổng quan hoạt động
total_logins                # count(LOGIN + LOGIN_FACEID + LOGIN_FINGER)
total_activities            # sum(ACTIVITY_NO)
num_active_days             # nunique(ACTIVITY_DATE)
num_distinct_activities     # nunique(ACTIVITY_NAME)

# Phương thức đăng nhập → Mức độ engagement
login_faceid_ratio          # % đăng nhập bằng FaceID
login_finger_ratio          # % đăng nhập bằng vân tay

# Hành vi quan trọng cho từng target:

## Tín hiệu quan tâm Tiết kiệm (→ target_term_deposit)
count_interest_rate_view    # Số lần xem biểu lãi suất (MB_INTEREST_RATE_VIEW)

## Tín hiệu quan tâm Vay (→ target_loan)  
count_query_loan            # Số lần tra cứu khoản nợ (QUERY_LOAN_ACCOUNT)
count_export_loan_statement # Số lần xuất sao kê vay (EXPORT_ACCOUNT_STATEMENT_LOAN)

## Tín hiệu quan tâm Thẻ (→ target_creditcard)
count_card_egift            # Tổng các activity CARD_EGIFT_* (đăng ký ưu đãi thẻ)
count_query_account_info    # Số lần xem thông tin tài khoản

## Mức độ engagement chung
count_query_portfolio       # Xem tổng quan danh mục tài sản
count_change_password       # Đổi mật khẩu
count_location_views        # Xem vị trí ATM/Branch/POS
```

#### D. Deposit Features (từ `Data_Deposit`)
Time-series aggregation per customer (12 monthly snapshots):
```python
# Tài khoản thanh toán (CASA)
avg_ca_balance_mean         # Trung bình số dư CASA qua 12 tháng
avg_ca_balance_max          # Số dư CASA cao nhất
avg_ca_balance_min          # Số dư CASA thấp nhất
avg_ca_balance_std          # Biến động số dư CASA
avg_ca_balance_trend        # Hệ số slope (tăng/giảm) qua 12 tháng (dùng linear regression)
avg_ca_balance_last         # Số dư tháng cuối cùng
ca_balance_growth           # (tháng_cuối - tháng_đầu) / tháng_đầu

# Tài khoản tiết kiệm kỳ hạn (Term Deposit)
has_term_deposit            # 1 nếu bất kỳ tháng nào COUNT_TD_ACCT > 0
max_td_accounts             # Số tài khoản TD cao nhất
avg_td_balance_mean         # Số dư TD bình quân
month_first_td              # Tháng đầu tiên mở TD (nếu có)
```

#### E. Lending Features (từ `Data_Lending`)
```python
has_loan                    # 1 nếu KH có trong Data_Lending
max_loan_count              # Số khoản vay nhiều nhất trong 1 tháng
avg_loan_amount_mean        # Dư nợ vay bình quân
avg_loan_amount_trend       # Xu hướng dư nợ (tăng = vay thêm, giảm = trả dần)
```

#### F. Card Features (từ `Data_Card`)
```python
has_creditcard              # 1 nếu bất kỳ tháng nào COUNT_CREDITCARD > 0
has_debitcard               # 1 nếu bất kỳ tháng nào COUNT_DEBITCARD > 0
max_creditcards             # Số thẻ tín dụng cao nhất
max_debitcards              # Số thẻ ghi nợ cao nhất
month_first_creditcard      # Tháng đầu tiên xuất hiện thẻ tín dụng
```

### 4.3 Pipeline Train Model

```python
# === PSEUDO-CODE PIPELINE ===

# Step 1: Load & Merge Data
df_customer = pd.read_csv("1.Data_Customer.csv")
df_transaction = pd.read_csv("2.Data_MyVIB_Transaction.csv")
df_activity = pd.read_csv("3.Data_MyVIB_Activity.csv", chunksize=2_000_000)  # CHUNKED!
df_deposit = pd.read_csv("4.Data_Deposit.csv")
df_lending = pd.read_csv("5.Data_Lending.csv")
df_card = pd.read_csv("6.Data_Card.csv")

# Step 2: Feature Engineering (per customer aggregation)
features_demo = build_demographic_features(df_customer)        # → 290,223 rows
features_txn = build_transaction_features(df_transaction)      # → 52,488 rows
features_act = build_activity_features(df_activity)            # → 77,741 rows (chunked)
features_dep = build_deposit_features(df_deposit)              # → 223,817 rows
features_lend = build_lending_features(df_lending)             # → 102,014 rows
features_card = build_card_features(df_card)                   # → 150,459 rows

# Step 3: Merge all features vào bảng customer (LEFT JOIN)
df_all = features_demo \
    .merge(features_txn, on='CUSTOMER_NUMBER', how='left') \
    .merge(features_act, on='CUSTOMER_NUMBER', how='left') \
    .merge(features_dep, on='CUSTOMER_NUMBER', how='left') \
    .merge(features_lend, on='CUSTOMER_NUMBER', how='left') \
    .merge(features_card, on='CUSTOMER_NUMBER', how='left')
# → 290,223 rows × ~50-80 features
# Fill NaN với 0 cho các KH không có data ở bảng con (ví dụ KH không có giao dịch)

# Step 4: Tạo Labels
df_all['target_creditcard'] = (df_all['has_creditcard'] == 1).astype(int)
df_all['target_term_deposit'] = (df_all['has_term_deposit'] == 1).astype(int)
df_all['target_loan'] = (df_all['has_loan'] == 1).astype(int)

# Step 5: Train/Test Split
X = df_all.drop(['CUSTOMER_NUMBER', 'target_creditcard', 'target_term_deposit', 'target_loan'], axis=1)
y = df_all['target_creditcard']  # Hoặc target khác

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

# Step 6: Train Model
from xgboost import XGBClassifier   # Hoặc LightGBM, CatBoost
model = XGBClassifier(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    scale_pos_weight=len(y_train[y_train==0]) / len(y_train[y_train==1]),  # Handle imbalance
    eval_metric='auc',
    random_state=42
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], early_stopping_rounds=50)

# Step 7: Evaluate
from sklearn.metrics import classification_report, roc_auc_score
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]
print(classification_report(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_prob))

# Step 8: Save Model for FastAPI deployment
import joblib
joblib.dump(model, 'model_creditcard_recommendation.joblib')
```

### 4.4 Đánh giá Model — Metrics cần báo cáo

| Metric | Ý nghĩa | Target tối thiểu |
|--------|---------|-------------------|
| **ROC-AUC** | Khả năng phân biệt KH mở/không mở sản phẩm | ≥ 0.75 |
| **Precision** | Tỷ lệ gợi ý đúng trong tổng gợi ý | ≥ 0.60 |
| **Recall** | Tỷ lệ KH tiềm năng được gợi ý đúng | ≥ 0.50 |
| **F1-Score** | Trung bình điều hòa Precision & Recall | ≥ 0.55 |
| **Feature Importance** | Top 10 đặc trưng quan trọng nhất (vẽ biểu đồ) | — |

### 4.5 Output API cho FastAPI Serving

Model sau khi train xong, save thành file `.joblib`, được FastAPI load lên và trả về kết quả dạng:

```json
// GET /api/v1/recommendation/00639362
{
  "customer_id": "00639362",
  "recommendations": [
    {
      "product": "Credit Card",
      "product_name": "VIB Cash Back",
      "score": 0.87,
      "confidence": "HIGH",
      "reason": "Khách hàng có tần suất chi tiêu qua ví điện tử cao và thường xuyên nạp tiền điện thoại"
    },
    {
      "product": "Term Deposit", 
      "product_name": "VIB Tiết kiệm Online",
      "score": 0.42,
      "confidence": "MEDIUM",
      "reason": "Số dư CASA bình quân cao hơn mức trung bình 3 lần"
    }
  ],
  "model_version": "v1.0",
  "inference_time_ms": 12
}
```

---

## 5. Lưu ý Kỹ thuật Quan trọng

### 5.1 Xử lý File Activity (713 MB)
```python
# KHÔNG ĐƯỢC đọc toàn bộ vào RAM cùng lúc trên Kaggle (RAM limit ~13GB)
# Phải dùng chunked reading:
activity_features = {}
for chunk in pd.read_csv("3.Data_MyVIB_Activity.csv", chunksize=2_000_000):
    grouped = chunk.groupby('CUSTOMER_NUMBER').agg({...})
    for cust, row in grouped.iterrows():
        if cust in activity_features:
            # Accumulate / merge counts
            ...
        else:
            activity_features[cust] = row
```

### 5.2 Xử lý Class Imbalance
- Target `target_creditcard`: Khoảng ~30% có thẻ tín dụng → Imbalance nhẹ
- Target `target_term_deposit`: Khoảng ~25% có tiết kiệm → Imbalance nhẹ  
- Target `target_loan`: Khoảng ~35% có vay → Tương đối cân bằng
- Giải pháp: `scale_pos_weight` trong XGBoost, hoặc SMOTE, hoặc class_weight='balanced'

### 5.3 Xử lý Missing Values
- Các KH không đăng ký eBank (131,248 KH) sẽ NULL toàn bộ cột `IB_REGISTER_DATE`, `EB_REGISTER_CHANNEL`, `SMS`, `VERIFY_METHOD` → Encode `has_ebank = 0` và fill features liên quan = 0
- KH không có giao dịch/activity/deposit/lending/card: Fill = 0 sau khi LEFT JOIN

### 5.4 Date Format khác nhau giữa các file
- `Data_Customer`: `YYYY-MM-DD` (ISO format)
- `Data_MyVIB_Transaction`: `YYYY-MM-DD`
- `Data_MyVIB_Activity`: `M/D/YYYY` (US format — **CẨN THẬN**)
- `Data_Deposit`, `Data_Lending`, `Data_Card`: `M/DD/YYYY` (US format)

### 5.5 Đường dẫn File trên Local
```
d:\HocTap\N4_K1\Cloud_Computing\Final_CloudComputing\Track 1 Datarathon\
├── 0.Data VIB Hackathon Guidline.xlsx
├── 1.Data_Customer.csv
├── 2.Data_MyVIB_Transaction.csv
├── 3.Data_MyVIB_Activity.csv       ← 713 MB, cần chunked reading
├── 4.Data_Deposit.csv
├── 5.Data_Lending.csv
└── 6.Data_Card.csv
```

---

## 6. Các Bài toán AI Thay thế (Nếu muốn đổi hướng)

Ngoài bài toán chính Next-Best-Action ở trên, bộ dữ liệu này còn hỗ trợ:

| Bài toán | Label source | Mô hình gợi ý |
|----------|-------------|---------------|
| **Customer Churn** (Rời bỏ) | KH có activity tháng 1–6 nhưng biến mất hoàn toàn tháng 7–12 | XGBoost, LSTM |
| **Digital Adoption** (Kích hoạt eBank) | 131K KH chưa đăng ký eBank vs 159K đã đăng ký | Logistic Regression, Random Forest |
| **Anomaly Detection** (Giao dịch bất thường) | Unsupervised — không có nhãn | Isolation Forest, Autoencoder |
| **Customer Segmentation** (Phân khúc KH) | Unsupervised — không có nhãn | K-Means, HDBSCAN + UMAP |
| **CLV Forecasting** (Dự báo giá trị KH) | Regression trên tổng số dư/giao dịch tương lai | LightGBM Regressor, XGBoost Regressor |
