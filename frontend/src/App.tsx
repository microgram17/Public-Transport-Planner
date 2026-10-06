import { useEffect, useState } from 'react'
import './App.css'

type Stop = {
  stop_id: string
  stop_name: string | null
  display_name: string | null
  stop_lat: number | null
  stop_lon: number | null
  location_type: number | null
  parent_station: string | null
  platform_code: string | null
}

type StopsPage = {
  items: Stop[]
  total: number
  limit: number
  offset: number
}

function App() {
  const [stops, setStops] = useState<Stop[]>([])
  const [totalStops, setTotalStops] = useState(0)
  const [selectedStopId, setSelectedStopId] = useState<string | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  useEffect(() => {
    async function loadStops() {
      try {
        const response = await fetch('/api/stops?limit=100')

        if (!response.ok) {
          throw new Error(`Stops request failed with ${response.status}`)
        }

        const page: StopsPage = await response.json()
        setStops(page.items)
        setTotalStops(page.total)
        setSelectedStopId(page.items[0]?.stop_id ?? null)
        setStatus('ready')
      } catch {
        setStatus('error')
      }
    }

    void loadStops()
  }, [])

  const selectedStop = stops.find((stop) => stop.stop_id === selectedStopId) ?? null
  const stopLabel = (stop: Stop) => stop.display_name ?? stop.stop_name ?? 'Unnamed stop'
  const coordinates = selectedStop?.stop_lat != null && selectedStop.stop_lon != null
    ? `${selectedStop.stop_lat.toFixed(5)}, ${selectedStop.stop_lon.toFixed(5)}`
    : 'Not available'

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">↗</span>
          <div>
            <p className="eyebrow">Public transport</p>
            <h1>Transport Planner</h1>
          </div>
        </div>
      </header>

      <section className="intro">
        <p className="eyebrow">Explore the network</p>
        <h2>Find a stop</h2>
        <label className="search-field">
          <span className="search-icon" aria-hidden="true">⌕</span>
          <input type="search" placeholder="Search stops" aria-label="Search stops" />
        </label>
      </section>

      <section className="content-grid" aria-label="Stops">
        <div className="panel stop-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Available locations</p>
              <h2>Stops</h2>
            </div>
            <span className="count-badge">{totalStops}</span>
          </div>

          {status === 'loading' && <p className="state-message">Loading stops…</p>}
          {status === 'error' && (
            <p className="state-message state-message--error">
              Could not load stops.
            </p>
          )}
          {status === 'ready' && stops.length === 0 && (
            <p className="state-message">No stops are available.</p>
          )}
          {status === 'ready' && stops.length > 0 && (
            <div className="stop-list">
              {stops.map((stop) => (
                <button
                  className={`stop-row ${stop.stop_id === selectedStopId ? 'stop-row--selected' : ''}`}
                  key={stop.stop_id}
                  type="button"
                  onClick={() => setSelectedStopId(stop.stop_id)}
                >
                  <span className="stop-row-name">{stopLabel(stop)}</span>
                  <span className="stop-row-id">{stop.stop_id}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <aside className="panel details-panel">
          <p className="eyebrow">Selected stop</p>
          {selectedStop ? (
            <>
              <h2>{stopLabel(selectedStop)}</h2>
              <dl className="details-list">
                <div>
                  <dt>Stop ID</dt>
                  <dd>{selectedStop.stop_id}</dd>
                </div>
                <div>
                  <dt>Coordinates</dt>
                  <dd>{coordinates}</dd>
                </div>
                {selectedStop.platform_code && (
                  <div>
                    <dt>Platform</dt>
                    <dd>{selectedStop.platform_code}</dd>
                  </div>
                )}
              </dl>
              <div className="details-placeholder">
                <span className="placeholder-icon" aria-hidden="true">→</span>
                <div>
                  <strong>Departures will appear here</strong>
                </div>
              </div>
            </>
          ) : (
            <p className="state-message">Select a stop to see its details.</p>
          )}
        </aside>
      </section>
    </main>
  )
}

export default App
