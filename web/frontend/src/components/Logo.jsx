export default function Logo({ light = false }) {
  return (
    <div className={`logo ${light ? 'light' : ''}`}>
      <svg viewBox="0 0 32 32" width="34" height="34" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="var(--brand)" />
        <path d="M8 10l8 13 8-13" stroke="var(--accent)" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>
        VIB <b>SmartBanking</b>
      </span>
    </div>
  )
}
