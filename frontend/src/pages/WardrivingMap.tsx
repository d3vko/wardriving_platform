import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import Pagination from '@mui/material/Pagination'
import L from 'leaflet'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { useSearchParams } from 'react-router-dom'

import {
  fetchLtePlaces,
  fetchWifiPlaces,
  type WardrivingPlace,
} from '@/api/wardriveMap'

import 'leaflet/dist/leaflet.css'

/** Coincide con MapPlacesPagination en la API (hasta 2000 por petición). */
const PAGE_SIZE = 1000

const DEFAULT_CENTER: [number, number] = [40.4168, -3.7038]
const DEFAULT_ZOOM = 6

function signalColor(signal: string): string {
  switch (signal) {
    case 'Excellent':
      return '#2e7d32'
    case 'Good':
      return '#66bb6a'
    case 'Fair':
      return '#ed6c02'
    case 'Weak':
      return '#c62828'
    default:
      return '#1976d2'
  }
}

function FitBounds({ places }: { places: WardrivingPlace[] }) {
  const map = useMap()
  const coords = useMemo(
    () =>
      places
        .filter(
          (p) =>
            p.current_latitude != null &&
            p.current_longitude != null &&
            !(p.current_latitude === 0 && p.current_longitude === 0),
        )
        .map((p) => [p.current_latitude, p.current_longitude] as [number, number]),
    [places],
  )

  useEffect(() => {
    if (coords.length === 0) {
      map.setView(DEFAULT_CENTER, DEFAULT_ZOOM)
      return
    }
    const b = L.latLngBounds(coords)
    map.fitBounds(b, { padding: [48, 48], maxZoom: 16 })
  }, [coords, map])

  return null
}

function parsePageParam(raw: string | null): number {
  const n = parseInt(raw ?? '1', 10)
  if (Number.isNaN(n) || n < 1) return 1
  return n
}

export default function WardrivingMap() {
  const [searchParams, setSearchParams] = useSearchParams()
  const modeParam = searchParams.get('mode')
  const mode: 'wifi' | 'lte' = modeParam === 'lte' ? 'lte' : 'wifi'
  const page = parsePageParam(searchParams.get('page')) // ?page=2 en la URL

  const setPage = useCallback(
    (p: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        if (p <= 1) next.delete('page')
        else next.set('page', String(p))
        return next
      })
    },
    [setSearchParams],
  )

  const handleModeChange = useCallback(
    (_: unknown, value: 'wifi' | 'lte' | null) => {
      if (!value) return
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('mode', value)
        next.delete('page')
        return next
      })
    },
    [setSearchParams],
  )

  const [data, setData] = useState<WardrivingPlace[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res =
          mode === 'wifi'
            ? await fetchWifiPlaces({ page, page_size: PAGE_SIZE })
            : await fetchLtePlaces({ page, page_size: PAGE_SIZE })
        if (!cancelled) {
          setData(res.results)
          setTotal(res.count)
        }
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'Error al cargar datos'
          setError(msg)
          setData([])
          setTotal(0)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [mode, page])

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE) || 1)

  useEffect(() => {
    if (total <= 0) return
    const maxPage = Math.ceil(total / PAGE_SIZE)
    if (maxPage >= 1 && page > maxPage) setPage(maxPage)
  }, [total, page, setPage])

  return (
    <Stack spacing={2} sx={{ height: '100%', minHeight: 480 }}>
      <Box>
        <Typography variant="h5" fontWeight={700} gutterBottom>
          Mapa wardriving
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Cada página muestra hasta {PAGE_SIZE} pines. Usa la barra encima del mapa (o la URL con{' '}
          <code>?page=2</code>). Leyenda por intensidad de señal.
        </Typography>
      </Box>

      <Stack direction="row" alignItems="center" spacing={2} flexWrap="wrap">
        <ToggleButtonGroup
          value={mode}
          exclusive
          onChange={handleModeChange}
          size="small"
          aria-label="Modo de mapa"
        >
          <ToggleButton value="wifi">WiFi</ToggleButton>
          <ToggleButton value="lte">LTE</ToggleButton>
        </ToggleButtonGroup>
        {loading && <CircularProgress size={22} />}
        {!loading && (
          <Chip
            size="small"
            label={`${total} registros · página ${page} / ${pageCount}`}
            variant="outlined"
          />
        )}
      </Stack>

      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
          py: 1,
          px: 1.5,
          borderRadius: 2,
          bgcolor: 'action.hover',
        }}
      >
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: { xs: 'center', sm: 'left' } }}>
          Pines en el mapa: página <strong>{page}</strong> de <strong>{pageCount}</strong>
          {total > 0 ? ` (${data.length} en pantalla)` : ''}
        </Typography>
        <Pagination
          count={pageCount}
          page={page}
          onChange={(_, p) => setPage(p)}
          color="primary"
          size="small"
          showFirstButton
          showLastButton
          disabled={loading || total === 0}
          siblingCount={1}
          boundaryCount={1}
        />
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper
        variant="outlined"
        sx={{
          flex: 1,
          minHeight: 420,
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 2,
        }}
      >
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom
          style={{ height: '100%', width: '100%', minHeight: 420 }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds places={data} />
          {data.map((p, i) => (
            <CircleMarker
              key={`${p.mac}-${i}-${page}`}
              center={[p.current_latitude, p.current_longitude]}
              radius={8}
              pathOptions={{
                color: signalColor(p.signal_streng),
                fillColor: signalColor(p.signal_streng),
                fillOpacity: 0.65,
                weight: 1,
              }}
            >
              <Popup>
                <Stack spacing={0.5} sx={{ minWidth: 200 }}>
                  <Typography variant="subtitle2" fontWeight={700}>
                    {p.vendor || '—'}
                  </Typography>
                  <Typography variant="caption" component="div">
                    <strong>MAC / ID:</strong> {p.mac}
                  </Typography>
                  <Typography variant="caption" component="div">
                    <strong>SSID:</strong> {p.ssid || '—'}
                  </Typography>
                  <Typography variant="caption" component="div">
                    <strong>Señal:</strong> {p.signal_streng}
                  </Typography>
                  <Typography variant="caption" component="div">
                    <strong>Tipo:</strong> {p.type} · <strong>Auth:</strong> {p.auth_mode || '—'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {p.device_source} · {p.uploaded_by || '—'}
                  </Typography>
                </Stack>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </Paper>

      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="caption" color="text.secondary">
          Leyenda:
        </Typography>
        {['Excellent', 'Good', 'Fair', 'Weak'].map((s) => (
          <Chip
            key={s}
            size="small"
            label={s}
            sx={{
              bgcolor: signalColor(s),
              color: s === 'Fair' ? '#000' : '#fff',
              fontWeight: 600,
            }}
          />
        ))}
      </Stack>
    </Stack>
  )
}
