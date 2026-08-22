import { Button, Card, Space, Tag, Typography } from 'antd'
import { WifiOutlined } from '@ant-design/icons'
import { appConfig } from '@/config/eventConfig'

export default function Home() {
  return (
    <div>
      <div className="page-title-row">
        <WifiOutlined style={{ fontSize: 32, color: 'var(--ant-color-primary)' }} />
        <Typography.Title level={2} style={{ margin: 0 }}>
          {appConfig.homeTitle}
        </Typography.Title>
        <Tag color="blue">{appConfig.homeBadge}</Tag>
      </div>
      <Typography.Paragraph type="secondary" className="page-lead">
        {appConfig.introText}
      </Typography.Paragraph>

      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Typography.Title level={4}>{appConfig.dynamicsTitle}</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ whiteSpace: 'pre-line', marginBottom: 0 }}>
            {appConfig.dynamicsText}
          </Typography.Paragraph>
        </Card>

        <Card>
          <Typography.Title level={4}>{appConfig.logoCardTitle}</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ whiteSpace: 'pre-line' }}>
            {appConfig.logoCardText}
          </Typography.Paragraph>

          {appConfig.logoUrl ? (
            <img className="home-logo" src={appConfig.logoUrl} alt={appConfig.logoAlt} />
          ) : (
            <div className="home-logo-placeholder">
              Set <code>VITE_EVENT_LOGO_URL</code> to display your event logo here.
            </div>
          )}

          {appConfig.logoLinkUrl && (
            <div style={{ marginTop: 16 }}>
              <Button href={appConfig.logoLinkUrl} target="_blank" rel="noreferrer">
                {appConfig.logoLinkLabel}
              </Button>
            </div>
          )}
        </Card>
      </Space>
    </div>
  )
}
