import { useState } from 'react'
import { Alert, Button, Card, Form, Input, Space, Typography } from 'antd'
import { LockOutlined } from '@ant-design/icons'
import { Link as RouterLink } from 'react-router-dom'
import { requestPasswordReset } from '@/api/auth'
import { ApiError } from '@/api/client'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
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
    <div className="auth-page">
      <Card className="auth-card">
        <Space direction="vertical" size="small" align="center" style={{ width: '100%', marginBottom: 24 }}>
          <LockOutlined style={{ fontSize: 40, color: 'var(--ant-color-primary)' }} />
          <Typography.Title level={3} style={{ margin: 0 }}>
            Recuperar contraseña
          </Typography.Title>
          <Typography.Text type="secondary" style={{ textAlign: 'center' }}>
            Ingresa tu correo y te enviaremos instrucciones para restablecerla.
          </Typography.Text>
        </Space>

        {sent ? (
          <Alert type="success" showIcon message="Si el correo está registrado, recibirás un enlace en tu bandeja de entrada." />
        ) : (
          <>
            {error && (
              <Alert type="error" showIcon closable onClose={() => setError(null)} message={error} style={{ marginBottom: 16 }} />
            )}
            <Form layout="vertical" onFinish={() => void handleSubmit()}>
              <Form.Item label="Correo electrónico">
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                  autoComplete="email"
                  disabled={loading}
                />
              </Form.Item>
              <Button type="primary" htmlType="submit" size="large" block loading={loading} disabled={!email.trim()}>
                {loading ? 'Enviando…' : 'Enviar instrucciones'}
              </Button>
            </Form>
          </>
        )}

        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <RouterLink to="/login">Volver al inicio de sesión</RouterLink>
        </div>
      </Card>
    </div>
  )
}
