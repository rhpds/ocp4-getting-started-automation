import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { getTheme } from './themes'
import DataSphereMap from './components/DataSphereMap'
import DatacenterPanel from './components/DatacenterPanel'
import StatusBar from './components/StatusBar'
import LoadControlPanel from './components/LoadControlPanel'

const POLL_INTERVAL_MS = 3000
const CONFIG_POLL_INTERVAL_MS = 10000

export default function App() {
  const [theme, setTheme] = useState(getTheme('earth'))
  const [datacenters, setDatacenters] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [apiError, setApiError] = useState(false)
  const [loadStats, setLoadStats] = useState(null)

  // Derive selected object from live datacenters — no stale closure possible
  const selected = datacenters.find(d => d.id === selectedId) ?? null

  const fetchConfig = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/config')
      setTheme(getTheme(data.theme))
    } catch {
      // Keep current theme on error
    }
  }, [])

  // No dependency on selectedId — interval stays stable, close button works
  const fetchDatacenters = useCallback(async () => {
    try {
      const [dcRes, loadRes] = await Promise.all([
        axios.get('/api/datacenters'),
        axios.get('/api/load'),
      ])
      setDatacenters(dcRes.data)
      setLoadStats(loadRes.data)
      setLastUpdated(new Date())
      setApiError(false)
    } catch {
      setApiError(true)
    }
  }, [])

  const handleToggleStatus = useCallback(async (dc) => {
    const newStatus = dc.status === 'online' ? 'offline' : 'online'
    try {
      const { data } = await axios.patch(`/api/datacenters/${dc.id}/status`, { status: newStatus })
      // Update datacenters in place — selected re-derives automatically
      setDatacenters(prev => prev.map(d => d.id === data.id ? data : d))
    } catch (err) {
      console.error('Failed to update status', err)
    }
  }, [])

  useEffect(() => {
    fetchConfig()
    fetchDatacenters()
    const dcTimer = setInterval(fetchDatacenters, POLL_INTERVAL_MS)
    const cfgTimer = setInterval(fetchConfig, CONFIG_POLL_INTERVAL_MS)
    return () => {
      clearInterval(dcTimer)
      clearInterval(cfgTimer)
    }
  }, [fetchConfig, fetchDatacenters])

  const online = datacenters.filter(d => d.status === 'online').length
  const degraded = datacenters.filter(d => d.status === 'degraded').length
  const offline = datacenters.filter(d => d.status === 'offline').length

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: theme.bg,
      color: theme.textPrimary,
      transition: 'background 0.8s ease, color 0.8s ease',
    }}>
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 24px',
        background: theme.headerBg,
        borderBottom: `1px solid ${theme.headerBorder}`,
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <img src="/redhat-logo.svg" alt="Red Hat" style={{ height: 28, opacity: 0.9 }} />
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: theme.textPrimary, letterSpacing: '0.02em' }}>
              {theme.mapTitle}
            </div>
            <div style={{ fontSize: 11, color: theme.textSecondary, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              {theme.mapSubtitle}
            </div>
          </div>
        </div>

        <StatusBar
          theme={theme}
          online={online}
          degraded={degraded}
          offline={offline}
          lastUpdated={lastUpdated}
          apiError={apiError}
        />
      </header>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <DataSphereMap
            theme={theme}
            datacenters={datacenters}
            selected={selected}
            onSelect={dc => setSelectedId(dc.id)}
          />
          <LoadControlPanel theme={theme} loadStats={loadStats} />
        </div>

        {selected && (
          <DatacenterPanel
            theme={theme}
            datacenter={selected}
            onClose={() => setSelectedId(null)}
            onToggleStatus={handleToggleStatus}
          />
        )}
      </div>
    </div>
  )
}
