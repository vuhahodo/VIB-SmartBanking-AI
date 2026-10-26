import { BrainCircuit, Database } from 'lucide-react'
import { api } from '../api/client'
import { useAsync } from '../utils/useAsync'
import { formatDate } from '../utils/format'
import { ErrorBox, Skeleton } from '../components/States'

const MODEL_LABEL = {
  target_creditcard: 'Thẻ tín dụng Super Card',
  target_term_deposit: 'Tiết kiệm iDepo',
  target_loan: 'Vay tiêu dùng',
}

const METRICS = [
  ['roc_auc', 'ROC-AUC'],
  ['f1', 'F1'],
  ['precision', 'Precision'],
  ['recall', 'Recall'],
]

export default function AIInsights() {
  const { data, loading, error } = useAsync(() => api.getModelMetrics(), [])

  if (loading) return <Skeleton height={300} count={2} />
  if (error) return <ErrorBox error={error} />

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>AI Insights</h1>
          <p className="muted">Hiệu năng mô hình Next-Best-Action (XGBoost) đang phục vụ gợi ý.</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card stat">
          <span className="muted">
            <Database size={15} /> Số khách hàng huấn luyện
          </span>
          <strong>{data.num_customers.toLocaleString('vi-VN')}</strong>
        </div>
        <div className="card stat">
          <span className="muted">
            <BrainCircuit size={15} /> Cập nhật mô hình
          </span>
          <strong>{formatDate(data.created_at)}</strong>
        </div>
      </div>

      <div className="grid-3">
        {Object.entries(data.results).map(([key, m]) => (
          <section key={key} className="card">
            <h3>{MODEL_LABEL[key] ?? key}</h3>
            <div className="metric-grid">
              {METRICS.map(([k, label]) => (
                <div key={k} className="metric">
                  <span className="muted">{label}</span>
                  <strong>{m[k].toFixed(3)}</strong>
                </div>
              ))}
            </div>
            <h4 className="muted">Đặc trưng quan trọng nhất</h4>
            <ul className="drivers">
              {data.top_drivers[key]?.slice(0, 5).map((d) => (
                <li key={d.feature}>
                  <code>{d.feature}</code>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(d.importance / data.top_drivers[key][0].importance) * 100}%` }} />
                  </div>
                  <span>{(d.importance * 100).toFixed(1)}%</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}
