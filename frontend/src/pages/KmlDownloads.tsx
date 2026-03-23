import { useState } from 'react'
import { Alert, Box, Button, Card, CardContent, CircularProgress, Stack, Typography } from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'

import { ApiError } from '@/api/client'
import { downloadLteKml, downloadWifiKml } from '@/api/wardriveMap'

type DownloadKind = 'wifi' | 'lte' | null

export default function KmlDownloads() {
  const [loading, setLoading] = useState<DownloadKind>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDownload = async (kind: Exclude<DownloadKind, null>) => {
    setError(null)
    setLoading(kind)
    try {
      if (kind === 'wifi') await downloadWifiKml()
      else await downloadLteKml()
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        setError(e.detail)
      } else if (e instanceof Error) {
        setError(e.message)
      } else {
        setError('No fue posible descargar el archivo KML.')
      }
    } finally {
      setLoading(null)
    }
  }

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Descargas KML
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Descarga tus escaneos por tecnología. Los archivos incluyen solo datos del usuario de la
        sesión actual.
      </Typography>

      {error && (
        <Alert sx={{ mb: 2 }} severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Stack spacing={2}>
        <Card variant="outlined">
          <CardContent>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'start', sm: 'center' }} justifyContent="space-between">
              <Box>
                <Typography variant="h6">Descargar KML WiFi</Typography>
                <Typography variant="body2" color="text.secondary">
                  Exporta los puntos WiFi con metadatos para visualización en Google Earth.
                </Typography>
              </Box>
              <Button
                variant="contained"
                startIcon={loading === 'wifi' ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
                disabled={loading !== null}
                onClick={() => void handleDownload('wifi')}
              >
                Descargar KML WiFi
              </Button>
            </Stack>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'start', sm: 'center' }} justifyContent="space-between">
              <Box>
                <Typography variant="h6">Descargar KML LTE</Typography>
                <Typography variant="body2" color="text.secondary">
                  Exporta celdas LTE (provider, cell_id, banda y señal) con coordenadas válidas.
                </Typography>
              </Box>
              <Button
                variant="contained"
                startIcon={loading === 'lte' ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
                disabled={loading !== null}
                onClick={() => void handleDownload('lte')}
              >
                Descargar KML LTE
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    </Box>
  )
}
