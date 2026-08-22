import { useState } from 'react'
import { Avatar, Button, Grid, Layout as AntLayout, Menu, Space, theme, Tooltip, Typography } from 'antd'
import { LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined, MoonOutlined, SunOutlined } from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useThemeMode } from '@/context/ThemeModeContext'
import {
  NavAnalyticsIcon,
  NavBrandIcon,
  NavHomeIcon,
  NavKmlIcon,
  NavLteIcon,
  NavUploadIcon,
  NavWifiMapIcon,
} from '@/components/navIcons'

const { Header, Sider, Content } = AntLayout
const { useBreakpoint } = Grid

const DRAWER_WIDTH = 220
const STORAGE_KEY = 'wardrive-drawer-open'

type NavItem = {
  key: string
  label: string
  path: string
  icon: React.ReactNode
  mapMode?: 'wifi' | 'lte'
}

const navItems: NavItem[] = [
  { key: 'home', label: 'Home', path: '/', icon: <NavHomeIcon /> },
  { key: 'wifi', label: 'Wardriving', path: '/map', mapMode: 'wifi', icon: <NavWifiMapIcon /> },
  { key: 'lte', label: 'Wardriving LTE', path: '/map', mapMode: 'lte', icon: <NavLteIcon /> },
  { key: 'analytics', label: 'Analytics', path: '/analytics', icon: <NavAnalyticsIcon /> },
  { key: 'upload', label: 'Upload', path: '/upload', icon: <NavUploadIcon /> },
  { key: 'downloads', label: 'KML downloads', path: '/downloads', icon: <NavKmlIcon /> },
]

function getInitialDrawerOpen(): boolean {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === null ? true : stored === 'true'
  } catch {
    return true
  }
}

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const screens = useBreakpoint()
  const isMobile = !screens.md
  const [collapsed, setCollapsed] = useState(() => !getInitialDrawerOpen())
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, logout } = useAuth()
  const { isDarkMode, toggleTheme: onToggleTheme } = useThemeMode()
  const { token } = theme.useToken()

  const handleCollapse = (next: boolean) => {
    setCollapsed(next)
    try {
      localStorage.setItem(STORAGE_KEY, String(!next))
    } catch {
      /* ignore */
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const selectedKey = navItems.find((item) => {
    if (item.mapMode) {
      if (location.pathname !== item.path) return false
      const mode = new URLSearchParams(location.search).get('mode') ?? 'wifi'
      return (item.mapMode === 'lte' && mode === 'lte') || (item.mapMode === 'wifi' && mode !== 'lte')
    }
    if (item.path === '/') return location.pathname === '/'
    return location.pathname.startsWith(item.path)
  })?.key

  const handleNav = (key: string) => {
    const item = navItems.find((n) => n.key === key)
    if (!item) return
    if (item.mapMode) {
      navigate(`${item.path}?mode=${item.mapMode}`)
    } else {
      navigate(item.path)
    }
    if (isMobile) setMobileOpen(false)
  }

  const menu = (
    <Menu
      theme="dark"
      mode="inline"
      selectedKeys={selectedKey ? [selectedKey] : []}
      items={navItems.map((item) => ({
        key: item.key,
        icon: item.icon,
        label: item.label,
      }))}
      onClick={({ key }) => handleNav(key)}
      style={{ flex: 1, borderInlineEnd: 0 }}
    />
  )

  const siderInner = (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="app-sider-brand" style={{ justifyContent: collapsed && !isMobile ? 'center' : 'flex-start' }}>
        <NavBrandIcon />
        {(!collapsed || isMobile) && (
          <span>
            Wardrive <span className="brand-mx">MX</span>
          </span>
        )}
      </div>
      {menu}
      <div
        style={{
          padding: collapsed && !isMobile ? '12px 0' : 16,
          display: 'flex',
          justifyContent: collapsed && !isMobile ? 'center' : 'flex-start',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <Avatar size={28} style={{ backgroundColor: token.colorSuccess, color: '#07060A', fontWeight: 700 }}>
          {(user?.username?.[0] ?? 'U').toUpperCase()}
        </Avatar>
        {(!collapsed || isMobile) && (
          <div style={{ minWidth: 0 }}>
            <Typography.Text style={{ color: 'rgba(255,255,255,0.85)' }} ellipsis>
              {user?.username ?? 'User'}
            </Typography.Text>
            <br />
            <Typography.Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>
              v0.1.0
            </Typography.Text>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      {isMobile ? (
        <Sider
          breakpoint="md"
          collapsedWidth={0}
          collapsed={!mobileOpen}
          onCollapse={(c) => setMobileOpen(!c)}
          width={DRAWER_WIDTH}
          theme="dark"
          style={{ position: 'fixed', zIndex: 100, height: '100vh' }}
        >
          {siderInner}
        </Sider>
      ) : (
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={handleCollapse}
          width={DRAWER_WIDTH}
          theme="dark"
          trigger={null}
          style={{ overflow: 'auto', height: '100vh', position: 'sticky', top: 0 }}
        >
          {siderInner}
        </Sider>
      )}

      <AntLayout>
        <Header
          style={{
            display: 'flex',
            alignItems: 'center',
            paddingInline: 16,
            height: 48,
            lineHeight: '48px',
            background: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Button
            type="text"
            icon={isMobile ? <MenuUnfoldOutlined /> : collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => (isMobile ? setMobileOpen(true) : handleCollapse(!collapsed))}
            style={{ marginRight: 12 }}
          />
          <Typography.Text strong style={{ flex: 1 }}>
            Wardriving Contest Platform
          </Typography.Text>
          <Space>
            <Tooltip title={isDarkMode ? 'Light mode' : 'Dark mode'}>
              <Button type="text" icon={isDarkMode ? <SunOutlined /> : <MoonOutlined />} onClick={onToggleTheme} />
            </Tooltip>
            <Tooltip title="Sign out">
              <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout} />
            </Tooltip>
          </Space>
        </Header>
        <Content style={{ margin: 16, minHeight: 280 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
