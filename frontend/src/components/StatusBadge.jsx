/**
 * StatusBadge — animated pipeline stage status indicator.
 * Props: status ("idle" | "running" | "success" | "error")
 */
export default function StatusBadge({ status }) {
  const config = {
    idle:    { label: 'Idle',    emoji: '○' },
    running: { label: 'Running', emoji: '◉' },
    success: { label: 'Done',    emoji: '✓' },
    error:   { label: 'Error',   emoji: '✕' },
  }

  const { label, emoji } = config[status] ?? config.idle

  return (
    <span className={`badge badge-${status}`} aria-label={`Status: ${label}`}>
      <span className="badge-dot" aria-hidden="true" />
      {emoji} {label}
    </span>
  )
}
