import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from '@mui/material'
import {
  WifiFind as WifiFindIcon,
  Router as RouterIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material'

const statCards = [
  {
    label: 'Networks Detected',
    value: '—',
    icon: <WifiFindIcon fontSize="large" />,
    color: 'primary.main',
  },
  {
    label: 'Access Points',
    value: '—',
    icon: <RouterIcon fontSize="large" />,
    color: 'success.main',
  },
  {
    label: 'Encrypted',
    value: '—',
    icon: <SecurityIcon fontSize="large" />,
    color: 'warning.main',
  },
  {
    label: 'Scan Speed',
    value: '—',
    icon: <SpeedIcon fontSize="large" />,
    color: 'info.main',
  },
]

export default function Home() {
  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1.5} mb={1}>
        <WifiFindIcon color="primary" sx={{ fontSize: 32 }} />
        <Typography variant="h4" fontWeight={700}>
          Inicio
        </Typography>
        <Chip label="Evento" color="primary" size="small" />
      </Stack>
      <Typography variant="body1" color="text.secondary" mb={4}>
        Bienvenido a la plataforma del evento de Wardriving. Aqui podras cargar capturas, revisar
        analiticas, explorar mapas WiFi/LTE y descargar tus resultados en KML.
      </Typography>

      <Grid container spacing={3}>
        {statCards.map(({ label, value, icon, color }) => (
          <Grid key={label} item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box>
                    <Typography variant="h3" fontWeight={700}>
                      {value}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" mt={0.5}>
                      {label}
                    </Typography>
                  </Box>
                  <Box sx={{ color }}>{icon}</Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Box mt={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} mb={2}>
              Dinamica del evento
            </Typography>
            <Typography variant="body2" color="text.secondary">
              1) Recolecta muestras con dispositivos soportados. 2) Sube los archivos en la seccion
              Upload. 3) Revisa tus hallazgos en mapa y analytics. 4) Exporta KML desde Descargas KML.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}
