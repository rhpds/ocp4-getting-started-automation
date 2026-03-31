export default function DatacenterPanel({ theme, datacenter: dc, onClose, onToggleStatus }) {
  const name = dc[theme.nameField] ?? dc.display_name
  const region = dc[theme.regionField] ?? dc.region
  const statusColor = theme.statusColors[dc.status]
  const statusLabel = theme.statusLabels[dc.status]
  const isOnline = dc.status === 'online'

  return (
    <div style={{
      width: 300,
      background: theme.panelBg,
      borderLeft: `1px solid ${theme.panelBorder}`,
      display: 'flex',
      flexDirection: 'column',
      transition: 'background 0.8s ease',
      flexShrink: 0,
      overflowY: 'auto',
    }}>
      {/* Panel header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        padding: '16px 18px 12px',
        borderBottom: `1px solid ${theme.panelBorder}`,
      }}>
        <div>
          <div style={{
            fontSize: 10,
            color: theme.textSecondary,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: 4,
          }}>
            {dc.tier === 'major' ? `Major ${theme.dcLabel}` : `Regional ${theme.dcLabel}`}
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: theme.textPrimary, lineHeight: 1.3 }}>
            {name}
          </div>
          <div style={{ fontSize: 12, color: theme.textSecondary, marginTop: 3 }}>
            {region}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: theme.textSecondary,
            cursor: 'pointer',
            fontSize: 18,
            lineHeight: 1,
            padding: 2,
          }}
          aria-label="Close panel"
        >
          ×
        </button>
      </div>

      {/* Status badge */}
      <div style={{ padding: '14px 18px', borderBottom: `1px solid ${theme.panelBorder}` }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 7,
          padding: '5px 12px',
          borderRadius: 20,
          background: `${statusColor}22`,
          border: `1px solid ${statusColor}66`,
        }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: statusColor }}>{statusLabel}</span>
        </div>
      </div>

      {/* Metrics */}
      <div style={{ padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Metric label="Capacity Utilization" theme={theme}>
          <CapacityBar value={dc.capacity_pct} color={statusColor} theme={theme} />
        </Metric>

        <Metric label="Active Workloads" theme={theme}>
          <div style={{ fontSize: 22, fontWeight: 700, color: theme.textPrimary, fontFamily: 'Red Hat Mono, monospace' }}>
            {dc.workload_count.toLocaleString()}
          </div>
        </Metric>

        <Metric label="Uptime (30d)" theme={theme}>
          <div style={{ fontSize: 22, fontWeight: 700, color: theme.statusColors.online, fontFamily: 'Red Hat Mono, monospace' }}>
            {dc.uptime_pct}%
          </div>
        </Metric>
      </div>

      {/* Actions */}
      <div style={{
        padding: '14px 18px',
        borderTop: `1px solid ${theme.panelBorder}`,
        marginTop: 'auto',
      }}>
        <button
          onClick={() => onToggleStatus(dc)}
          style={{
            width: '100%',
            padding: '10px 0',
            borderRadius: 6,
            border: `1px solid ${isOnline ? theme.statusColors.offline : theme.statusColors.online}`,
            background: isOnline
              ? `${theme.statusColors.offline}22`
              : `${theme.statusColors.online}22`,
            color: isOnline ? theme.statusColors.offline : theme.statusColors.online,
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'Red Hat Display, sans-serif',
            transition: 'all 0.2s ease',
          }}
        >
          {isOnline ? `Take ${theme.dcLabel} Offline` : `Bring ${theme.dcLabel} Online`}
        </button>
      </div>
    </div>
  )
}

function Metric({ label, theme, children }) {
  return (
    <div>
      <div style={{
        fontSize: 10,
        color: theme.textSecondary,
        textTransform: 'uppercase',
        letterSpacing: '0.1em',
        marginBottom: 6,
      }}>
        {label}
      </div>
      {children}
    </div>
  )
}

function CapacityBar({ value, color, theme }) {
  return (
    <div>
      <div style={{
        fontSize: 22,
        fontWeight: 700,
        color: theme.textPrimary,
        fontFamily: 'Red Hat Mono, monospace',
        marginBottom: 8,
      }}>
        {value}%
      </div>
      <div style={{
        height: 6,
        background: `${color}22`,
        borderRadius: 3,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${value}%`,
          background: color,
          borderRadius: 3,
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  )
}
