import { useState } from 'react'
import { Alert, Button, Card, Divider, Form, Input, Space, Typography } from 'antd'
import { WifiOutlined } from '@ant-design/icons'
import { Link as RouterLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { ApiError } from '@/api/client'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string })?.from ?? '/'

  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!identifier.trim() || !password) return
    setError(null)
    setLoading(true)
    try {
      await login(identifier.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <Card className="auth-card">
        <Space direction="vertical" size="small" align="center" style={{ width: '100%', marginBottom: 24 }}>
          <WifiOutlined style={{ fontSize: 40, color: 'var(--ant-color-primary)' }} />
          <Typography.Title level={3} style={{ margin: 0 }}>
            Wardrive
          </Typography.Title>
          <Typography.Text type="secondary">Inicia sesión para continuar</Typography.Text>
        </Space>

        {error && (
          <Alert type="error" showIcon closable onClose={() => setError(null)} message={error} style={{ marginBottom: 16 }} />
        )}

        <Form layout="vertical" onFinish={() => void handleSubmit()}>
          <Form.Item label="Usuario o correo">
            <Input
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              autoFocus
              autoComplete="username"
              disabled={loading}
            />
          </Form.Item>
          <Form.Item label="Contraseña">
            <Input.Password
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              disabled={loading}
            />
          </Form.Item>
          <div style={{ textAlign: 'right', marginTop: -8, marginBottom: 16 }}>
            <RouterLink to="/forgot-password">¿Olvidaste tu contraseña?</RouterLink>
          </div>
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            loading={loading}
            disabled={!identifier.trim() || !password}
          >
            {loading ? 'Iniciando sesión…' : 'Iniciar sesión'}
          </Button>
        </Form>

        <Divider />

        <Typography.Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 0 }}>
          ¿No tienes cuenta? <RouterLink to="/register">Regístrate</RouterLink>
        </Typography.Paragraph>
      </Card>
    </div>
  )
}
