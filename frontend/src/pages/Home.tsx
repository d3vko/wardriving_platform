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
          Dashboard
        </Typography>
        <Chip label="Live" color="success" size="small" />
      </Stack>
      <Typography variant="body1" color="text.secondary" mb={4}>
        Wardriving Contest Platform — monitor de redes en tiempo real.
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
              Actividad reciente
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Sin datos disponibles. Inicia un escaneo para ver actividad.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}
