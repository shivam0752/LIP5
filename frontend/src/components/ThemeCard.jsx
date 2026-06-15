/**
 * ThemeCard — color-coded domain theme card for the Dashboard.
 * Props:
 *   domain  string  — one of the 5 fintech domains
 *   summary string  — 1–2 sentence theme description
 *   rank    number  — 1-indexed position (optional, for display)
 */

const DOMAIN_CONFIG = {
  'Order Execution & Latency': { color: '#ff6b6b', icon: '📈' },
  'Payments & Funding':        { color: '#ffa94d', icon: '💳' },
  'KYC & Onboarding':          { color: '#4dabf7', icon: '🪪' },
  'Customer Support Quality':  { color: '#cc5de8', icon: '🎧' },
  'App Stability & UI':        { color: '#51cf66', icon: '📱' },
  'Other':                     { color: '#868e96', icon: '🔖' },
}

export default function ThemeCard({ domain, summary, rank }) {
  const { color, icon } = DOMAIN_CONFIG[domain] ?? DOMAIN_CONFIG['Other']

  return (
    <div
      className="theme-card"
      style={{ '--card-accent': color }}
      aria-label={`Theme: ${domain}`}
    >
      <div className="theme-domain-tag">
        <span aria-hidden="true">{icon}</span>
        {rank && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>#{rank} ·</span>}
        {domain}
      </div>
      <p style={{ color: 'var(--text-secondary)', fontSize: '.9rem', lineHeight: 1.6 }}>
        {summary}
      </p>
    </div>
  )
}

export { DOMAIN_CONFIG }
