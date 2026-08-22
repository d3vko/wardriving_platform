import { useState } from 'react'
import { Alert, Button, Card, Form, Input, Space, Typography } from 'antd'
import { LockOutlined } from '@ant-design/icons'
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

  const handleSubmit = async () => {
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
    <div className="auth-page">
      <Card className="auth-card">
        <Space direction="vertical" size="small" align="center" style={{ width: '100%', marginBottom: 24 }}>
          <LockOutlined style={{ fontSize: 40, color: 'var(--ant-color-primary)' }} />
          <Typography.Title level={3} style={{ margin: 0 }}>
            Nueva contraseña
          </Typography.Title>
          <Typography.Text type="secondary" style={{ textAlign: 'center' }}>
            Elige una contraseña segura para tu cuenta.
          </Typography.Text>
        </Space>

        {isInvalidLink && (
          <Alert type="error" showIcon message="El enlace no es válido o ha expirado. Solicita uno nuevo." style={{ marginBottom: 16 }} />
        )}

        {done ? (
          <>
            <Alert type="success" showIcon message="Contraseña actualizada correctamente." style={{ marginBottom: 16 }} />
            <div style={{ textAlign: 'center' }}>
              <RouterLink to="/login">Iniciar sesión</RouterLink>
            </div>
          </>
        ) : (
          <>
            {error && (
              <Alert type="error" showIcon closable onClose={() => setError(null)} message={error} style={{ marginBottom: 16 }} />
            )}
            <Form layout="vertical" onFinish={() => void handleSubmit()}>
              <Form.Item label="Nueva contraseña">
                <Input.Password
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoFocus
                  autoComplete="new-password"
                  disabled={loading || isInvalidLink}
                />
              </Form.Item>
              <Form.Item label="Confirmar contraseña">
                <Input.Password
                  value={newPasswordConfirm}
                  onChange={(e) => setNewPasswordConfirm(e.target.value)}
                  autoComplete="new-password"
                  disabled={loading || isInvalidLink}
                />
              </Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                block
                loading={loading}
                disabled={isInvalidLink || !newPassword || !newPasswordConfirm}
              >
                {loading ? 'Guardando…' : 'Guardar contraseña'}
              </Button>
            </Form>
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <RouterLink to="/login">Volver al inicio de sesión</RouterLink>
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
