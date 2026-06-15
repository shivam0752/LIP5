import { useEffect, useState, useRef, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function levelColor(level) {
  return {
    INFO:    'var(--accent-blue)',
    WARNING: 'var(--accent-orange)',
    ERROR:   'var(--accent-red)',
    DEBUG:   'var(--text-muted)',
  }[level] ?? 'var(--text-secondary)'
}

function LogLine({ entry }) {
  const ts = new Date(entry.ts).toLocaleTimeString('en-GB', { hour12: false })
  return (
    <div className="log-line">
      <span className="log-ts">{ts}</span>
      <span style={{ color: levelColor(entry.level), width: 60, flexShrink: 0, fontWeight: 600 }}>
        {entry.level}
      </span>
      <span className="log-msg">
        {entry.run_id && (
          <span style={{ color: 'var(--accent-purple)', marginRight: 6 }}>
            [{entry.run_id}]
          </span>
        )}
        {entry.message}
      </span>
    </div>
  )
}

export default function Logs() {
  const [entries, setEntries] = useState([])
  const [total,   setTotal]   = useState(0)
  const [page,    setPage]    = useState(1)
  const [pageSize]            = useState(100)
  const [loading, setLoading] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [levelFilter, setLevelFilter] = useState('ALL')
  const terminalRef = useRef(null)

  const fetchLogs = useCallback(async (p = page) => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/logs?page=${p}&page_size=${pageSize}`)
      if (!res.ok) return
      const data = await res.json()
      setEntries(data.entries ?? [])
      setTotal(data.total ?? 0)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  // Poll every 5s
  useEffect(() => {
    fetchLogs(1)
    const id = setInterval(() => fetchLogs(1), 5000)
    return () => clearInterval(id)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [entries, autoScroll])

  const filtered = levelFilter === 'ALL'
    ? entries
    : entries.filter(e => e.level === levelFilter)

  const totalPages = Math.ceil(total / pageSize)

  return (
    <>
      <div className="page-header">
        <div className="flex-between">
          <div>
            <h2>Logs</h2>
            <p>Real-time pipeline log stream · polls every 5 seconds</p>
          </div>
          <div className="flex-gap">
            <span style={{ fontSize: '.8rem', color: 'var(--text-muted)' }}>
              {total} total entries
            </span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => fetchLogs(1)}
              aria-label="Refresh logs"
            >
              ↺ Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="page-body stack" style={{ gap: 16 }}>
        {/* Controls */}
        <div className="flex-between" style={{ flexWrap: 'wrap', gap: 12 }}>
          <div className="flex-gap">
            <label htmlFor="level-filter" style={{ margin: 0, color: 'var(--text-secondary)' }}>
              Level:
            </label>
            <select
              id="level-filter"
              className="select"
              style={{ width: 120 }}
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
            >
              <option value="ALL">All</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="DEBUG">DEBUG</option>
            </select>
          </div>

          <label className="flex-gap" style={{ cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={e => setAutoScroll(e.target.checked)}
              id="auto-scroll-toggle"
            />
            <span style={{ fontSize: '.875rem', color: 'var(--text-secondary)' }}>
              Auto-scroll
            </span>
          </label>
        </div>

        {/* Terminal */}
        <div
          className="log-terminal"
          ref={terminalRef}
          role="log"
          aria-live="polite"
          aria-label="Pipeline log output"
        >
          {loading && entries.length === 0 && (
            <div style={{ color: 'var(--text-muted)', padding: '8px 0' }}>Loading logs…</div>
          )}
          {filtered.length === 0 && !loading && (
            <div style={{ color: 'var(--text-muted)', padding: '8px 0' }}>
              No log entries found.
            </div>
          )}
          {/* Show newest at bottom — entries come newest-first from API so reverse */}
          {[...filtered].reverse().map((entry, i) => (
            <LogLine key={i} entry={entry} />
          ))}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex-between">
            <button
              className="btn btn-secondary btn-sm"
              disabled={page <= 1}
              onClick={() => { setPage(p => p - 1); fetchLogs(page - 1) }}
            >
              ← Prev
            </button>
            <span style={{ fontSize: '.85rem', color: 'var(--text-muted)' }}>
              Page {page} of {totalPages}
            </span>
            <button
              className="btn btn-secondary btn-sm"
              disabled={page >= totalPages}
              onClick={() => { setPage(p => p + 1); fetchLogs(page + 1) }}
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </>
  )
}
