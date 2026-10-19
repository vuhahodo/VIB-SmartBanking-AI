import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useAsync } from '../utils/useAsync'
import ProductIcon from '../components/ProductIcon'
import ScoreRing from '../components/ScoreRing'
import { ErrorBox, Skeleton } from '../components/States'

// Trường riêng của form đăng ký theo từng loại sản phẩm
const EXTRA_FIELDS = {
  Cards: [{ name: 'monthly_income', label: 'Thu nhập hàng tháng (VND)', type: 'number', placeholder: '15000000' }],
  Savings: [
    { name: 'amount', label: 'Số tiền gửi (VND)', type: 'number', placeholder: '50000000' },
    { name: 'term_months', label: 'Kỳ hạn', type: 'select', options: ['1', '3', '6', '12', '24', '36'] },
  ],
  Lending: [
    { name: 'amount', label: 'Số tiền vay (VND)', type: 'number', placeholder: '30000000' },
    { name: 'term_months', label: 'Thời hạn vay (tháng)', type: 'select', options: ['6', '12', '24', '36'] },
  ],
}

export default function ProductDetail() {
  const { code } = useParams()
  const { customerId } = useAuth()
  const product = useAsync(() => api.getProduct(code), [code])
  const customer = useAsync(() => api.getCustomer(customerId), [customerId])
  const recs = useAsync(() => api.getRecommendations(customerId), [customerId])
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  if (product.loading || customer.loading) return <Skeleton height={400} />
  if (product.error) return <ErrorBox error={product.error} />

  const p = product.data
  const profile = customer.data?.profile
  const rec = recs.data?.recommendations.find((r) => r.product_code === code)

  async function onSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const form = Object.fromEntries(new FormData(e.currentTarget))
      const res = await api.submitApplication({ customer_number: customerId, product_code: code, ...form })
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      <Link to="/products" className="link back">
        <ArrowLeft size={16} /> Quay lại danh sách
      </Link>

      <div className="detail-grid">
        <div className="stack">
          <section className="card detail-hero">
            <ProductIcon category={p.category} size={28} />
            <div>
              <h1>{p.product_name}</h1>
              <span className="badge">{p.badge}</span>
            </div>
          </section>
          <section className="card">
            <h2>Giới thiệu</h2>
            <p>{p.description}</p>
            <ul className="highlights">
              {p.highlights?.map((h) => (
                <li key={h}>
                  <CheckCircle2 size={18} /> {h}
                </li>
              ))}
            </ul>
          </section>

          {rec && (
            <section className="card ai-why">
              <div className="section-title">
                <Sparkles size={18} className="accent" />
                <h2>Vì sao AI gợi ý sản phẩm này?</h2>
              </div>
              <div className="ai-why-body">
                <ScoreRing percent={rec.percent} size={84} />
                <ul className="reasons">
                  {rec.reasons.map((r) => (
                    <li key={r}>
                      <CheckCircle2 size={15} />
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}
        </div>

        <section className="card apply">
          {result ? (
            <div className="success">
              <CheckCircle2 size={48} />
              <h2>Đăng ký thành công!</h2>
              <p className="muted">
                Mã hồ sơ <b>{result.application_id}</b> đang được xử lý. VIB sẽ liên hệ bạn trong vòng 24 giờ.
              </p>
              <Link to="/" className="btn btn-primary">
                Về trang tổng quan
              </Link>
            </div>
          ) : (
            <form onSubmit={onSubmit}>
              <h2>Đăng ký trực tuyến</h2>
              <p className="muted">Thông tin đã được điền sẵn từ hồ sơ của bạn.</p>
              <label className="field">
                <span>Họ và tên</span>
                <input name="full_name" defaultValue={profile?.full_name} required />
              </label>
              <label className="field">
                <span>Số điện thoại</span>
                <input name="phone" defaultValue={profile?.phone} required />
              </label>
              <label className="field">
                <span>Email</span>
                <input name="email" type="email" defaultValue={profile?.email} required />
              </label>
              {EXTRA_FIELDS[p.category]?.map((f) => (
                <label className="field" key={f.name}>
                  <span>{f.label}</span>
                  {f.type === 'select' ? (
                    <select name={f.name} defaultValue={f.options[2] ?? f.options[0]}>
                      {f.options.map((o) => (
                        <option key={o} value={o}>
                          {o} tháng
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input name={f.name} type={f.type} placeholder={f.placeholder} min="0" required />
                  )}
                </label>
              ))}
              <label className="checkbox">
                <input type="checkbox" required /> Tôi đồng ý với điều khoản & điều kiện của VIB
              </label>
              {error && <div className="form-error">{error}</div>}
              <button className="btn btn-accent btn-block" disabled={submitting}>
                {submitting ? 'Đang gửi...' : 'Gửi đăng ký'}
              </button>
            </form>
          )}
        </section>
      </div>
    </div>
  )
}
