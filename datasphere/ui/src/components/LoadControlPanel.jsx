import { useState, useEffect, useRef } from 'react'

export default function LoadControlPanel({ theme, loadStats }) {
  const [sliderValue, setSliderValue] = useState(0)
  const debounceRef = useRef(null)
  const hasInteracted = useRef(false)

  // Sync slider from server on initial load only — once the user has touched
  // the slider, they own it. Without this guard the poll (every 3s) races
  // against the debounced POST and snaps the slider back to the old value.
  useEffect(() => {
    if (!hasInteracted.current && loadStats && loadStats.simulated_load > 0) {
      setSliderValue(loadStats.simulated_load)
    }
  }, [loadStats])

  const handleChange = (e) => {
    const val = Number(e.target.value)
    hasInteracted.current = true
    setSliderValue(val)

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        await fetch('/api/load', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ level: val }),
        })
      } catch {
        // API error handled by parent poll
      }
    }, 300)
  }

  const perPod = loadStats?.per_pod_load ?? 0
  const perPodColor = perPod > 80
    ? theme.statusColors.offline
    : perPod > 50
      ? theme.statusColors.degraded
      : theme.textSecondary

  return (
    <div style={{
      position: 'absolute',
      bottom: 20,
      left: 180,
      background: theme.panelBg,
      border: `1px solid ${theme.panelBorder}`,
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 11,
      color: theme.textSecondary,
      minWidth: 170,
    }}>
      <div style={{
        fontSize: 10,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        marginBottom: 8,
        color: theme.textPrimary,
        fontWeight: 600,
      }}>
        Simulated Traffic
      </div>

      <input
        type="range"
        min={0}
        max={100}
        value={sliderValue}
        onChange={handleChange}
        style={{
          width: '100%',
          accentColor: theme.accent,
          cursor: 'pointer',
          marginBottom: 8,
        }}
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span>Traffic:</span>
        <span style={{ fontFamily: 'Red Hat Mono, monospace' }}>{loadStats?.simulated_load ?? 0}%</span>
      </div>

      {(loadStats?.offline_penalty ?? 0) > 0 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span>DC Penalty:</span>
          <span style={{ fontFamily: 'Red Hat Mono, monospace' }}>+{loadStats.offline_penalty}%</span>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span>Total Load:</span>
        <span style={{ fontFamily: 'Red Hat Mono, monospace' }}>{loadStats?.total_load ?? 0}%</span>
      </div>

      <div style={{
        marginTop: 6,
        paddingTop: 6,
        borderTop: `1px solid ${theme.panelBorder}`,
        display: 'flex',
        justifyContent: 'space-between',
        marginBottom: 4,
      }}>
        <span>Pods:</span>
        <span style={{ fontFamily: 'Red Hat Mono, monospace' }}>{loadStats?.replica_count ?? 1}</span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>Per-Pod:</span>
        <span style={{ fontFamily: 'Red Hat Mono, monospace', color: perPodColor }}>
          {perPod}%
        </span>
      </div>
    </div>
  )
}
