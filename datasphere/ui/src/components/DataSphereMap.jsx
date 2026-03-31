import { useState } from 'react'
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

// Regional labels appear once zoomed in enough to be useful
const REGIONAL_LABEL_ZOOM = 2.5

export default function DataSphereMap({ theme, datacenters, selected, onSelect }) {
  const [zoom, setZoom] = useState(1)

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: theme.mapBg,
      transition: 'background 0.8s ease',
    }}>
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 140, center: [15, 15] }}
        style={{ width: '100%', height: '100%' }}
      >
        <ZoomableGroup onMoveEnd={({ zoom }) => setZoom(zoom)}>
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

          {datacenters.map(dc => {
            const isSelected = selected?.id === dc.id
            const isMajor = dc.tier === 'major'
            const color = theme.statusColors[dc.status] ?? theme.statusColors.online
            const label = dc[theme.nameField] ?? dc.display_name
            const showLabel = isMajor || zoom >= REGIONAL_LABEL_ZOOM

            // Scale all SVG sizes inversely with zoom → consistent visual size at any zoom level
            const r = (isMajor ? theme.majorRadius : theme.regionalRadius) / zoom
            const fontSize = (isMajor ? 10 : 9) / zoom
            const labelY = -(r + 4 / zoom)
            const strokeWidth = (isSelected ? 2.5 : 1) / zoom
            const ringR = (isMajor ? theme.majorRadius + 6 : 0) / zoom

            return (
              <Marker key={dc.id} coordinates={[dc.lng, dc.lat]}>
                {/* Pulse ring for online major sites */}
                {isMajor && dc.status === 'online' && (
                  <circle
                    r={ringR}
                    fill="none"
                    stroke={color}
                    strokeWidth={1 / zoom}
                    opacity={0.35}
                  />
                )}

                {/* Main dot */}
                <circle
                  r={r}
                  fill={color}
                  stroke={isSelected ? theme.textPrimary : theme.mapBg}
                  strokeWidth={strokeWidth}
                  style={{ cursor: 'pointer', transition: 'fill 0.3s ease' }}
                  onClick={() => onSelect(dc)}
                />

                {/* Label — always for major, zoom-gated for regional */}
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
