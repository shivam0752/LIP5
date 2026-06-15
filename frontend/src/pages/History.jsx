import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function formatDate(isoString) {
  try {
    return new Date(isoString).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    })
  } catch { return isoString }
}

export default function History() {
  const [pulses,  setPulses]  = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API}/api/pulses`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setPulses(data.pulses ?? [])
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <>
      <div className="page-header">
        <div className="flex-between">
          <div>
            <h2>History</h2>
            <p>All past review pulse reports</p>
          </div>
          <span style={{ fontSize: '.85rem', color: 'var(--text-muted)' }}>
            {pulses.length} pulse{pulses.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="page-body">
        {loading && (
          <div className="empty-state">
            <div className="spinner" />
            <p>Loading history…</p>
          </div>
        )}

        {error && (
          <div className="alert alert-error" role="alert" style={{ marginBottom: 20 }}>
            Failed to load pulses: {error}
          </div>
        )}

        {!loading && !error && pulses.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">🗂</div>
            <h3>No pulses yet</h3>
            <p>Run the pipeline from the Dashboard to generate your first pulse report.</p>
            <Link to="/" className="btn btn-primary btn-sm" style={{ marginTop: 8 }}>
              Go to Dashboard
            </Link>
          </div>
        )}

        {!loading && pulses.length > 0 && (
          <div className="table-wrapper">
            <table aria-label="Historical pulse reports">
              <thead>
                <tr>
                  <th>Timeline</th>
                  <th>Run ID</th>
                  <th>Reviews</th>
                  <th>Created</th>
                  <th>Google Doc</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pulses.map((pulse) => (
                  <tr key={pulse.run_id}>
                    <td>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                        {pulse.timeline}
                      </span>
                    </td>
                    <td>
                      <code style={{ fontSize: '.8rem', color: 'var(--accent-purple)' }}>
                        {pulse.run_id}
                      </code>
                    </td>
                    <td>
                      <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
                        {pulse.total_reviews_analyzed}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '.82rem' }}>
                      {formatDate(pulse.created_at)}
                    </td>
                    <td>
                      {pulse.google_doc_url ? (
                        <a
                          href={pulse.google_doc_url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-secondary btn-sm"
                          style={{ display: 'inline-flex' }}
                          aria-label={`Open Google Doc for timeline ${pulse.timeline}`}
                        >
                          📄 Open
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '.8rem' }}>—</span>
                      )}
                    </td>
                    <td>
                      <Link
                        to={`/?pulse=${pulse.run_id}`}
                        className="btn btn-secondary btn-sm"
                        aria-label={`View pulse ${pulse.run_id}`}
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
