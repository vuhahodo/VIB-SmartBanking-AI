import { ArrowDownLeft, ArrowUpRight } from 'lucide-react'
import { formatDateTime, formatSignedVND } from '../utils/format'

export default function TransactionList({ items }) {
  if (!items.length) return <p className="muted center">Không có giao dịch nào.</p>
  return (
    <ul className="tx-list">
      {items.map((t) => {
        const income = t.amount > 0
        return (
          <li key={t.id}>
            <div className={`tx-icon ${income ? 'in' : 'out'}`}>
              {income ? <ArrowDownLeft size={16} /> : <ArrowUpRight size={16} />}
            </div>
            <div className="tx-main">
              <strong>{t.description}</strong>
              <span className="muted">
                {formatDateTime(t.date)} · {t.category}
              </span>
            </div>
            <span className={`tx-amount ${income ? 'in' : ''}`}>{formatSignedVND(t.amount)}</span>
          </li>
        )
      })}
    </ul>
  )
}
