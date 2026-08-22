import { useEffect, useState } from 'react'
import { Alert, Button, Card, DatePicker, Modal, Progress, Space, Spin, Typography } from 'antd'
import { DownloadOutlined, WarningOutlined } from '@ant-design/icons'
import { useBlocker } from 'react-router-dom'
import dayjs, { type Dayjs } from 'dayjs'

import { ANALYTICS_DEFAULTS } from '@/api/analytics'
import { ApiError } from '@/api/client'
import { downloadLteKml, downloadWifiKml } from '@/api/wardriveMap'
import { dateInputToDayRangeIso, isoToDateInputValue } from '@/utils/datetimeLocal'

type DownloadKind = 'wifi' | 'lte' | null

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function KmlDownloads() {
  const [loading, setLoading] = useState<DownloadKind>(null)
  const [error, setError] = useState<string | null>(null)
  const [errorStatus, setErrorStatus] = useState<number | null>(null)
  const [zipSuccess, setZipSuccess] = useState(false)
  const [afterDate, setAfterDate] = useState(() => isoToDateInputValue(ANALYTICS_DEFAULTS.startDate))
  const [beforeDate, setBeforeDate] = useState(() => isoToDateInputValue(ANALYTICS_DEFAULTS.endDate))
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (loading === null) {
      setElapsed(0)
      return
    }
    const id = window.setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => window.clearInterval(id)
  }, [loading])

  useEffect(() => {
    if (loading === null) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [loading])

  const blocker = useBlocker(loading !== null)

  const handleDownload = async (kind: Exclude<DownloadKind, null>) => {
    setError(null)
    setErrorStatus(null)
    setZipSuccess(false)
    if (!afterDate || !beforeDate) {
      setError('Set both start and end dates of the range.')
      return
    }
    const range = dateInputToDayRangeIso(afterDate, beforeDate, {
      minIso: ANALYTICS_DEFAULTS.minDate,
      maxIso: ANALYTICS_DEFAULTS.maxDate,
    })
    setAfterDate(range.fromDate)
    setBeforeDate(range.toDate)
    const first_seen_after = range.startIso
    const first_seen_before = range.endIso
    if (new Date(first_seen_after) > new Date(first_seen_before)) {
      setError('The start of the range must be before or equal to the end.')
      return
    }
    setLoading(kind)
    try {
      const params = { first_seen_after, first_seen_before }
      if (kind === 'wifi') {
        const { isZip } = await downloadWifiKml(params)
        if (isZip) setZipSuccess(true)
      } else {
        await downloadLteKml(params)
      }
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        setError(e.detail)
        setErrorStatus(e.status)
      } else if (e instanceof Error) {
        setError(e.message)
        setErrorStatus(null)
      } else {
        setError('Could not download the KML file.')
        setErrorStatus(null)
      }
    } finally {
      setLoading(null)
    }
  }

  return (
    <div>
      <Typography.Title level={3}>KML downloads</Typography.Title>
      <Typography.Paragraph type="secondary">
        Download your scans by technology. Files include only data for the current session user. Each point
        includes full metadata in the popup when you click it in Google My Maps. KML is optimized for{' '}
        <strong>Google My Maps</strong> (limit 5&nbsp;MB per file). Large WiFi exports are delivered as a{' '}
        <strong>ZIP</strong> with several KML files to import as separate layers. The API requires a date range (
        <code>first_seen_after</code> and <code>first_seen_before</code>) and normalizes each bound to the full
        calendar day in the value&apos;s timezone.
      </Typography.Paragraph>

      <Typography.Text type="secondary">Date range for export</Typography.Text>
      <Space wrap style={{ marginTop: 8, marginBottom: 24 }}>
        <DatePicker
          value={dayjs(afterDate)}
          minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
          maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
          onChange={(value: Dayjs | null) => {
            if (!value || !value.isValid()) return
            setAfterDate(value.format('YYYY-MM-DD'))
          }}
        />
        <DatePicker
          value={dayjs(beforeDate)}
          minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
          maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
          onChange={(value: Dayjs | null) => {
            if (!value || !value.isValid()) return
            setBeforeDate(value.format('YYYY-MM-DD'))
          }}
        />
      </Space>

      {zipSuccess && (
        <Alert
          style={{ marginBottom: 16 }}
          type="info"
          closable
          onClose={() => setZipSuccess(false)}
          message={
            <>
              Descarga completada como ZIP. Descomprime el archivo e importa cada <code>.kml</code> en Google My
              Maps como una capa separada (máximo 10 capas por mapa).
            </>
          }
        />
      )}

      {error && (
        <Alert
          style={{ marginBottom: 16 }}
          type={errorStatus === 413 ? 'warning' : 'error'}
          closable
          onClose={() => {
            setError(null)
            setErrorStatus(null)
          }}
          message={error}
        />
      )}

      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Card>
          <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
            <div>
              <Typography.Title level={5} style={{ marginTop: 0 }}>
                Download WiFi KML
              </Typography.Title>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                Export WiFi points with full metadata (SSID, vendor, signal, device, etc.) for Google My Maps.
                Large ranges may download as a ZIP with multiple KML files.
              </Typography.Paragraph>
            </div>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={loading === 'wifi'}
              disabled={loading !== null}
              onClick={() => void handleDownload('wifi')}
            >
              Download WiFi KML
            </Button>
          </Space>
        </Card>

        <Card>
          <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
            <div>
              <Typography.Title level={5} style={{ marginTop: 0 }}>
                Download LTE KML
              </Typography.Title>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                Export LTE cells (provider, cell_id, band, signal) with valid coordinates.
              </Typography.Paragraph>
            </div>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={loading === 'lte'}
              disabled={loading !== null}
              onClick={() => void handleDownload('lte')}
            >
              Download LTE KML
            </Button>
          </Space>
        </Card>
      </Space>

      {loading !== null && (
        <div className="kml-overlay" role="status" aria-live="polite" aria-label="Descargando archivo KML">
          <Spin size="large" />
          <div>
            <Typography.Title level={3} style={{ color: '#fff' }}>
              Generando archivo KML ({loading.toUpperCase()})…
            </Typography.Title>
            <Typography.Title level={4} style={{ color: '#90caf9' }}>
              {formatElapsed(elapsed)}
            </Typography.Title>
            <Typography.Paragraph style={{ color: 'rgba(255,255,255,0.75)' }}>
              El servidor está procesando y empaquetando tus datos. La descarga comenzará automáticamente al
              terminar.
            </Typography.Paragraph>
            <Space>
              <WarningOutlined style={{ color: '#faad14' }} />
              <Typography.Text strong style={{ color: '#faad14' }}>
                No cierres esta pestaña ni navegues a otra sección.
              </Typography.Text>
            </Space>
          </div>
          <div style={{ width: '100%', maxWidth: 420 }}>
            <Progress percent={100} status="active" showInfo={false} />
          </div>
        </div>
      )}

      <Modal
        open={blocker.state === 'blocked'}
        title="Descarga en curso"
        onCancel={() => blocker.reset?.()}
        footer={[
          <Button key="wait" type="primary" onClick={() => blocker.reset?.()}>
            Continuar esperando
          </Button>,
          <Button key="leave" danger onClick={() => blocker.proceed?.()}>
            Cancelar descarga y salir
          </Button>,
        ]}
      >
        Hay una descarga KML en progreso. Si navegas ahora la descarga se cancelará y no recibirás el archivo.
        ¿Deseas continuar de todas formas?
      </Modal>
    </div>
  )
}
