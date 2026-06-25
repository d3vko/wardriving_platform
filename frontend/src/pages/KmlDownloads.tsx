import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import { useBlocker } from 'react-router-dom'

import { ANALYTICS_DEFAULTS } from '@/api/analytics'
import { ApiError } from '@/api/client'
import { downloadLteKml, downloadWifiKml } from '@/api/wardriveMap'
import { dateInputToDayRangeIso, isoToDateInputValue } from '@/utils/datetimeLocal'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import dayjs, { type Dayjs } from 'dayjs'

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

  // Timer: increments every second while a download is in progress.
  useEffect(() => {
    if (loading === null) {
      setElapsed(0)
      return
    }
    const id = window.setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => window.clearInterval(id)
  }, [loading])

  // Warn the browser (close/reload tab) while downloading.
  useEffect(() => {
    if (loading === null) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [loading])

  // Block in-app navigation (drawer, back button) while downloading.
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
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        KML downloads
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Download your scans by technology. Files include only data for the current session user.
        Each point includes full metadata in the popup when you click it in Google My Maps.
        KML is optimized for <strong>Google My Maps</strong> (limit 5&nbsp;MB per file). Large WiFi
        exports are delivered as a <strong>ZIP</strong> with several KML files to import as separate
        layers. The API requires a date range (<code>first_seen_after</code> and{' '}
        <code>first_seen_before</code>) and normalizes each bound to the full calendar day in the
        value&apos;s timezone.
      </Typography>

      <LocalizationProvider dateAdapter={AdapterDayjs}>
        <Stack direction="row" spacing={1} alignItems="center" mb={2}>
          <Typography variant="subtitle2" color="text.secondary">
            Date range for export
          </Typography>
        </Stack>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          sx={{ mb: 3 }}
          alignItems={{ sm: 'center' }}
        >
          <DatePicker
            label="From (range start)"
            value={dayjs(afterDate)}
            minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
            maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
            onChange={(value: Dayjs | null) => {
              if (!value || !value.isValid()) return
              setAfterDate(value.format('YYYY-MM-DD'))
            }}
            slotProps={{
              textField: { size: 'small', sx: { minWidth: 260 } },
            }}
          />
          <DatePicker
            label="To (range end)"
            value={dayjs(beforeDate)}
            minDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.minDate))}
            maxDate={dayjs(isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate))}
            onChange={(value: Dayjs | null) => {
              if (!value || !value.isValid()) return
              setBeforeDate(value.format('YYYY-MM-DD'))
            }}
            slotProps={{
              textField: { size: 'small', sx: { minWidth: 260 } },
            }}
          />
        </Stack>
      </LocalizationProvider>

      {zipSuccess && (
        <Alert
          sx={{ mb: 2 }}
          severity="info"
          onClose={() => setZipSuccess(false)}
        >
          Descarga completada como ZIP. Descomprime el archivo e importa cada{' '}
          <code>.kml</code> en Google My Maps como una capa separada (máximo 10 capas por mapa).
        </Alert>
      )}

      {error && (
        <Alert
          sx={{ mb: 2 }}
          severity={errorStatus === 413 ? 'warning' : 'error'}
          onClose={() => {
            setError(null)
            setErrorStatus(null)
          }}
        >
          {error}
        </Alert>
      )}

      <Stack spacing={2}>
        <Card variant="outlined">
          <CardContent>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={2}
              alignItems={{ xs: 'start', sm: 'center' }}
              justifyContent="space-between"
            >
              <Box>
                <Typography variant="h6">Download WiFi KML</Typography>
                <Typography variant="body2" color="text.secondary">
                  Export WiFi points with full metadata (SSID, vendor, signal, device, etc.) for
                  Google My Maps. Large ranges may download as a ZIP with multiple KML files.
                </Typography>
              </Box>
              <Button
                variant="contained"
                startIcon={loading === 'wifi' ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
                disabled={loading !== null}
                onClick={() => void handleDownload('wifi')}
              >
                Download WiFi KML
              </Button>
            </Stack>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={2}
              alignItems={{ xs: 'start', sm: 'center' }}
              justifyContent="space-between"
            >
              <Box>
                <Typography variant="h6">Download LTE KML</Typography>
                <Typography variant="body2" color="text.secondary">
                  Export LTE cells (provider, cell_id, band, signal) with valid coordinates.
                </Typography>
              </Box>
              <Button
                variant="contained"
                startIcon={loading === 'lte' ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
                disabled={loading !== null}
                onClick={() => void handleDownload('lte')}
              >
                Download LTE KML
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Stack>

      {/* Full-screen overlay while downloading */}
      {loading !== null && (
        <Box
          role="status"
          aria-live="polite"
          aria-label="Descargando archivo KML"
          sx={{
            position: 'fixed',
            inset: 0,
            zIndex: 1400,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 3,
            px: 4,
            bgcolor: 'rgba(0, 0, 0, 0.72)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <CircularProgress size={72} thickness={3} sx={{ color: 'primary.light' }} />

          <Stack spacing={1} alignItems="center" sx={{ maxWidth: 420, textAlign: 'center' }}>
            <Typography variant="h5" fontWeight={700} sx={{ color: '#fff' }}>
              Generando archivo KML ({loading.toUpperCase()})…
            </Typography>

            <Typography variant="h6" sx={{ color: 'primary.light', fontVariantNumeric: 'tabular-nums' }}>
              {formatElapsed(elapsed)}
            </Typography>

            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.75)' }}>
              El servidor está procesando y empaquetando tus datos. La descarga comenzará
              automáticamente al terminar.
            </Typography>

            <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
              <WarningAmberIcon sx={{ color: 'warning.light', fontSize: 20 }} />
              <Typography variant="body2" fontWeight={600} sx={{ color: 'warning.light' }}>
                No cierres esta pestaña ni navegues a otra sección.
              </Typography>
            </Stack>
          </Stack>

          <Box sx={{ width: '100%', maxWidth: 420 }}>
            <LinearProgress color="primary" />
          </Box>
        </Box>
      )}

      {/* Confirmation dialog when the user tries to navigate away via the SPA router */}
      <Dialog
        open={blocker.state === 'blocked'}
        onClose={() => blocker.reset?.()}
        aria-labelledby="nav-block-title"
      >
        <DialogTitle id="nav-block-title" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningAmberIcon color="warning" />
          Descarga en curso
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Hay una descarga KML en progreso. Si navegas ahora la descarga se cancelará y no
            recibirás el archivo. ¿Deseas continuar de todas formas?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => blocker.reset?.()} variant="contained" autoFocus>
            Continuar esperando
          </Button>
          <Button
            onClick={() => blocker.proceed?.()}
            color="error"
            variant="outlined"
          >
            Cancelar descarga y salir
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
