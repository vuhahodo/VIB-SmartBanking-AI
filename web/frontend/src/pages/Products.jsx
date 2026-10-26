import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useAsync } from '../utils/useAsync'
import { CATEGORY_LABEL } from '../utils/format'
import ProductIcon from '../components/ProductIcon'
import { ErrorBox, Skeleton } from '../components/States'

const FILTERS = ['All', 'Cards', 'Savings', 'Lending']

export default function Products() {
  const { customerId } = useAuth()
  const [filter, setFilter] = useState('All')
  const products = useAsync(() => api.getProducts(), [])
  const recs = useAsync(() => api.getRecommendations(customerId), [customerId])

  const scoreOf = (code) => recs.data?.recommendations.find((r) => r.product_code === code)
  const list = (products.data ?? []).filter((p) => filter === 'All' || p.category === filter)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Sản phẩm tài chính</h1>
          <p className="muted">Mức độ phù hợp được AI tính riêng cho hồ sơ của bạn.</p>
        </div>
      </div>

      <div className="tabs">
        {FILTERS.map((f) => (
          <button key={f} className={`tab ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
            {f === 'All' ? 'Tất cả' : CATEGORY_LABEL[f]}
          </button>
        ))}
      </div>

      {products.error && <ErrorBox error={products.error} />}
      <div className="grid-3">
        {products.loading ? (
          <Skeleton height={300} count={3} />
        ) : (
          list.map((p) => {
            const s = scoreOf(p.product_code)
            return (
              <article key={p.product_code} className="card product-card">
                <div className="product-card-head">
                  <ProductIcon category={p.category} />
                  <span className="tag">{CATEGORY_LABEL[p.category]}</span>
                </div>
                <h3>{p.product_name}</h3>
                <span className="badge">{p.badge}</span>
                <p className="muted">{p.description}</p>
                {s && (
                  <div className={`match ${s.recommended ? 'good' : ''}`}>
                    <Sparkles size={15} /> Độ phù hợp AI: <b>{s.percent}%</b>
                  </div>
                )}
                <Link to={`/products/${p.product_code}`} className="btn btn-outline">
                  Xem chi tiết <ArrowRight size={16} />
                </Link>
              </article>
            )
          })
        )}
      </div>
    </div>
  )
}
