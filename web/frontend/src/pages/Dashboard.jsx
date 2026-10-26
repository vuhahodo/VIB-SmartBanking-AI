import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeftRight, Eye, EyeOff, QrCode, Receipt, Smartphone, Sparkles } from 'lucide-react'
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

  const firstName = customer.data?.profile.full_name.split(' ').pop()
  const mainAccount = customer.data?.accounts.find((a) => a.balance !== null)

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
                <span>{mainAccount.type}</span>
                <button className="icon-btn ghost" onClick={() => setHidden((h) => !h)} aria-label="Ẩn/hiện số dư">
                  {hidden ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              <div className="balance-amount">{hidden ? '••••••••' : formatVND(mainAccount.balance)}</div>
              <div className="balance-number">STK: {mainAccount.number}</div>
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
