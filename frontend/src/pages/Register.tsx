import { useState } from 'react'
import { Alert, Button, Card, Divider, Form, Input, Space, Typography } from 'antd'
import { WifiOutlined } from '@ant-design/icons'
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

  const handleSubmit = async () => {
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

  const isValid = form.username.trim() && form.email.trim() && form.password && form.passwordConfirm
  const mismatch = Boolean(form.passwordConfirm && form.password !== form.passwordConfirm)

  return (
    <div className="auth-page">
      <Card className="auth-card auth-card-wide">
        <Space direction="vertical" size="small" align="center" style={{ width: '100%', marginBottom: 24 }}>
          <WifiOutlined style={{ fontSize: 40, color: 'var(--ant-color-primary)' }} />
          <Typography.Title level={3} style={{ margin: 0 }}>
            Create account
          </Typography.Title>
          <Typography.Text type="secondary">Join Wardrive</Typography.Text>
        </Space>

        {error && (
          <Alert type="error" showIcon closable onClose={() => setError(null)} message={error} style={{ marginBottom: 16 }} />
        )}

        <Form layout="vertical" onFinish={() => void handleSubmit()}>
          <Form.Item label="Username">
            <Input
              value={form.username}
              onChange={(e) => setForm((p) => ({ ...p, username: e.target.value }))}
              autoFocus
              autoComplete="username"
              disabled={loading}
            />
          </Form.Item>
          <Form.Item label="Email">
            <Input
              type="email"
              value={form.email}
              onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
              autoComplete="email"
              disabled={loading}
            />
          </Form.Item>
          <Form.Item label="Password">
            <Input.Password
              value={form.password}
              onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
              autoComplete="new-password"
              disabled={loading}
            />
          </Form.Item>
          <Form.Item
            label="Confirm password"
            validateStatus={mismatch ? 'error' : undefined}
            help={mismatch ? 'Passwords do not match' : undefined}
          >
            <Input.Password
              value={form.passwordConfirm}
              onChange={(e) => setForm((p) => ({ ...p, passwordConfirm: e.target.value }))}
              autoComplete="new-password"
              disabled={loading}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" size="large" block loading={loading} disabled={!isValid}>
            {loading ? 'Registering…' : 'Create account'}
          </Button>
        </Form>

        <Divider />

        <Typography.Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 0 }}>
          Already have an account? <RouterLink to="/login">Sign in</RouterLink>
        </Typography.Paragraph>
      </Card>
    </div>
  )
}
