import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'

import { ANALYTICS_DEFAULTS } from '@/api/analytics'
import { ApiError } from '@/api/client'
import { downloadLteKml, downloadWifiKml } from '@/api/wardriveMap'
import { dateInputToDayRangeIso, isoToDateInputValue } from '@/utils/datetimeLocal'

type DownloadKind = 'wifi' | 'lte' | null

export default function KmlDownloads() {
  const [loading, setLoading] = useState<DownloadKind>(null)
  const [error, setError] = useState<string | null>(null)
  const [afterDate, setAfterDate] = useState(() => isoToDateInputValue(ANALYTICS_DEFAULTS.startDate))
  const [beforeDate, setBeforeDate] = useState(() => isoToDateInputValue(ANALYTICS_DEFAULTS.endDate))

  const handleDownload = async (kind: Exclude<DownloadKind, null>) => {
    setError(null)
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
      if (kind === 'wifi') await downloadWifiKml(params)
      else await downloadLteKml(params)
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        setError(e.detail)
      } else if (e instanceof Error) {
        setError(e.message)
      } else {
        setError('Could not download the KML file.')
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
        The API requires a date range (`first_seen_after` and `first_seen_before`) and normalizes
        each bound to the full calendar day in the value&apos;s timezone. Very wide ranges may take
        longer to generate.
      </Typography>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 3 }} alignItems={{ sm: 'center' }}>
        <TextField
          label="From (range start)"
          type="date"
          value={afterDate}
          onChange={(e) => setAfterDate(e.target.value)}
          InputLabelProps={{ shrink: true }}
          size="small"
          sx={{ minWidth: 260 }}
          inputProps={{
            min: isoToDateInputValue(ANALYTICS_DEFAULTS.minDate),
            max: isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate),
          }}
        />
        <TextField
          label="To (range end)"
          type="date"
          value={beforeDate}
          onChange={(e) => setBeforeDate(e.target.value)}
          InputLabelProps={{ shrink: true }}
          size="small"
          sx={{ minWidth: 260 }}
          inputProps={{
            min: isoToDateInputValue(ANALYTICS_DEFAULTS.minDate),
            max: isoToDateInputValue(ANALYTICS_DEFAULTS.maxDate),
          }}
        />
      </Stack>

      {error && (
        <Alert sx={{ mb: 2 }} severity="error" onClose={() => setError(null)}>
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
                  Export WiFi points with metadata for Google Earth and similar tools.
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
    </Box>
  )
}
