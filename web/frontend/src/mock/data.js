// Dữ liệu giả cho giao diện. Cấu trúc `recommendations` khớp 100% với output
// của ai/predict.py -> VIBRecommendationEngine.predict_single()

const PRODUCTS = {
  CREDIT_CARD: {
    target_key: 'target_creditcard',
    product_code: 'CREDIT_CARD',
    product_name: 'Thẻ tín dụng VIB Super Card',
    category: 'Cards',
    badge: 'Hoàn tiền 15%',
    description:
      'Tùy chọn tính năng hoàn tiền linh hoạt đến 15%, miễn phí thường niên trọn đời khi đạt chỉ tiêu chi tiêu.',
    threshold: 0.4,
    highlights: ['Hoàn tiền đến 15% theo danh mục tự chọn', 'Miễn phí thường niên năm đầu', 'Trả góp 0% tại 1000+ đối tác', 'Mở thẻ online trong 5 phút'],
  },
  TERM_DEPOSIT: {
    target_key: 'target_term_deposit',
    product_code: 'TERM_DEPOSIT',
    product_name: 'Tiết kiệm trực tuyến iDepo',
    category: 'Savings',
    badge: 'Lãi suất ưu đãi +0.5%',
    description:
      'Gửi tiết kiệm linh hoạt mọi lúc mọi nơi trên MyVIB, kỳ hạn đa dạng từ 1-36 tháng với lãi suất cạnh tranh.',
    threshold: 0.35,
    highlights: ['Kỳ hạn linh hoạt 1 – 36 tháng', 'Cộng thêm 0.5%/năm khi gửi online', 'Rút trước hạn từng phần', 'Số tiền gửi tối thiểu 1 triệu VND'],
  },
  CONSUMER_LOAN: {
    target_key: 'target_loan',
    product_code: 'CONSUMER_LOAN',
    product_name: 'Vay tiêu dùng tín chấp MyVIB',
    category: 'Lending',
    badge: 'Giải ngân 15 phút',
    description:
      'Phê duyệt tự động hạn mức đến 100 triệu không cần chứng minh thu nhập phức tạp, lãi suất chỉ từ 0.8%/tháng.',
    threshold: 0.4,
    highlights: ['Hạn mức đến 100 triệu VND', 'Lãi suất từ 0.8%/tháng', 'Không cần tài sản đảm bảo', 'Giải ngân trong 15 phút'],
  },
}

export const productCatalog = Object.values(PRODUCTS)

function rec(code, score, reasons) {
  const { highlights, threshold, ...p } = PRODUCTS[code]
  return {
    ...p,
    score,
    percent: Math.round(score * 1000) / 10,
    recommended: score >= threshold,
    reasons,
  }
}

function buildPrediction(customerNumber, recs) {
  const sorted = [...recs].sort((a, b) => b.score - a.score)
  const top = sorted[0]
  return {
    customer_number: customerNumber,
    top_product: { code: top.product_code, name: top.product_name, score: top.score, percent: top.percent },
    summary_explanation: `Khách hàng có xác suất quan tâm cao nhất đến ${top.product_name} (${top.percent}%), do ${top.reasons[0].toLowerCase()}`,
    recommendations: sorted,
  }
}

export const customers = {
  '00992830': {
    profile: {
      customer_number: '00992830',
      full_name: 'Nguyễn Thị Minh Anh',
      segment: 'Khách hàng cá nhân',
      age: 28,
      tenure_days: 412,
      email: 'minhanh@example.com',
      phone: '0901 234 567',
    },
    accounts: [
      { id: 'CA-001', type: 'Tài khoản thanh toán', number: '0123 4567 8901', balance: 48_650_000 },
      { id: 'DC-001', type: 'Thẻ ghi nợ VIB Online Plus', number: '**** **** **** 2830', balance: null },
    ],
    prediction: buildPrediction('00992830', [
      rec('TERM_DEPOSIT', 0.8732, [
        'Số dư tài khoản thanh toán CASA dồi dào (~48.7 triệu VND), đề xuất gửi tiết kiệm để tối ưu lãi suất sinh lời.',
        'Khách hàng đã tra cứu bảng lãi suất 6 lần trên MyVIB.',
        'Khách hàng gắn bó lâu dài (412 ngày), đủ điều kiện hưởng lãi suất bậc thang iDepo VIP.',
      ]),
      rec('CREDIT_CARD', 0.6215, [
        'Tần suất giao dịch mua sắm/thanh toán cao (34 giao dịch, tổng 27.4M VND), thẻ VIB Super Card giúp hoàn tiền đến 15%.',
        'Đã kích hoạt thẻ thanh toán nội địa/quốc tế, đủ điều kiện cấp trước hạn mức thẻ tín dụng.',
      ]),
      rec('CONSUMER_LOAN', 0.1874, ['Hỗ trợ tài chính nhanh chóng phục vụ nhu cầu chi tiêu linh hoạt.']),
    ]),
  },
  '01234567': {
    profile: {
      customer_number: '01234567',
      full_name: 'Trần Văn Hùng',
      segment: 'Khách hàng cá nhân',
      age: 35,
      tenure_days: 95,
      email: 'hung.tran@example.com',
      phone: '0912 888 999',
    },
    accounts: [{ id: 'CA-002', type: 'Tài khoản thanh toán', number: '0987 6543 2101', balance: 3_215_000 }],
    prediction: buildPrediction('01234567', [
      rec('CONSUMER_LOAN', 0.7921, [
        'Có hành vi tìm hiểu và tra cứu biểu phí/khoản vay trên ứng dụng MyVIB.',
        'Dòng tiền giao dịch MyVIB đều đặn, đủ điều kiện phê duyệt khoản vay thấu chi tức thì.',
        'Hồ sơ tín dụng đạt chuẩn tín nhiệm VIB, miễn sao kê thu nhập giấy tờ.',
      ]),
      rec('CREDIT_CARD', 0.4512, [
        'Thường xuyên thanh toán số (Ví điện tử / QR Code), thanh toán qua thẻ tín dụng an toàn và tiện lợi hơn.',
      ]),
      rec('TERM_DEPOSIT', 0.0931, ['Sản phẩm sinh lời an toàn, bảo toàn vốn tối ưu cho khách hàng ngân hàng số.']),
    ]),
  },
}

export const DEMO_CUSTOMER_IDS = Object.keys(customers)

const today = new Date()
const daysAgo = (n, h = 10) => {
  const d = new Date(today)
  d.setDate(d.getDate() - n)
  d.setHours(h, 15, 0, 0)
  return d.toISOString()
}

export const transactions = [
  { id: 't1', date: daysAgo(0, 9), description: 'Thanh toán QR - Highlands Coffee', category: 'QR', amount: -65_000 },
  { id: 't2', date: daysAgo(0, 8), description: 'Nhận lương tháng 10 - CTY ABC', category: 'Chuyển khoản', amount: 18_500_000 },
  { id: 't3', date: daysAgo(1, 20), description: 'Nạp tiền điện thoại Viettel', category: 'Nạp tiền', amount: -200_000 },
  { id: 't4', date: daysAgo(2, 12), description: 'Thanh toán Shopee qua ví điện tử', category: 'Ví điện tử', amount: -1_249_000 },
  { id: 't5', date: daysAgo(3, 18), description: 'Chuyển khoản đến Lê Thu Hà', category: 'Chuyển khoản', amount: -2_000_000 },
  { id: 't6', date: daysAgo(4, 7), description: 'Hóa đơn điện EVN tháng 9', category: 'Hóa đơn', amount: -785_400 },
  { id: 't7', date: daysAgo(5, 21), description: 'Thanh toán QR - Circle K', category: 'QR', amount: -48_000 },
  { id: 't8', date: daysAgo(6, 14), description: 'Hóa đơn Internet FPT', category: 'Hóa đơn', amount: -260_000 },
  { id: 't9', date: daysAgo(8, 11), description: 'Nhận chuyển khoản từ Phạm Quốc Bảo', category: 'Chuyển khoản', amount: 1_500_000 },
  { id: 't10', date: daysAgo(10, 19), description: 'Thanh toán Grab qua ví điện tử', category: 'Ví điện tử', amount: -156_000 },
  { id: 't11', date: daysAgo(12, 9), description: 'Hóa đơn nước Sawaco', category: 'Hóa đơn', amount: -184_000 },
  { id: 't12', date: daysAgo(15, 16), description: 'Thanh toán QR - Bách Hóa Xanh', category: 'QR', amount: -412_500 },
]

// Từ ai/models/training_metrics.json
export const modelMetrics = {
  num_customers: 290223,
  created_at: '2026-10-18T17:15:35',
  results: {
    target_creditcard: { roc_auc: 0.9891, precision: 0.864, recall: 0.9207, f1: 0.8915 },
    target_term_deposit: { roc_auc: 0.9716, precision: 0.6662, recall: 0.8961, f1: 0.7642 },
    target_loan: { roc_auc: 0.9711, precision: 0.8718, recall: 0.9152, f1: 0.893 },
  },
  top_drivers: {
    target_creditcard: [
      { feature: 'has_loan', importance: 0.7147 },
      { feature: 'max_loan_count', importance: 0.0559 },
      { feature: 'channel_auto_job', importance: 0.0493 },
      { feature: 'num_lending_months', importance: 0.0301 },
      { feature: 'avg_loan_amount_mean', importance: 0.0219 },
    ],
    target_term_deposit: [
      { feature: 'avg_ca_balance_min', importance: 0.1724 },
      { feature: 'num_deposit_months', importance: 0.1305 },
      { feature: 'max_debitcards', importance: 0.0722 },
      { feature: 'is_female', importance: 0.0576 },
      { feature: 'avg_loan_amount_max', importance: 0.052 },
    ],
    target_loan: [
      { feature: 'has_creditcard', importance: 0.1817 },
      { feature: 'max_debitcards', importance: 0.1701 },
      { feature: 'has_debitcard', importance: 0.1421 },
      { feature: 'max_creditcards', importance: 0.0936 },
      { feature: 'max_td_accounts', importance: 0.0632 },
    ],
  },
}

export function getProduct(code) {
  return PRODUCTS[code]
}
