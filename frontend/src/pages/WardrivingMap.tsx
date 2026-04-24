import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Stack,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import Pagination from '@mui/material/Pagination'
import L from 'leaflet'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { useSearchParams } from 'react-router-dom'

import { ANALYTICS_DEFAULTS } from '@/api/analytics'
import {
  fetchLtePlaces,
  fetchWifiPlaces,
  type WardrivingPlace,
} from '@/api/wardriveMap'
import { useAuth } from '@/context/AuthContext'
import { dateInputToDayRangeIso, isoToDateInputValue } from '@/utils/datetimeLocal'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import dayjs, { type Dayjs } from 'dayjs'

import 'leaflet/dist/leaflet.css'

/** Puntos visibles por “página” del mapa máx 1000 pines. */
const VIEW_SIZE = 1000
const BATCH_SIZE = 250
const BATCHES_PER_VIEW = VIEW_SIZE / BATCH_SIZE

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
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const modeParam = searchParams.get('mode')
  const mode: 'wifi' | 'lte' = modeParam === 'lte' ? 'lte' : 'wifi'
  const page = parsePageParam(searchParams.get('page'))

  const first_seen_after = searchParams.get('first_seen_after') ?? ANALYTICS_DEFAULTS.startDate
  const first_seen_before = searchParams.get('first_seen_before') ?? ANALYTICS_DEFAULTS.endDate

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

  const setDateRange = useCallback(
    (nextFromDate: string, nextToDate: string) => {
      const range = dateInputToDayRangeIso(nextFromDate, nextToDate, {
        minIso: ANALYTICS_DEFAULTS.minDate,
        maxIso: ANALYTICS_DEFAULTS.maxDate,
      })
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('first_seen_after', range.startIso)
        next.set('first_seen_before', range.endIso)
        next.delete('page')
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

  useEffect(() => {
    const fromInput = isoToDateInputValue(first_seen_after) || isoToDateInputValue(ANALYTICS_DEFAULTS.startDate)
    const toInput = isoToDateInputValue(first_seen_before) || isoToDateInputValue(ANALYTICS_DEFAULTS.endDate)
    const normalized = dateInputToDayRangeIso(fromInput, toInput, {
      minIso: ANALYTICS_DEFAULTS.minDate,
      maxIso: ANALYTICS_DEFAULTS.maxDate,
    })
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (next.get('first_seen_after') === normalized.startIso && next.get('first_seen_before') === normalized.endIso) {
        return prev
      }
      next.set('first_seen_after', normalized.startIso)
      next.set('first_seen_before', normalized.endIso)
      return next
    }, { replace: true })
  }, [first_seen_after, first_seen_before, setSearchParams])

  const [data, setData] = useState<WardrivingPlace[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      const baseSubPage = (page - 1) * BATCHES_PER_VIEW + 1
      const params = {
        first_seen_after,
        first_seen_before,
        ...(user?.username ? { uploaded_by: user.username } : {}),
      }
      try {
        /** Listas WiFi/LTE vía WebSocket (`wardriveMap.ts`). */
        const fetchPlacesForMode = mode === 'wifi' ? fetchWifiPlaces : fetchLtePlaces

        // First batch only — get total count, then request extra pages only if they exist.
        // (DRF returns 404 for page > last page; parallel requests to empty pages break the UI.)
        const first = await fetchPlacesForMode({
          page: baseSubPage,
          page_size: BATCH_SIZE,
          ...params,
        })
        if (cancelled) return

        const totalCount = first.count
        const startOffset = (baseSubPage - 1) * BATCH_SIZE
        const itemsAvailable = Math.max(0, totalCount - startOffset)
        const itemsToFetch = Math.min(VIEW_SIZE, itemsAvailable)
        const numBatches =
          itemsToFetch === 0
            ? 0
            : Math.min(
                BATCHES_PER_VIEW,
                Math.ceil(itemsToFetch / BATCH_SIZE),
              )

        if (numBatches <= 1) {
          setData(first.results)
          setTotal(totalCount)
          return
        }

        const rest = await Promise.all(
          Array.from({ length: numBatches - 1 }, (_, i) =>
            fetchPlacesForMode({
              page: baseSubPage + 1 + i,
              page_size: BATCH_SIZE,
              ...params,
            }),
          ),
        )
        if (cancelled) return
        const merged = [first, ...rest].flatMap((r) => r.results)
        setData(merged)
        setTotal(totalCount)
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'Failed to load data'
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
  }, [mode, page, first_seen_after, first_seen_before, user?.username])

  const pageCount = Math.max(1, Math.ceil(total / VIEW_SIZE) || 1)

  useEffect(() => {
    if (total <= 0) return
    const maxPage = Math.ceil(total / VIEW_SIZE)
    if (maxPage >= 1 && page > maxPage) setPage(maxPage)
  }, [total, page, setPage])

  return (
    <Stack spacing={2} sx={{ height: '100%', minHeight: 480 }}>
      <Box>
        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
          <Typography variant="h5" fontWeight={700}>
            Wardriving map
          </Typography>
          <Chip label="WiFi / LTE · WebSocket" size="small" variant="outlined" color="secondary" />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Map data (WiFi and LTE) loads over WebSocket to the same paths as the REST list API. Up to{' '}
          {VIEW_SIZE} pins per view in batches of {BATCH_SIZE}. Date filters in the URL (
          <code>first_seen_after</code>, <code>first_seen_before</code>). Legend by signal strength.
          {user?.username ? (
            <> Showing points matching your username filter (<code>uploaded_by</code>).</>
          ) : null}
        </Typography>
      </Box>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }} flexWrap="wrap">
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }} flexWrap="wrap">
            <DatePicker
              label="From"
              value={dayjs(isoToDateInputValue(first_seen_after))}
              minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
              maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
              disabled={loading}
              onChange={(value: Dayjs | null) => {
                if (!value || !value.isValid()) return
                setDateRange(value.format('YYYY-MM-DD'), isoToDateInputValue(first_seen_before))
              }}
              slotProps={{
                textField: { size: 'small', sx: { minWidth: 240 } },
              }}
            />
            <DatePicker
              label="To"
              value={dayjs(isoToDateInputValue(first_seen_before))}
              minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
              maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
              disabled={loading}
              onChange={(value: Dayjs | null) => {
                if (!value || !value.isValid()) return
                setDateRange(isoToDateInputValue(first_seen_after), value.format('YYYY-MM-DD'))
              }}
              slotProps={{
                textField: { size: 'small', sx: { minWidth: 240 } },
              }}
            />
          </Stack>
        </LocalizationProvider>
      </Stack>

      <Stack direction="row" alignItems="center" spacing={2} flexWrap="wrap">
        <ToggleButtonGroup
          value={mode}
          exclusive
          onChange={handleModeChange}
          size="small"
          disabled={loading}
          aria-label="Map mode"
        >
          <ToggleButton value="wifi">WiFi</ToggleButton>
          <ToggleButton value="lte">LTE</ToggleButton>
        </ToggleButtonGroup>
        {!loading && (
          <Chip
            size="small"
            label={`${total} records · view ${page} / ${pageCount}`}
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
          Pins on map: view <strong>{page}</strong> of <strong>{pageCount}</strong>
          {total > 0 ? ` (${data.length} on screen)` : ''}
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
        {loading && (
          <Box
            role="progressbar"
            aria-busy="true"
            aria-live="polite"
            aria-label="Cargando datos del mapa"
            sx={{
              position: 'absolute',
              inset: 0,
              zIndex: 1400,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 2,
              px: 3,
              bgcolor: 'rgba(255, 255, 255, 0.92)',
              backdropFilter: 'blur(6px)',
              borderRadius: 2,
            }}
          >
            <CircularProgress size={48} thickness={4} />
            <Typography variant="body1" color="text.secondary" textAlign="center" fontWeight={500}>
              Cargando datos del mapa…
            </Typography>
            <Typography variant="caption" color="text.disabled" textAlign="center" sx={{ maxWidth: 280 }}>
              Espera un momento; el mapa no está disponible hasta que termine la carga.
            </Typography>
          </Box>
        )}
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom={!loading}
          style={{ height: '100%', width: '100%', minHeight: 420 }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds places={data} />
          {data.map((p, i) => (
            <CircleMarker
              key={`${mode}-${p.mac}-${i}-${page}`}
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
                    <strong>Signal:</strong> {p.signal_streng}
                  </Typography>
                  <Typography variant="caption" component="div">
                    <strong>Type:</strong> {p.type} · <strong>Auth:</strong> {p.auth_mode || '—'}
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
          Legend:
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
