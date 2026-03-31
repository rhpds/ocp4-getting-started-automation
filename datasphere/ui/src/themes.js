export const THEMES = {
  earth: {
    id: 'earth',
    // Colors
    bg: '#0d1b2e',
    mapBg: '#0a1628',
    countryFill: '#162a4a',
    countryStroke: '#1e4080',
    headerBg: '#0a1628',
    headerBorder: '#1e4080',
    panelBg: '#111f38',
    panelBorder: '#1e4080',
    accent: '#4a9eff',
    textPrimary: '#e2eaf5',
    textSecondary: '#7fa8cc',
    statusColors: {
      online: '#22c55e',
      degraded: '#f59e0b',
      offline: '#ef4444',
    },
    // Copy
    mapTitle: 'DataSphere',
    mapSubtitle: 'Global Infrastructure Operations',
    dcLabel: 'Datacenter',
    regionLabel: 'Region',
    statusLabels: {
      online: 'Online',
      degraded: 'Degraded',
      offline: 'Offline',
    },
    nameField: 'display_name',
    regionField: 'region',
    // Dot sizes
    majorRadius: 9,
    regionalRadius: 5,
  },
  mars: {
    id: 'mars',
    // Colors
    bg: '#1a0800',
    mapBg: '#130500',
    countryFill: '#3d1205',
    countryStroke: '#6b2208',
    headerBg: '#130500',
    headerBorder: '#8b3a0f',
    panelBg: '#220c02',
    panelBorder: '#8b3a0f',
    accent: '#f97316',
    textPrimary: '#f5e0d0',
    textSecondary: '#c97a50',
    statusColors: {
      online: '#f97316',
      degraded: '#fbbf24',
      offline: '#7f1d1d',
    },
    // Copy
    mapTitle: 'DataSphere',
    mapSubtitle: 'Mars Operations Command',
    dcLabel: 'Research Colony',
    regionLabel: 'Zone',
    statusLabels: {
      online: 'Operational',
      degraded: 'Limited',
      offline: 'Dark',
    },
    nameField: 'mars_name',
    regionField: 'mars_region',
    // Dot sizes
    majorRadius: 9,
    regionalRadius: 5,
  },
}

export function getTheme(themeId) {
  return THEMES[themeId] ?? THEMES.earth
}
