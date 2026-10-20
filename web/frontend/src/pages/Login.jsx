import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Lock, ShieldCheck, Sparkles, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { api, DEMO_PASSWORD } from '../api/client'
import { useAsync } from '../utils/useAsync'
import Logo from '../components/Logo'

export default function Login() {
  const { customerId, login } = useAuth()
  const [id, setId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  // Backend tắt DEMO_MODE thì endpoint trả 404 -> không hiện gợi ý
  const demo = useAsync(() => api.getDemoAccounts(), [])

  if (customerId) return <Navigate to="/" replace />

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(id.trim(), password)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <section className="login-hero">
        <Logo light />
        <div>
          <h1>Ngân hàng số thông minh, hiểu bạn hơn mỗi ngày.</h1>
          <p>AI phân tích hành vi giao dịch để gợi ý đúng sản phẩm tài chính bạn cần — thẻ tín dụng, tiết kiệm hay khoản vay.</p>
          <ul className="hero-points">
            <li>
              <Sparkles size={18} /> Gợi ý cá nhân hóa theo thời gian thực
            </li>
            <li>
              <ShieldCheck size={18} /> Bảo mật chuẩn ngân hàng
            </li>
          </ul>
        </div>
        <small>© 2026 VIB SmartBanking — Đồ án môn học</small>
      </section>

      <section className="login-form-wrap">
        <form className="card login-form" onSubmit={onSubmit}>
          <h2>Đăng nhập</h2>
          <p className="muted">Sử dụng mã khách hàng để truy cập SmartBanking.</p>

          <label className="field">
            <span>Mã khách hàng</span>
            <div className="input-icon">
              <User size={18} />
              <input value={id} onChange={(e) => setId(e.target.value)} placeholder="VD: 00992830" required />
            </div>
          </label>
          <label className="field">
            <span>Mật khẩu</span>
            <div className="input-icon">
              <Lock size={18} />
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
            </div>
          </label>

          {error && <div className="form-error">{error}</div>}

          <button className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>

          {demo.data?.length > 0 && (
            <div className="demo-hint">
              Tài khoản demo (mật khẩu {DEMO_PASSWORD}):
              <div className="demo-ids">
                {demo.data.map((d) => (
                  <button
                    type="button"
                    key={d.customer_number}
                    className="chip"
                    title={d.full_name}
                    onClick={() => {
                      setId(d.customer_number)
                      setPassword(DEMO_PASSWORD)
                    }}
                  >
                    {d.customer_number}
                  </button>
                ))}
              </div>
            </div>
          )}
        </form>
      </section>
    </div>
  )
}
