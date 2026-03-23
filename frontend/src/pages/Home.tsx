import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from '@mui/material'
import { WifiFind as WifiFindIcon } from '@mui/icons-material'

import { appConfig } from '@/config/eventConfig'

export default function Home() {
  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1.5} mb={1}>
        <WifiFindIcon color="primary" sx={{ fontSize: 32 }} />
        <Typography variant="h4" fontWeight={700}>
          {appConfig.homeTitle}
        </Typography>
        <Chip label={appConfig.homeBadge} color="primary" size="small" />
      </Stack>
      <Typography variant="body1" color="text.secondary" mb={4}>
        {appConfig.introText}
      </Typography>

      <Stack spacing={3}>
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} mb={2}>
              {appConfig.dynamicsTitle}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
              {appConfig.dynamicsText}
            </Typography>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" fontWeight={600} mb={1}>
              {appConfig.logoCardTitle}
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={2} sx={{ whiteSpace: 'pre-line' }}>
              {appConfig.logoCardText}
            </Typography>

            {appConfig.logoUrl ? (
              <Box
                component="img"
                src={appConfig.logoUrl}
                alt={appConfig.logoAlt}
                sx={{
                  maxWidth: { xs: '100%', sm: 360 },
                  width: '100%',
                  height: 'auto',
                  borderRadius: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  p: 1,
                  bgcolor: 'background.paper',
                }}
              />
            ) : (
              <Box
                sx={{
                  border: '1px dashed',
                  borderColor: 'divider',
                  borderRadius: 2,
                  p: 2,
                  color: 'text.secondary',
                }}
              >
                Set <code>VITE_EVENT_LOGO_URL</code> to display your event logo here.
              </Box>
            )}

            {appConfig.logoLinkUrl && (
              <Button
                sx={{ mt: 2 }}
                variant="outlined"
                component="a"
                href={appConfig.logoLinkUrl}
                target="_blank"
                rel="noreferrer"
              >
                {appConfig.logoLinkLabel}
              </Button>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Box>
  )
}
