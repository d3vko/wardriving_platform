import { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Card, DatePicker, Space, Spin, Table, Tabs, Tooltip, Typography } from 'antd'
import { BarChartOutlined, CalendarOutlined, ReloadOutlined } from '@ant-design/icons'
import { Column } from '@ant-design/plots'
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
import { RF_VILLAGE } from '@/theme'
import { useThemeMode } from '@/context/ThemeModeContext'

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
  loading,
  error,
}: {
  title: string
  data: ChartData[]
  loading: boolean
  error: string | null
}) {
  const { isDarkMode } = useThemeMode()
  const axisFill = isDarkMode ? RF_VILLAGE.textSecondary : '#434343'
  return (
    <Card title={title} style={{ height: '100%' }}>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
          <Spin />
        </div>
      ) : error ? (
        <Alert type="error" message={error} />
      ) : data.length === 0 ? (
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          Sin datos
        </Typography.Paragraph>
      ) : (
        <Column
          data={data}
          xField="label"
          yField="value"
          height={280}
          color={RF_VILLAGE.purple}
          axis={{
            x: { labelFill: axisFill, titleFill: axisFill },
            y: { labelFill: axisFill, titleFill: axisFill },
          }}
        />
      )}
    </Card>
  )
}

const DETAIL_COLS = [
  { dataIndex: 'ssid', title: 'SSID' },
  { dataIndex: 'mac', title: 'MAC' },
  { dataIndex: 'auth_mode', title: 'Auth Mode' },
  { dataIndex: 'vendor', title: 'Fabricante' },
  { dataIndex: 'registry', title: 'Registro' },
  { dataIndex: 'source', title: 'Fuente' },
  { dataIndex: 'signal_streng', title: 'Señal' },
  { dataIndex: 'rssi', title: 'RSSI' },
  { dataIndex: 'channel', title: 'Canal' },
  { dataIndex: 'device_source', title: 'Dispositivo' },
  { dataIndex: 'uploaded_by', title: 'Usuario' },
  { dataIndex: 'first_seen', title: 'First Seen' },
  { dataIndex: 'type', title: 'Tipo' },
  { dataIndex: 'current_latitude', title: 'Latitud' },
  { dataIndex: 'current_longitude', title: 'Longitud' },
]

function DetailTable({
  rows,
  loading,
  error,
}: {
  rows: DetailRow[]
  loading: boolean
  error: string | null
}) {
  if (error) return <Alert type="error" message={error} />
  return (
    <Table
      size="small"
      loading={loading}
      pagination={false}
      scroll={{ x: true, y: 400 }}
      dataSource={rows.slice(0, 250).map((row, i) => ({ key: i, ...row }))}
      locale={{ emptyText: 'No records for the selected period.' }}
      columns={DETAIL_COLS.map((c) => ({
        ...c,
        render: (value: unknown) => (value != null ? String(value) : '—'),
      }))}
    />
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
  const [tab, setTab] = useState<'self' | 'global'>('self')
  const [startDateInput, setStartDateInput] = useState(isoToDateInputValue(ANALYTICS_DEFAULTS.startDate))
  const [endDateInput, setEndDateInput] = useState(isoToDateInputValue(ANALYTICS_DEFAULTS.endDate))
  const [state, setState] = useState<AnalyticsState>(INITIAL_STATE)

  const scope: AnalyticsScope = tab === 'self' ? 'self-analytics' : 'global-analytics'

  const load = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, errors: {} }))
    const range = dateInputToDayRangeIso(startDateInput, endDateInput, {
      minIso: ANALYTICS_DEFAULTS.minDate,
      maxIso: ANALYTICS_DEFAULTS.maxDate,
    })

    const params = {
      first_seen_start: range.startIso,
      first_seen_end: range.endIso,
      ...(tab === 'self' && user?.username ? { author: user.username } : {}),
    }

    const results = await Promise.allSettled([
      fetchAuthModes(scope, params),
      fetchByDevice(scope, params),
      fetchBySignal(scope, params),
      fetchByVendor(scope, params),
      tab === 'global'
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
    <div>
      <div className="page-title-row">
        <BarChartOutlined style={{ fontSize: 32, color: 'var(--ant-color-primary)' }} />
        <Typography.Title level={2} style={{ margin: 0 }}>
          Analytics
        </Typography.Title>
        <Tooltip title="Reload data">
          <Button icon={<ReloadOutlined />} onClick={() => void load()} disabled={state.loading} />
        </Tooltip>
      </div>

      <Tabs
        activeKey={tab}
        onChange={(key) => setTab(key as 'self' | 'global')}
        items={[
          { key: 'self', label: `My data${user?.username ? ` (${user.username})` : ''}` },
          { key: 'global', label: 'Global' },
        ]}
      />

      <Card style={{ marginBottom: 24 }}>
        <Space style={{ marginBottom: 12 }}>
          <CalendarOutlined />
          <Typography.Text type="secondary">Date range filter</Typography.Text>
        </Space>
        <Space wrap>
          <DatePicker
            value={dayjs(startDateInput)}
            minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
            maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
            onChange={(value: Dayjs | null) => {
              if (!value || !value.isValid()) return
              setStartDateInput(value.format('YYYY-MM-DD'))
            }}
          />
          <DatePicker
            value={dayjs(endDateInput)}
            minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
            maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
            onChange={(value: Dayjs | null) => {
              if (!value || !value.isValid()) return
              setEndDateInput(value.format('YYYY-MM-DD'))
            }}
          />
          <Typography.Text type="secondary">Local timezone day bounds (00:00 - 23:59)</Typography.Text>
        </Space>
        {tab === 'self' && user?.username && (
          <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
            Filtered by user: <strong>{user.username}</strong>
          </Typography.Paragraph>
        )}
      </Card>

      <Space direction="vertical" size="large" style={{ width: '100%', marginBottom: 24 }}>
        <BarChartCard title="Authentication modes" data={state.authModes} loading={state.loading} error={state.errors.authModes ?? null} />
        <BarChartCard title="Devices" data={state.byDevice} loading={state.loading} error={state.errors.byDevice ?? null} />
        <BarChartCard title="Signal strength" data={state.bySignal} loading={state.loading} error={state.errors.bySignal ?? null} />
        {tab === 'global' ? (
          <BarChartCard title="Contributors" data={state.byAuthor} loading={state.loading} error={state.errors.byAuthor ?? null} />
        ) : (
          <BarChartCard title="Vendors" data={state.byVendor} loading={state.loading} error={state.errors.byVendor ?? null} />
        )}
        {tab === 'global' && (
          <BarChartCard
            title="Top vendors"
            data={state.byVendor.slice(0, 15)}
            loading={state.loading}
            error={state.errors.byVendor ?? null}
          />
        )}
      </Space>

      <Card title="Record detail" extra="At most 250 rows (server-limited query)">
        <DetailTable rows={state.detail} loading={state.loading} error={state.errors.detail ?? null} />
      </Card>
    </div>
  )
}
