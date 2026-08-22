import { useCallback, useEffect, useMemo, useState } from 'react'
import { Alert, Card, DatePicker, Pagination, Radio, Space, Spin, Tag, Typography } from 'antd'
import L from 'leaflet'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'

import { ANALYTICS_DEFAULTS } from '@/api/analytics'
import { fetchLtePlaces, fetchWifiPlaces, type WardrivingPlace } from '@/api/wardriveMap'
import { useAuth } from '@/context/AuthContext'
import { useThemeMode } from '@/context/ThemeModeContext'
import { dateInputToDayRangeIso, isoToDateInputValue } from '@/utils/datetimeLocal'

import 'leaflet/dist/leaflet.css'

const VIEW_SIZE = 500

const DEFAULT_CENTER: [number, number] = [40.4168, -3.7038]
const DEFAULT_ZOOM = 6

function signalColor(signal: string): string {
  switch (signal) {
    case 'Excellent':
      return '#15803d'
    case 'Good':
      return '#16a34a'
    case 'Fair':
      return '#c2410c'
    case 'Weak':
      return '#b91c1c'
    default:
      return '#B026FF'
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
  const { isDarkMode } = useThemeMode()
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
    (value: string | number) => {
      if (value !== 'wifi' && value !== 'lte') return
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
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (next.get('first_seen_after') === normalized.startIso && next.get('first_seen_before') === normalized.endIso) {
          return prev
        }
        next.set('first_seen_after', normalized.startIso)
        next.set('first_seen_before', normalized.endIso)
        return next
      },
      { replace: true },
    )
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
      const params = {
        page,
        page_size: VIEW_SIZE,
        first_seen_after,
        first_seen_before,
        ...(user?.username ? { uploaded_by: user.username } : {}),
      }
      try {
        const fetchPlacesForMode = mode === 'wifi' ? fetchWifiPlaces : fetchLtePlaces
        const result = await fetchPlacesForMode(params)
        if (cancelled) return
        setData(result.results)
        setTotal(result.count)
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

  useEffect(() => {
    if (total <= 0) return
    const maxPage = Math.ceil(total / VIEW_SIZE)
    if (maxPage >= 1 && page > maxPage) setPage(maxPage)
  }, [total, page, setPage])

  return (
    <div className="map-shell">
      <Card
        size="small"
        title="Wardriving map"
        extra={
          <Space>
            <Tag color="processing">REST</Tag>
            <Tag>{mode.toUpperCase()}</Tag>
          </Space>
        }
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
          Hasta {VIEW_SIZE} pines por página. Filtros en la URL (<code>first_seen_after</code>,{' '}
          <code>first_seen_before</code>).
          {user?.username ? (
            <>
              {' '}
              Puntos de <code>{user.username}</code>.
            </>
          ) : null}
        </Typography.Paragraph>

        <Space wrap style={{ marginBottom: 12 }} size="middle">
          <DatePicker.RangePicker
            disabled={loading}
            allowClear={false}
            value={[
              dayjs(isoToDateInputValue(first_seen_after)),
              dayjs(isoToDateInputValue(first_seen_before)),
            ]}
            minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
            maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
            onChange={(dates) => {
              if (!dates?.[0] || !dates?.[1]) return
              setDateRange(dates[0].format('YYYY-MM-DD'), dates[1].format('YYYY-MM-DD'))
            }}
          />
          <Radio.Group
            optionType="button"
            buttonStyle="solid"
            disabled={loading}
            value={mode}
            onChange={(e) => handleModeChange(e.target.value)}
            options={[
              { label: 'WiFi', value: 'wifi' },
              { label: 'LTE', value: 'lte' },
            ]}
          />
        </Space>

        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <Typography.Text type="secondary">
            {loading ? 'Cargando…' : `${total.toLocaleString()} registros · ${data.length} en pantalla`}
          </Typography.Text>
          <Pagination
            size="small"
            current={page}
            total={total}
            pageSize={VIEW_SIZE}
            onChange={setPage}
            showSizeChanger={false}
            disabled={loading || total === 0}
            showQuickJumper
            showTotal={(t, range) => `${range[0]}-${range[1]} de ${t}`}
          />
        </div>
      </Card>

      {error && <Alert type="error" closable onClose={() => setError(null)} message={error} />}

      <div className="map-frame">
        {loading && (
          <div
            className={isDarkMode ? 'map-overlay map-overlay-dark' : 'map-overlay'}
            role="progressbar"
            aria-busy="true"
            aria-live="polite"
            aria-label="Cargando datos del mapa"
          >
            <Spin size="large" />
            <Typography.Text>Cargando datos del mapa…</Typography.Text>
            <Typography.Text type="secondary">Espera un momento; el mapa no está disponible hasta que termine la carga.</Typography.Text>
          </div>
        )}
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom={!loading}
          style={{ height: '100%', width: '100%', minHeight: 420 }}
        >
          <TileLayer
            key={isDarkMode ? 'carto-dark' : 'osm'}
            attribution={
              isDarkMode
                ? '&copy; OSM &copy; CARTO'
                : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }
            url={
              isDarkMode
                ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
                : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
            }
            referrerPolicy="strict-origin-when-cross-origin"
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
                <div style={{ minWidth: 200 }}>
                  <Typography.Text strong>{p.vendor || '—'}</Typography.Text>
                  <div>
                    <strong>MAC / ID:</strong> {p.mac}
                  </div>
                  <div>
                    <strong>SSID:</strong> {p.ssid || '—'}
                  </div>
                  <div>
                    <strong>Signal:</strong> {p.signal_streng}
                  </div>
                  <div>
                    <strong>Type:</strong> {p.type} · <strong>Auth:</strong> {p.auth_mode || '—'}
                  </div>
                  <Typography.Text type="secondary">
                    {p.device_source} · {p.uploaded_by || '—'}
                  </Typography.Text>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      <Space wrap>
        <Typography.Text type="secondary">Legend:</Typography.Text>
        {['Excellent', 'Good', 'Fair', 'Weak'].map((s) => (
          <Tag
            key={s}
            bordered={false}
            style={{
              marginInlineEnd: 0,
              backgroundColor: signalColor(s),
              color: '#fff',
              fontWeight: 600,
            }}
          >
            {s}
          </Tag>
        ))}
      </Space>
    </div>
  )
}
