import { useEffect, useState, useCallback } from 'react'
import ThemeCard, { DOMAIN_CONFIG } from '../components/ThemeCard.jsx'
import TriggerButton from '../components/TriggerButton.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Stars renderer
function Stars({ rating }) {
  return (
    <span className="stars" aria-label={`${rating} out of 5 stars`}>
      {'★'.repeat(rating)}{'☆'.repeat(5 - rating)}
    </span>
  )
}

// Domain accent for quote blocks
function domainColor(domain) {
  return DOMAIN_CONFIG[domain]?.color ?? '#868e96'
}

export default function Dashboard() {
  const [status, setStatus]   = useState(null)
  const [latestPulse, setLatestPulse] = useState(null)
  const [loadingPulse, setLoadingPulse] = useState(true)

  // ── Poll pipeline status every 3s ───────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/status`)
      if (res.ok) setStatus(await res.json())
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 3000)
    return () => clearInterval(id)
  }, [fetchStatus])

  // ── Load latest pulse ────────────────────────────────────
  const fetchLatestPulse = useCallback(async () => {
    setLoadingPulse(true)
    try {
      const res = await fetch(`${API}/api/pulses`)
      if (!res.ok) return
      const data = await res.json()
      if (data.pulses?.length > 0) {
        const latest = data.pulses[0]
        const detailRes = await fetch(`${API}/api/pulses/${latest.run_id}`)
        if (detailRes.ok) setLatestPulse(await detailRes.json())
      }
    } catch { /* ignore */ } finally {
      setLoadingPulse(false)
    }
  }, [])

  useEffect(() => { fetchLatestPulse() }, [fetchLatestPulse])

  function handleTriggered() {
    // refresh pulse and status after trigger
    setTimeout(fetchLatestPulse, 3000)
  }

  const isPipelineRunning = status?.status === 'running'

  return (
    <>
      <div className="page-header">
        <div className="flex-between">
          <div>
            <h2>Dashboard</h2>
            <p>Weekly App Store Pulse · Groww</p>
          </div>
          {status && (
            <StatusBadge status={status.status} />
          )}
        </div>
      </div>

      <div className="page-body stack" style={{ gap: 24 }}>

        {/* ── Stat row ─────────────────────────────────── */}
        {latestPulse && (
          <div className="grid-3">
            <div className="stat-chip">
              <div className="stat-value">{latestPulse.total_reviews_analyzed}</div>
              <div className="stat-label">Reviews Analysed</div>
            </div>
            <div className="stat-chip">
              <div className="stat-value">{latestPulse.top_themes?.length ?? 0}</div>
              <div className="stat-label">Top Themes</div>
            </div>
            <div className="stat-chip">
              <div className="stat-value">{latestPulse.week_ending}</div>
              <div className="stat-label">Week Ending</div>
            </div>
          </div>
        )}

        {/* ── Pipeline status stages ────────────────────── */}
        {status && status.stages?.length > 0 && (
          <div className="card">
            <div className="card-title">Pipeline Stages</div>
            <div className="stage-list">
              {status.stages.map((stage) => (
                <div key={stage.name} className="stage-row">
                  <span className="stage-name">{stage.name}</span>
                  {stage.detail && (
                    <span className="stage-detail">{stage.detail}</span>
                  )}
                  <StatusBadge status={stage.status} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Trigger ───────────────────────────────────── */}
        <TriggerButton
          disabled={isPipelineRunning}
          onTriggered={handleTriggered}
        />

        {/* ── Top themes ───────────────────────────────── */}
        {loadingPulse && (
          <div className="empty-state">
            <div className="spinner" />
            <p>Loading latest pulse…</p>
          </div>
        )}

        {!loadingPulse && latestPulse && (
          <>
            <div>
              <h3 style={{ marginBottom: 16 }}>
                📊 Top Themes
                <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: '.8rem', marginLeft: 10 }}>
                  Week ending {latestPulse.week_ending}
                </span>
              </h3>
              <div className="grid-3">
                {latestPulse.top_themes?.map((theme, i) => (
                  <ThemeCard
                    key={theme.domain}
                    domain={theme.domain}
                    summary={theme.summary}
                    rank={i + 1}
                  />
                ))}
              </div>
            </div>

            {/* ── Verbatim Quotes ───────────────────────── */}
            <div>
              <h3 style={{ marginBottom: 16 }}>💬 Verbatim Quotes</h3>
              <div className="stack">
                {latestPulse.verbatim_quotes?.map((q, i) => (
                  <div
                    key={i}
                    className="quote-block"
                    style={{ '--card-accent': domainColor(q.domain) }}
                  >
                    <p className="quote-text">"{q.quote}"</p>
                    <div className="quote-meta">
                      <Stars rating={q.rating} />
                      <span>·</span>
                      <span style={{ color: domainColor(q.domain), fontWeight: 600 }}>
                        {q.domain}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* ── Action Ideas ──────────────────────────── */}
            <div>
              <h3 style={{ marginBottom: 16 }}>🚀 Strategic Action Ideas</h3>
              <div className="stack">
                {latestPulse.action_ideas?.map((idea, i) => (
                  <div key={i} className="card" style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: 28, height: 28, borderRadius: '50%',
                        background: domainColor(idea.domain),
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        flexShrink: 0, fontSize: '.75rem', fontWeight: 700, color: 'white',
                      }}
                    >
                      {i + 1}
                    </div>
                    <div>
                      <div style={{ fontSize: '.72rem', color: domainColor(idea.domain), fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 4 }}>
                        {idea.domain}
                      </div>
                      <p style={{ color: 'var(--text-primary)', fontSize: '.9rem' }}>{idea.action}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* ── Workspace links ───────────────────────── */}
            {(latestPulse.google_doc_url || latestPulse.gmail_draft_id) && (
              <div className="card">
                <div className="card-title">Workspace Artifacts</div>
                <div className="flex-gap" style={{ flexWrap: 'wrap' }}>
                  {latestPulse.google_doc_url && (
                    <a
                      href={latestPulse.google_doc_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary btn-sm"
                    >
                      📄 Open Google Doc
                    </a>
                  )}
                  {latestPulse.gmail_draft_id && (
                    <span className="badge badge-success">
                      ✉ Gmail Draft Staged
                    </span>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {!loadingPulse && !latestPulse && (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No pulses yet</h3>
            <p>Trigger the pipeline above to generate your first weekly pulse.</p>
          </div>
        )}
      </div>
    </>
  )
}
