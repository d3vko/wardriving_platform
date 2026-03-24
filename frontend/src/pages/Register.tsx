import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  Link,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { WifiFind as WifiFindIcon } from '@mui/icons-material'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { ApiError } from '@/api/client'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    passwordConfirm: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.passwordConfirm) {
      setError('Passwords do not match')
      return
    }
    setError(null)
    setLoading(true)
    try {
      await register(form.username.trim(), form.email.trim(), form.password, form.passwordConfirm)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to register')
    } finally {
      setLoading(false)
    }
  }

  const isValid =
    form.username.trim() && form.email.trim() && form.password && form.passwordConfirm

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
          maxWidth: 420,
          p: 4,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 3,
        }}
      >
        <Stack alignItems="center" spacing={1} mb={3}>
          <WifiFindIcon color="primary" sx={{ fontSize: 40 }} />
          <Typography variant="h5" fontWeight={700}>
            Create account
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Join Wardrive
          </Typography>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Username"
              value={form.username}
              onChange={set('username')}
              autoFocus
              fullWidth
              autoComplete="username"
              disabled={loading}
            />
            <TextField
              label="Email"
              type="email"
              value={form.email}
              onChange={set('email')}
              fullWidth
              autoComplete="email"
              disabled={loading}
            />
            <TextField
              label="Password"
              type="password"
              value={form.password}
              onChange={set('password')}
              fullWidth
              autoComplete="new-password"
              disabled={loading}
            />
            <TextField
              label="Confirm password"
              type="password"
              value={form.passwordConfirm}
              onChange={set('passwordConfirm')}
              fullWidth
              autoComplete="new-password"
              disabled={loading}
              error={Boolean(form.passwordConfirm && form.password !== form.passwordConfirm)}
              helperText={
                form.passwordConfirm && form.password !== form.passwordConfirm
                  ? 'Passwords do not match'
                  : undefined
              }
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              fullWidth
              disabled={loading || !isValid}
              startIcon={loading ? <CircularProgress size={18} color="inherit" /> : null}
            >
              {loading ? 'Registering…' : 'Create account'}
            </Button>
          </Stack>
        </Box>

        <Divider sx={{ my: 3 }} />

        <Typography variant="body2" color="text.secondary" textAlign="center">
          Already have an account?{' '}
          <Link component={RouterLink} to="/login" underline="hover">
            Sign in
          </Link>
        </Typography>
      </Paper>
    </Box>
  )
}
