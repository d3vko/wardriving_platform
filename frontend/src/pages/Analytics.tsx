import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material'
import {
  BarChart as BarChartIcon,
  CalendarMonth as CalendarMonthIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { BarChart } from '@mui/x-charts'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import dayjs, { type Dayjs } from 'dayjs'
import { useAuth } from '@/context/AuthContext'
import {
  ANALYTICS_DEFAULTS,
  AnalyticsError,
  type AnalyticsRow,
  type AnalyticsScope,
  fetchAuthModes,
  fetchByAuthor,
  fetchByDevice,
  fetchBySignal,
  fetchByVendor,
  fetchDetail,
} from '@/api/analytics'
import { dateInputToDayRangeIso, isoToDateInputValue } from '@/utils/datetimeLocal'
import IconButton from '@mui/material/IconButton'

interface ChartData {
  label: string
  value: number
}

interface DetailRow extends AnalyticsRow {
  mac?: string | null
  registry?: string | null
  vendor?: string | null
  source?: string | null
  ssid?: string | null
  auth_mode?: string | null
  first_seen?: string | null
  channel?: number | null
  rssi?: number | null
  signal_streng?: string | null
  device_source?: string | null
  uploaded_by?: string | null
  type?: string | null
  current_latitude?: number | null
  current_longitude?: number | null
}

function toChartData(rows: AnalyticsRow[], labelCol: string, valueCol: string): ChartData[] {
  return rows.map((r) => ({
    label: String(r[labelCol] ?? '(vacío)'),
    value: Number(r[valueCol] ?? 0),
  }))
}

function BarChartCard({
  title,
  data,
  xLabel,
  yLabel,
  loading,
  error,
}: {
  title: string
  data: ChartData[]
  xLabel: string
  yLabel: string
  loading: boolean
  error: string | null
}) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardHeader
        title={title}
        titleTypographyProps={{ variant: 'subtitle1', fontWeight: 600 }}
        sx={{ pb: 0 }}
      />
      <CardContent sx={{ pt: 1 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress size={32} />
          </Box>
        ) : error ? (
          <Alert severity="error">{error}</Alert>
        ) : data.length === 0 ? (
          <Typography variant="body2" color="text.secondary" textAlign="center" py={3}>
            Sin datos
          </Typography>
        ) : (
          <BarChart
            xAxis={[{ scaleType: 'band', data: data.map((d) => d.label), label: xLabel }]}
            series={[{ data: data.map((d) => d.value), label: yLabel }]}
            height={280}
          />
        )}
      </CardContent>
    </Card>
  )
}

function DetailTable({
  rows,
  loading,
  error,
}: {
  rows: DetailRow[]
  loading: boolean
  error: string | null
}) {
  const cols = [
    { key: 'ssid', label: 'SSID' },
    { key: 'mac', label: 'MAC' },
    { key: 'auth_mode', label: 'Auth Mode' },
    { key: 'vendor', label: 'Fabricante' },
    { key: 'registry', label: 'Registro' },
    { key: 'source', label: 'Fuente' },
    { key: 'signal_streng', label: 'Señal' },
    { key: 'rssi', label: 'RSSI' },
    { key: 'channel', label: 'Canal' },
    { key: 'device_source', label: 'Dispositivo' },
    { key: 'uploaded_by', label: 'Usuario' },
    { key: 'first_seen', label: 'First Seen' },
    { key: 'type', label: 'Tipo' },
    { key: 'current_latitude', label: 'Latitud' },
    { key: 'current_longitude', label: 'Longitud' },
  ]

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={6}>
        <CircularProgress />
      </Box>
    )
  }
  if (error) return <Alert severity="error">{error}</Alert>
  if (rows.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" textAlign="center" py={4}>
        No records for the selected period.
      </Typography>
    )
  }

  return (
    <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            {cols.map((c) => (
              <TableCell key={c.key} sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                {c.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.slice(0, 250).map((row, i) => (
            <TableRow key={i} hover>
              {cols.map((c) => (
                <TableCell key={c.key} sx={{ whiteSpace: 'nowrap', fontSize: 12 }}>
                  {row[c.key] != null ? String(row[c.key]) : '—'}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

interface AnalyticsState {
  authModes: ChartData[]
  byDevice: ChartData[]
  bySignal: ChartData[]
  byVendor: ChartData[]
  byAuthor: ChartData[]
  detail: DetailRow[]
  loading: boolean
  errors: Record<string, string>
}

const INITIAL_STATE: AnalyticsState = {
  authModes: [],
  byDevice: [],
  bySignal: [],
  byVendor: [],
  byAuthor: [],
  detail: [],
  loading: false,
  errors: {},
}

export default function Analytics() {
  const { user } = useAuth()
  const [tab, setTab] = useState<0 | 1>(0)
  const [startDateInput, setStartDateInput] = useState(isoToDateInputValue(ANALYTICS_DEFAULTS.startDate))
  const [endDateInput, setEndDateInput] = useState(isoToDateInputValue(ANALYTICS_DEFAULTS.endDate))
  const [state, setState] = useState<AnalyticsState>(INITIAL_STATE)

  const scope: AnalyticsScope = tab === 0 ? 'self-analytics' : 'global-analytics'

  const load = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, errors: {} }))
    const range = dateInputToDayRangeIso(startDateInput, endDateInput, {
      minIso: ANALYTICS_DEFAULTS.minDate,
      maxIso: ANALYTICS_DEFAULTS.maxDate,
    })

    const params = {
      first_seen_start: range.startIso,
      first_seen_end: range.endIso,
      ...(tab === 0 && user?.username ? { author: user.username } : {}),
    }

    const results = await Promise.allSettled([
      fetchAuthModes(scope, params),
      fetchByDevice(scope, params),
      fetchBySignal(scope, params),
      fetchByVendor(scope, params),
      tab === 1
        ? fetchByAuthor({ first_seen_start: range.startIso, first_seen_end: range.endIso })
        : Promise.resolve(null),
      fetchDetail(scope, params),
    ])

    const errors: Record<string, string> = {}
    const getRows = (r: PromiseSettledResult<{ rows: AnalyticsRow[] } | null>, key: string) => {
      if (r.status === 'rejected') {
        errors[key] =
          r.reason instanceof AnalyticsError
            ? `Error ${r.reason.status}: ${r.reason.message}`
            : String(r.reason)
        return []
      }
      return r.value?.rows ?? []
    }

    setState({
      loading: false,
      errors,
      authModes: toChartData(getRows(results[0], 'authModes'), 'auth_mode', 'qty_auth'),
      byDevice: toChartData(getRows(results[1], 'byDevice'), 'device_source', 'qty_device'),
      bySignal: toChartData(getRows(results[2], 'bySignal'), 'signal_streng', 'qty_by_signal'),
      byVendor: toChartData(getRows(results[3], 'byVendor'), 'vendor', 'qty_by_vendor'),
      byAuthor: toChartData(getRows(results[4], 'byAuthor'), 'uploaded_by', 'qty_by_author'),
      detail: getRows(results[5], 'detail') as DetailRow[],
    })
  }, [scope, startDateInput, endDateInput, tab, user?.username])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1.5} mb={3}>
        <BarChartIcon color="primary" sx={{ fontSize: 32 }} />
        <Typography variant="h4" fontWeight={700}>
          Analytics
        </Typography>
        <Tooltip title="Reload data">
          <IconButton onClick={() => void load()} disabled={state.loading} size="small">
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Tabs */}
      <Tabs
        value={tab}
        onChange={(_, v: 0 | 1) => setTab(v)}
        sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab label={`My data${user?.username ? ` (${user.username})` : ''}`} />
        <Tab label="Global" />
      </Tabs>

      {/* Date filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" mb={2}>
            <CalendarMonthIcon fontSize="small" color="primary" />
            <Typography variant="subtitle2" color="text.secondary">
              Date range filter
            </Typography>
          </Stack>
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-end">
              <DatePicker
                label="From"
                value={dayjs(startDateInput)}
                minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
                maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
                onChange={(value: Dayjs | null) => {
                  if (!value || !value.isValid()) return
                  setStartDateInput(value.format('YYYY-MM-DD'))
                }}
                slotProps={{
                  textField: {
                    size: 'small',
                    sx: { minWidth: 220 },
                  },
                }}
              />
              <DatePicker
                label="To"
                value={dayjs(endDateInput)}
                minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
                maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
                onChange={(value: Dayjs | null) => {
                  if (!value || !value.isValid()) return
                  setEndDateInput(value.format('YYYY-MM-DD'))
                }}
                slotProps={{
                  textField: {
                    size: 'small',
                    sx: { minWidth: 220 },
                  },
                }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ pb: 1 }}>
                Local timezone day bounds (00:00 - 23:59)
              </Typography>
            </Stack>
          </LocalizationProvider>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-end">
            {tab === 0 && user?.username && (
              <Typography variant="body2" color="text.secondary">
                Filtered by user: <strong>{user.username}</strong>
              </Typography>
            )}
          </Stack>
        </CardContent>
      </Card>

      {/* Charts */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12}>
          <BarChartCard
            title="Authentication modes"
            data={state.authModes}
            xLabel="Mode"
            yLabel="Count"
            loading={state.loading}
            error={state.errors.authModes ?? null}
          />
        </Grid>
        <Grid item xs={12}>
          <BarChartCard
            title="Devices"
            data={state.byDevice}
            xLabel="Device"
            yLabel="Count"
            loading={state.loading}
            error={state.errors.byDevice ?? null}
          />
        </Grid>
        <Grid item xs={12}>
          <BarChartCard
            title="Signal strength"
            data={state.bySignal}
            xLabel="Signal"
            yLabel="Count"
            loading={state.loading}
            error={state.errors.bySignal ?? null}
          />
        </Grid>
        {tab === 1 ? (
          <Grid item xs={12}>
            <BarChartCard
              title="Contributors"
              data={state.byAuthor}
              xLabel="User"
              yLabel="Count"
              loading={state.loading}
              error={state.errors.byAuthor ?? null}
            />
          </Grid>
        ) : (
          <Grid item xs={12}>
            <BarChartCard
              title="Vendors"
              data={state.byVendor}
              xLabel="Vendor"
              yLabel="Count"
              loading={state.loading}
              error={state.errors.byVendor ?? null}
            />
          </Grid>
        )}
      </Grid>

      {/* Vendor bar chart (global tab) */}
      {tab === 1 && (
        <Box mb={3}>
          <BarChartCard
            title="Top vendors"
            data={state.byVendor.slice(0, 15)}
            xLabel="Vendor"
            yLabel="Count"
            loading={state.loading}
            error={state.errors.byVendor ?? null}
          />
        </Box>
      )}

      {/* Detail table */}
      <Card>
        <CardHeader
          title="Record detail"
          subheader="At most 250 rows (server-limited query)"
          titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
        />
        <CardContent sx={{ pt: 0 }}>
          <DetailTable
            rows={state.detail}
            loading={state.loading}
            error={state.errors.detail ?? null}
          />
        </CardContent>
      </Card>
    </Box>
  )
}
