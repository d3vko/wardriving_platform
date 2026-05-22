import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Link,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { LockReset as LockResetIcon } from '@mui/icons-material'
import { Link as RouterLink } from 'react-router-dom'
import { requestPasswordReset } from '@/api/auth'
import { ApiError } from '@/api/client'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    setError(null)
    setLoading(true)
    try {
      await requestPasswordReset(email.trim())
      setSent(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error al procesar la solicitud')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
        p: 2,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          width: '100%',
          maxWidth: 400,
          p: 4,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 3,
        }}
      >
        <Stack alignItems="center" spacing={1} mb={3}>
          <LockResetIcon color="primary" sx={{ fontSize: 40 }} />
          <Typography variant="h5" fontWeight={700}>
            Recuperar contraseña
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center">
            Ingresa tu correo y te enviaremos instrucciones para restablecerla.
          </Typography>
        </Stack>

        {sent ? (
          <Alert severity="success">
            Si el correo está registrado, recibirás un enlace en tu bandeja de entrada.
          </Alert>
        ) : (
          <>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                {error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit}>
              <Stack spacing={2}>
                <TextField
                  label="Correo electrónico"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                  fullWidth
                  autoComplete="email"
                  disabled={loading}
                />
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  fullWidth
                  disabled={loading || !email.trim()}
                  startIcon={loading ? <CircularProgress size={18} color="inherit" /> : null}
                >
                  {loading ? 'Enviando…' : 'Enviar instrucciones'}
                </Button>
              </Stack>
            </Box>
          </>
        )}

        <Box mt={3} textAlign="center">
          <Link component={RouterLink} to="/login" variant="body2" underline="hover">
            Volver al inicio de sesión
          </Link>
        </Box>
      </Paper>
    </Box>
  )
}
