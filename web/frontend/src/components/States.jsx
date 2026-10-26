import { AlertTriangle } from 'lucide-react'

export function Skeleton({ height = 120, count = 1 }) {
  return Array.from({ length: count }, (_, i) => <div key={i} className="skeleton" style={{ height }} />)
}

export function ErrorBox({ error }) {
  return (
    <div className="error-box">
      <AlertTriangle size={18} />
      <span>{error?.message || 'Đã có lỗi xảy ra'}</span>
    </div>
  )
}
