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
import { Link as RouterLink, useSearchParams } from 'react-router-dom'
import { confirmPasswordReset } from '@/api/auth'
import { ApiError } from '@/api/client'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const uid = searchParams.get('uid') ?? ''
  const token = searchParams.get('token') ?? ''

  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const isInvalidLink = !uid || !token

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newPassword || !newPasswordConfirm) return
    setError(null)
    setLoading(true)
    try {
      await confirmPasswordReset(uid, token, newPassword, newPasswordConfirm)
      setDone(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error al restablecer la contraseña')
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
            Nueva contraseña
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center">
            Elige una contraseña segura para tu cuenta.
          </Typography>
        </Stack>

        {isInvalidLink && (
          <Alert severity="error" sx={{ mb: 2 }}>
            El enlace no es válido o ha expirado. Solicita uno nuevo.
          </Alert>
        )}

        {done ? (
          <>
            <Alert severity="success" sx={{ mb: 2 }}>
              Contraseña actualizada correctamente.
            </Alert>
            <Box textAlign="center">
              <Link component={RouterLink} to="/login" variant="body2" underline="hover">
                Iniciar sesión
              </Link>
            </Box>
          </>
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
                  label="Nueva contraseña"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoFocus
                  fullWidth
                  autoComplete="new-password"
                  disabled={loading || isInvalidLink}
                />
                <TextField
                  label="Confirmar contraseña"
                  type="password"
                  value={newPasswordConfirm}
                  onChange={(e) => setNewPasswordConfirm(e.target.value)}
                  fullWidth
                  autoComplete="new-password"
                  disabled={loading || isInvalidLink}
                />
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  fullWidth
                  disabled={loading || isInvalidLink || !newPassword || !newPasswordConfirm}
                  startIcon={loading ? <CircularProgress size={18} color="inherit" /> : null}
                >
                  {loading ? 'Guardando…' : 'Guardar contraseña'}
                </Button>
              </Stack>
            </Box>

            <Box mt={3} textAlign="center">
              <Link component={RouterLink} to="/login" variant="body2" underline="hover">
                Volver al inicio de sesión
              </Link>
            </Box>
          </>
        )}
      </Paper>
    </Box>
  )
}
