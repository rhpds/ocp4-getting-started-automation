import { useState, useMemo } from 'react'
import { ComposableMap, Geographies, Geography, Marker, Line, ZoomableGroup } from 'react-simple-maps'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'
const REGIONAL_LABEL_ZOOM = 2.5

export default function DataSphereMap({ theme, datacenters, selected, onSelect }) {
  const [zoom, setZoom] = useState(1)

  // Major-to-major backbone (full mesh) + each regional → nearest major hub
  const arcs = useMemo(() => {
    const majors = datacenters.filter(dc => dc.tier === 'major' && dc.status !== 'offline')
    const regionals = datacenters.filter(dc => dc.tier === 'regional' && dc.status !== 'offline')
    const result = []

    for (let i = 0; i < majors.length; i++) {
      for (let j = i + 1; j < majors.length; j++) {
        result.push({ from: majors[i], to: majors[j], isMajor: true })
      }
    }

    for (const r of regionals) {
      if (!majors.length) continue
      let nearest = majors[0], minDist = Infinity
      for (const m of majors) {
        const d = Math.hypot(r.lat - m.lat, r.lng - m.lng)
        if (d < minDist) { minDist = d; nearest = m }
      }
      result.push({ from: r, to: nearest, isMajor: false })
    }

    return result
  }, [datacenters])

  return (
    <div style={{ width: '100%', height: '100%', background: theme.mapBg, position: 'relative', transition: 'background 0.8s ease' }}>

      {/* Keyframes for the flowing arc dash animation */}
      <style>{`
        @keyframes arc-flow { from { stroke-dashoffset: 24; } to { stroke-dashoffset: 0; } }
        @keyframes arc-flow-dim { from { stroke-dashoffset: 12; } to { stroke-dashoffset: 0; } }
      `}</style>

      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 140, center: [15, 15] }}
        style={{ width: '100%', height: '100%' }}
      >
        <ZoomableGroup onMoveEnd={({ zoom }) => setZoom(zoom)}>

          {/* Countries */}
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill={theme.countryFill}
                  stroke={theme.countryStroke}
                  strokeWidth={0.5 / zoom}
                  style={{
                    default: { outline: 'none' },
                    hover: { outline: 'none', fill: theme.countryStroke },
                    pressed: { outline: 'none' },
                  }}
                />
              ))
            }
          </Geographies>

          {/* Traffic arcs — rendered before markers so dots appear on top */}
          {arcs.map((arc, i) => (
            <Line
              key={i}
              from={[arc.from.lng, arc.from.lat]}
              to={[arc.to.lng, arc.to.lat]}
              stroke={arc.isMajor ? theme.arcColor : theme.arcColorDim}
              strokeWidth={arc.isMajor ? 1.2 / zoom : 0.9 / zoom}
              strokeLinecap="round"
              style={{
                strokeDasharray: arc.isMajor ? '8 4' : '3 9',
                animation: arc.isMajor
                  ? 'arc-flow 1.8s linear infinite'
                  : 'arc-flow-dim 3.5s linear infinite',
              }}
            />
          ))}

          {/* Datacenter markers */}
          {datacenters.map(dc => {
            const isSelected = selected?.id === dc.id
            const isMajor = dc.tier === 'major'
            const color = theme.statusColors[dc.status] ?? theme.statusColors.online
            const label = dc[theme.nameField] ?? dc.display_name
            const showLabel = isMajor || zoom >= REGIONAL_LABEL_ZOOM

            const r = (isMajor ? theme.majorRadius : theme.regionalRadius) / zoom
            const fontSize = (isMajor ? 10 : 9) / zoom
            const labelY = -(r + 4 / zoom)
            const strokeWidth = (isSelected ? 2.5 : 1) / zoom
            const ringR = (isMajor ? theme.majorRadius + 6 : 0) / zoom

            return (
              <Marker key={dc.id} coordinates={[dc.lng, dc.lat]}>
                {isMajor && dc.status === 'online' && (
                  <circle r={ringR} fill="none" stroke={color} strokeWidth={1 / zoom} opacity={0.35} />
                )}
                <circle
                  r={r}
                  fill={color}
                  stroke={isSelected ? theme.textPrimary : theme.mapBg}
                  strokeWidth={strokeWidth}
                  style={{ cursor: 'pointer', transition: 'fill 0.3s ease' }}
                  onClick={() => onSelect(dc)}
                />
                {showLabel && (
                  <text
                    textAnchor="middle"
                    y={labelY}
                    style={{
                      fontFamily: 'Red Hat Display, sans-serif',
                      fontSize,
                      fill: theme.textSecondary,
                      pointerEvents: 'none',
                      userSelect: 'none',
                    }}
                  >
                    {label}
                  </text>
                )}
              </Marker>
            )
          })}

        </ZoomableGroup>
      </ComposableMap>

      {/* Legend */}
      <div style={{
        position: 'absolute',
        bottom: 20,
        left: 20,
        background: theme.panelBg,
        border: `1px solid ${theme.panelBorder}`,
        borderRadius: 8,
        padding: '10px 14px',
        fontSize: 11,
        color: theme.textSecondary,
      }}>
        {Object.entries(theme.statusColors).map(([status, color]) => (
          <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 4 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
            <span>{theme.statusLabels[status]}</span>
          </div>
        ))}
        <div style={{ marginTop: 6, paddingTop: 6, borderTop: `1px solid ${theme.panelBorder}`, fontSize: 10 }}>
          Click a site to inspect
        </div>
      </div>
    </div>
  )
}
