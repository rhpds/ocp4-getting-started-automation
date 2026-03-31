export default function StatusBar({ theme, online, degraded, offline, lastUpdated, apiError }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
      <div style={{ display: 'flex', gap: 16 }}>
        <Stat label="Online" value={online} color={theme.statusColors.online} theme={theme} />
        <Stat label={theme.statusLabels?.degraded ?? 'Degraded'} value={degraded} color={theme.statusColors.degraded} theme={theme} />
        <Stat label={theme.statusLabels?.offline ?? 'Offline'} value={offline} color={theme.statusColors.offline} theme={theme} />
      </div>

      <div style={{
        fontSize: 10,
        color: apiError ? theme.statusColors.offline : theme.textSecondary,
        fontFamily: 'Red Hat Mono, monospace',
        letterSpacing: '0.05em',
      }}>
        {apiError
          ? 'API unreachable'
          : lastUpdated
            ? `Updated ${lastUpdated.toLocaleTimeString()}`
            : 'Connecting...'}
      </div>
    </div>
  )
}

function Stat({ label, value, color, theme }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontSize: 20,
        fontWeight: 700,
        color,
        fontFamily: 'Red Hat Mono, monospace',
        lineHeight: 1,
      }}>
        {value}
      </div>
      <div style={{ fontSize: 9, color: theme.textSecondary, textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 2 }}>
        {label}
      </div>
    </div>
  )
}
