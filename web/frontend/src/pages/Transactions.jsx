import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useAsync } from '../utils/useAsync'
import { formatVND } from '../utils/format'
import TransactionList from '../components/TransactionList'
import { ErrorBox, Skeleton } from '../components/States'

export default function Transactions() {
  const { customerId } = useAuth()
  const { data, loading, error } = useAsync(() => api.getTransactions(customerId), [customerId])
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')

  const categories = useMemo(() => [...new Set((data ?? []).map((t) => t.category))], [data])
  const filtered = (data ?? []).filter(
    (t) => (!category || t.category === category) && t.description.toLowerCase().includes(q.toLowerCase()),
  )
  const income = filtered.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0)
  const expense = filtered.filter((t) => t.amount < 0).reduce((s, t) => s - t.amount, 0)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Lịch sử giao dịch</h1>
          <p className="muted">Theo dõi dòng tiền vào – ra trên tài khoản của bạn.</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card stat">
          <span className="muted">Tổng tiền vào</span>
          <strong className="in">{formatVND(income)}</strong>
        </div>
        <div className="card stat">
          <span className="muted">Tổng tiền ra</span>
          <strong>{formatVND(expense)}</strong>
        </div>
      </div>

      <section className="card">
        <div className="filters">
          <div className="input-icon grow">
            <Search size={18} />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm giao dịch..." />
          </div>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">Tất cả loại</option>
            {categories.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        {loading ? <Skeleton height={56} count={6} /> : error ? <ErrorBox error={error} /> : <TransactionList items={filtered} />}
      </section>
    </div>
  )
}
