import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeftRight, Eye, EyeOff, FileText, QrCode, Receipt, Smartphone, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useAsync } from '../utils/useAsync'
import { formatVND } from '../utils/format'
import RecommendationCard from '../components/RecommendationCard'
import TransactionList from '../components/TransactionList'
import { ErrorBox, Skeleton } from '../components/States'

const QUICK_ACTIONS = [
  { label: 'Chuyển tiền', icon: ArrowLeftRight },
  { label: 'Quét QR', icon: QrCode },
  { label: 'Nạp điện thoại', icon: Smartphone },
  { label: 'Thanh toán hóa đơn', icon: Receipt },
]

export default function Dashboard() {
  const { customerId } = useAuth()
  const [hidden, setHidden] = useState(false)
  const customer = useAsync(() => api.getCustomer(customerId), [customerId])
  const recs = useAsync(() => api.getRecommendations(customerId), [customerId])
  const txs = useAsync(() => api.getTransactions(customerId), [customerId])
  const apps = useAsync(() => api.getMyApplications(), [])

  const firstName = customer.data?.profile?.full_name?.split(' ').pop()
  const mainAccount = customer.data?.accounts?.find((a) => a.balance !== null)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Xin chào{firstName ? `, ${firstName}` : ''} 👋</h1>
          <p className="muted">Đây là tình hình tài chính của bạn hôm nay.</p>
        </div>
      </div>

      <div className="grid-dash">
        <section className="balance-card">
          {customer.loading ? (
            <Skeleton height={140} />
          ) : customer.error ? (
            <ErrorBox error={customer.error} />
          ) : (
            <>
              <div className="balance-top">
                <span>{mainAccount?.type || 'Tài khoản thanh toán'}</span>
                <button className="icon-btn ghost" onClick={() => setHidden((h) => !h)} aria-label="Ẩn/hiện số dư">
                  {hidden ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              <div className="balance-amount">{hidden ? '••••••••' : formatVND(mainAccount?.balance || 0)}</div>
              <div className="balance-number">STK: {mainAccount?.number || '---'}</div>
              <div className="quick-actions">
                {QUICK_ACTIONS.map(({ label, icon: Icon }) => (
                  <button key={label} className="qa">
                    <span>
                      <Icon size={20} />
                    </span>
                    {label}
                  </button>
                ))}
              </div>
            </>
          )}
        </section>

        <section className="card ai-summary">
          <div className="section-title">
            <Sparkles size={18} className="accent" />
            <h2>AI phân tích cho bạn</h2>
          </div>
          {recs.loading ? (
            <Skeleton height={90} />
          ) : recs.error ? (
            <ErrorBox error={recs.error} />
          ) : (
            <>
              <p>{recs.data.summary_explanation}</p>
              <div className="mini-bars">
                {recs.data.recommendations.map((r) => (
                  <div key={r.product_code} className="mini-bar">
                    <span>{r.product_name}</span>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${r.percent}%` }} />
                    </div>
                    <b>{r.percent}%</b>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>

      <section>
        <div className="section-title spread">
          <h2>Gợi ý dành riêng cho bạn</h2>
          <Link to="/products" className="link">
            Xem tất cả sản phẩm
          </Link>
        </div>
        <div className="grid-3">
          {recs.loading ? (
            <Skeleton height={320} count={3} />
          ) : (
            recs.data?.recommendations.map((r, i) => <RecommendationCard key={r.product_code} rec={r} rank={i} />)
          )}
        </div>
      </section>

      {/* Hồ sơ đăng ký từ xa của bạn */}
      <section className="card">
        <div className="section-title spread">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={20} style={{ color: 'var(--brand)' }} />
            <h2>Hồ sơ đăng ký từ xa của bạn ({apps.data?.length || 0})</h2>
          </div>
          <Link to="/products" className="link">
            + Đăng ký dịch vụ mới
          </Link>
        </div>

        {apps.loading ? (
          <Skeleton height={80} count={2} />
        ) : !apps.data || apps.data.length === 0 ? (
          <p className="muted center">Bạn chưa có hồ sơ đăng ký nào. Hãy khám phá các sản phẩm thẻ & vay được AI gợi ý bên dưới.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {apps.data.slice(0, 5).map((app) => (
              <div
                key={app.application_id}
                style={{
                  padding: '12px 16px',
                  borderRadius: 10,
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--bg)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 12,
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <strong style={{ fontFamily: 'monospace', color: 'var(--brand)' }}>{app.application_id}</strong>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: 6,
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        backgroundColor:
                          app.status === 'PRE_APPROVED'
                            ? 'var(--success-soft)'
                            : app.status === 'QUEUED_OFFLINE'
                            ? 'var(--accent-soft)'
                            : 'var(--brand-soft)',
                        color:
                          app.status === 'PRE_APPROVED'
                            ? 'var(--success)'
                            : app.status === 'QUEUED_OFFLINE'
                            ? 'var(--accent-dark)'
                            : 'var(--brand)',
                      }}
                    >
                      {app.status === 'PRE_APPROVED'
                        ? 'ĐÃ DUYỆT TỨC THÌ'
                        : app.status === 'QUEUED_OFFLINE'
                        ? 'ĐỆM OUTBOX DỰ PHÒNG'
                        : 'CHỜ THẨM ĐỊNH'}
                    </span>
                    {app.mode && (
                      <span className="tag" style={{ fontSize: '0.7rem' }}>
                        {app.mode}
                      </span>
                    )}
                  </div>
                  <p className="muted" style={{ fontSize: '0.82rem', marginTop: 4 }}>
                    Sản phẩm: <strong>{app.product_code}</strong>
                    {app.assigned_limit ? ` • Hạn mức cấp: ${formatVND(app.assigned_limit)}` : ''}
                  </p>
                  {app.decision_reason && (
                    <p style={{ fontSize: '0.78rem', color: 'var(--muted)', marginTop: 2 }}>
                      {app.decision_reason}
                    </p>
                  )}
                </div>

                <div style={{ textAlign: 'right', fontSize: '0.78rem', color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                  {app.created_at ? new Date(app.created_at).toLocaleString('vi-VN') : 'Vừa xong'}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <div className="section-title spread">
          <h2>Giao dịch gần đây</h2>
          <Link to="/transactions" className="link">
            Xem tất cả
          </Link>
        </div>
        {txs.loading ? <Skeleton height={56} count={4} /> : txs.error ? <ErrorBox error={txs.error} /> : <TransactionList items={txs.data.slice(0, 5)} />}
      </section>
    </div>
  )
}
