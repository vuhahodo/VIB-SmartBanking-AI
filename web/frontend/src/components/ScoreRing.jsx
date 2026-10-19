// Vòng tròn hiển thị % phù hợp do AI dự đoán
export default function ScoreRing({ percent, size = 64 }) {
  const r = 26
  const c = 2 * Math.PI * r
  const level = percent >= 60 ? 'high' : percent >= 35 ? 'mid' : 'low'
  return (
    <div className={`score-ring ${level}`} style={{ width: size, height: size }}>
      <svg viewBox="0 0 64 64">
        <circle cx="32" cy="32" r={r} className="track" />
        <circle cx="32" cy="32" r={r} className="bar" strokeDasharray={c} strokeDashoffset={c * (1 - percent / 100)} />
      </svg>
      <span>{Math.round(percent)}%</span>
    </div>
  )
}
