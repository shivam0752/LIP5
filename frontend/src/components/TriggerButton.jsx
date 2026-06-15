import { useState } from 'react'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * TriggerButton — date-range picker + manual pipeline run button.
 * Props:
 *   onTriggered(runId) — callback after successful trigger
 *   disabled           — disables the button (e.g. pipeline already running)
 */
export default function TriggerButton({ onTriggered, disabled }) {
  const today = new Date()
  const lastWeek = new Date(today)
  lastWeek.setDate(today.getDate() - 7)

  const fmt = (d) => d.toISOString().split('T')[0]

  const [startDate, setStartDate] = useState(fmt(lastWeek))
  const [endDate,   setEndDate]   = useState(fmt(today))
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)
  const [success,   setSuccess]   = useState(null)

  async function handleTrigger() {
    if (!startDate || !endDate) return
    if (startDate > endDate) { setError('Start date must be before end date.'); return }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const res = await fetch(`${API}/api/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_date: startDate, end_date: endDate }),
      })

      if (res.status === 409) {
        setError('A pipeline run is already in progress.')
        return
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(body.detail ?? `Server error (${res.status})`)
        return
      }

      const data = await res.json()
      setSuccess(`Pipeline queued — Run ID: ${data.run_id}`)
      onTriggered?.(data.run_id)
    } catch (e) {
      setError(`Network error: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="card-title">Manual Pipeline Trigger</div>

      <div className="grid-2" style={{ gap: 12 }}>
        <div>
          <label htmlFor="trigger-start">Start Date</label>
          <input
            id="trigger-start"
            type="date"
            className="input"
            value={startDate}
            max={endDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="trigger-end">End Date</label>
          <input
            id="trigger-end"
            type="date"
            className="input"
            value={endDate}
            min={startDate}
            max={fmt(today)}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
      </div>

      <button
        id="trigger-run-btn"
        className="btn btn-primary"
        onClick={handleTrigger}
        disabled={disabled || loading}
        aria-busy={loading}
      >
        {loading
          ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Running…</>
          : <><span aria-hidden="true">▶</span> Run Pipeline</>
        }
      </button>

      {error   && <div className="alert alert-error"   role="alert">{error}</div>}
      {success && <div className="alert alert-success" role="status">{success}</div>}
    </div>
  )
}
