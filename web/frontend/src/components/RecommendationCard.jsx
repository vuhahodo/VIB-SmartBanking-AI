import { Link } from 'react-router-dom'
import { ArrowRight, Check } from 'lucide-react'
import ProductIcon from './ProductIcon'
import ScoreRing from './ScoreRing'

export default function RecommendationCard({ rec, rank }) {
  return (
    <article className={`rec-card ${rank === 0 ? 'top' : ''}`}>
      {rank === 0 && <div className="rec-ribbon">Phù hợp nhất</div>}
      <div className="rec-head">
        <ProductIcon category={rec.category} />
        <div className="rec-title">
          <h3>{rec.product_name}</h3>
          <span className="badge">{rec.badge}</span>
        </div>
        <ScoreRing percent={rec.percent} />
      </div>
      <p className="muted">{rec.description}</p>
      <ul className="reasons">
        {rec.reasons.slice(0, 2).map((r) => (
          <li key={r}>
            <Check size={15} />
            <span>{r}</span>
          </li>
        ))}
      </ul>
      <Link to={`/products/${rec.product_code}`} className={`btn ${rank === 0 ? 'btn-accent' : 'btn-outline'}`}>
        {rec.recommended ? 'Đăng ký ngay' : 'Tìm hiểu thêm'} <ArrowRight size={16} />
      </Link>
    </article>
  )
}
