// Lớp gọi API duy nhất của frontend. Các trang chỉ import từ đây,
// nên khi backend FastAPI sẵn sàng chỉ cần đặt VITE_USE_MOCK=false.
import * as mock from '../mock/data'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
const BASE = import.meta.env.VITE_API_BASE || '/api'

const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms))

async function http(path, options = {}) {
  const token = localStorage.getItem('vib_token')
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (res.status === 401 && token) {
    // Token hết hạn / không hợp lệ -> về trang đăng nhập
    localStorage.removeItem('vib_token')
    localStorage.removeItem('vib_customer')
    window.location.assign('/login')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = Array.isArray(body.detail) ? 'Dữ liệu không hợp lệ, vui lòng kiểm tra lại' : body.detail
    throw new Error(detail || `Lỗi ${res.status}`)
  }
  return res.json()
}

function mockCustomer(id) {
  const c = mock.customers[id]
  if (!c) throw new Error('Không tìm thấy khách hàng')
  return c
}

export const api = {
  // POST /api/auth/login -> { access_token, customer_number }
  async login(customerNumber, password) {
    if (!USE_MOCK) {
      return http('/auth/login', { method: 'POST', body: JSON.stringify({ customer_number: customerNumber, password }) })
    }
    await delay()
    if (!mock.customers[customerNumber] || !password) throw new Error('Mã khách hàng hoặc mật khẩu không đúng')
    return { access_token: `mock-${customerNumber}`, customer_number: customerNumber }
  },

  // GET /api/auth/demo-accounts -> [{ customer_number, full_name }]
  async getDemoAccounts() {
    if (!USE_MOCK) return http('/auth/demo-accounts')
    return mock.DEMO_CUSTOMER_IDS.map((id) => ({ customer_number: id, full_name: mock.customers[id].profile.full_name }))
  },

  // GET /api/customers/{id} -> { profile, accounts }
  async getCustomer(id) {
    if (!USE_MOCK) return http(`/customers/${id}`)
    await delay()
    const { profile, accounts } = mockCustomer(id)
    return { profile, accounts }
  },

  // GET /api/recommendations/{id} -> output của VIBRecommendationEngine.predict_single()
  async getRecommendations(id) {
    if (!USE_MOCK) return http(`/recommendations/${id}`)
    await delay(600)
    return mockCustomer(id).prediction
  },

  // GET /api/customers/{id}/transactions -> [{ id, date, description, category, amount }]
  async getTransactions(id) {
    if (!USE_MOCK) return http(`/customers/${id}/transactions`)
    await delay()
    return mock.transactions
  },

  // GET /api/products -> [product]
  async getProducts() {
    if (!USE_MOCK) return http('/products')
    await delay(200)
    return mock.productCatalog
  },

  async getProduct(code) {
    if (!USE_MOCK) return http(`/products/${code}`)
    await delay(200)
    const p = mock.getProduct(code)
    if (!p) throw new Error('Sản phẩm không tồn tại')
    return p
  },

  // POST /api/applications -> { application_id, status }
  async submitApplication(payload) {
    if (!USE_MOCK) return http('/applications', { method: 'POST', body: JSON.stringify(payload) })
    await delay(800)
    return { application_id: `APP-${Date.now().toString().slice(-6)}`, status: 'PENDING' }
  },

  // GET /api/ai/metrics -> nội dung training_metrics.json
  async getModelMetrics() {
    if (!USE_MOCK) return http('/ai/metrics')
    await delay(200)
    return mock.modelMetrics
  },
}

export const isMock = USE_MOCK
export const DEMO_PASSWORD = '123456'
