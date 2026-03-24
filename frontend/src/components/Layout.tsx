import { useState, type ReactNode } from 'react'
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Home as HomeIcon,
  WifiFind as WifiFindIcon,
  CellTower as CellTowerIcon,
  BarChart as BarChartIcon,
  CloudUpload as CloudUploadIcon,
  Download as DownloadIcon,
  DarkMode as DarkModeIcon,
  LightMode as LightModeIcon,
  ChevronLeft as ChevronLeftIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

const DRAWER_WIDTH = 240
const MINI_DRAWER_WIDTH = 64
const STORAGE_KEY = 'wardrive-drawer-open'

type NavItem =
  | { label: string; path: string; icon: ReactNode; mapMode?: undefined }
  | {
      label: string
      path: string
      icon: ReactNode
      mapMode: 'wifi' | 'lte'
    }

const navItems: NavItem[] = [
  { label: 'Home', path: '/', icon: <HomeIcon /> },
  { label: 'Wardriving', path: '/map', mapMode: 'wifi', icon: <WifiFindIcon /> },
  { label: 'Wardriving LTE', path: '/map', mapMode: 'lte', icon: <CellTowerIcon /> },
  { label: 'Analytics', path: '/analytics', icon: <BarChartIcon /> },
  { label: 'Upload', path: '/upload', icon: <CloudUploadIcon /> },
  { label: 'KML downloads', path: '/downloads', icon: <DownloadIcon /> },
]

interface LayoutProps {
  onToggleTheme: () => void
  isDarkMode: boolean
}

function getInitialDrawerOpen(): boolean {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === null ? true : stored === 'true'
  } catch {
    return true
  }
}

export default function Layout({ onToggleTheme, isDarkMode }: LayoutProps) {
  const theme = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [drawerOpen, setDrawerOpen] = useState(getInitialDrawerOpen)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, logout } = useAuth()

  const handleDrawerToggle = () => {
    if (isMobile) {
      setMobileOpen((prev) => !prev)
    } else {
      setDrawerOpen((prev) => {
        const next = !prev
        try { localStorage.setItem(STORAGE_KEY, String(next)) } catch { /* ignore */ }
        return next
      })
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const handleNav = (item: NavItem) => {
    if (item.mapMode) {
      navigate(`${item.path}?mode=${item.mapMode}`)
    } else {
      navigate(item.path)
    }
    if (isMobile) setMobileOpen(false)
  }

  const isSelected = (item: NavItem) => {
    if (item.mapMode) {
      if (location.pathname !== item.path) return false
      const mode = new URLSearchParams(location.search).get('mode') ?? 'wifi'
      return (item.mapMode === 'lte' && mode === 'lte') || (item.mapMode === 'wifi' && mode !== 'lte')
    }
    if (item.path === '/') return location.pathname === '/'
    return location.pathname.startsWith(item.path)
  }

  // Mini drawer: solo iconos con tooltip
  const miniDrawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', alignItems: 'center' }}>
      <Toolbar sx={{ width: '100%', justifyContent: 'center', minHeight: '64px !important' }}>
        <Tooltip title="Open menu" placement="right">
          <IconButton onClick={handleDrawerToggle} size="small">
            <MenuIcon />
          </IconButton>
        </Tooltip>
      </Toolbar>
      <Divider sx={{ width: '100%' }} />
      <List sx={{ flexGrow: 1, pt: 1, width: '100%', px: 0.5 }}>
        {navItems.map((item) => (
          <ListItem
            key={item.mapMode ? `${item.path}-${item.mapMode}` : item.path}
            disablePadding
            sx={{ mb: 0.5, justifyContent: 'center' }}
          >
            <Tooltip title={item.label} placement="right">
              <ListItemButton
                selected={isSelected(item)}
                onClick={() => handleNav(item)}
                sx={{
                  borderRadius: 2,
                  justifyContent: 'center',
                  px: 1.5,
                  minWidth: 0,
                  '&.Mui-selected': {
                    backgroundColor: 'primary.main',
                    color: 'primary.contrastText',
                    '& .MuiListItemIcon-root': { color: 'primary.contrastText' },
                    '&:hover': { backgroundColor: 'primary.dark' },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 0, justifyContent: 'center' }}>{item.icon}</ListItemIcon>
              </ListItemButton>
            </Tooltip>
          </ListItem>
        ))}
      </List>
      <Divider sx={{ width: '100%' }} />
      <Box sx={{ py: 1.5, display: 'flex', justifyContent: 'center' }}>
        <Tooltip title={user?.username ?? 'User'} placement="right">
          <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
            {user?.username?.[0]?.toUpperCase() ?? 'U'}
          </Avatar>
        </Tooltip>
      </Box>
    </Box>
  )

  // Full drawer: iconos + texto
  const fullDrawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          minHeight: '64px !important',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WifiFindIcon color="primary" />
          <Typography variant="h6" fontWeight={700} noWrap>
            Wardrive
          </Typography>
        </Box>
        <Tooltip title="Collapse menu">
          <IconButton onClick={handleDrawerToggle} size="small">
            <ChevronLeftIcon />
          </IconButton>
        </Tooltip>
      </Toolbar>
      <Divider />
      <List sx={{ flexGrow: 1, px: 1, pt: 1 }}>
        {navItems.map((item) => (
          <ListItem key={item.mapMode ? `${item.path}-${item.mapMode}` : item.path} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              selected={isSelected(item)}
              onClick={() => handleNav(item)}
              sx={{
                borderRadius: 2,
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'primary.contrastText',
                  '& .MuiListItemIcon-root': { color: 'primary.contrastText' },
                  '&:hover': { backgroundColor: 'primary.dark' },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
          {user?.username?.[0]?.toUpperCase() ?? 'U'}
        </Avatar>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="body2" fontWeight={600} noWrap>
            {user?.username ?? 'User'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            wardrive-frontend v0.1.0
          </Typography>
        </Box>
      </Box>
    </Box>
  )

  // Ancho efectivo del drawer en desktop
  const desktopDrawerWidth = drawerOpen ? DRAWER_WIDTH : MINI_DRAWER_WIDTH

  const transition = theme.transitions.create(['width', 'margin'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.enteringScreen,
  })

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <CssBaseline />

      {/* AppBar */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { xs: '100%', md: `calc(100% - ${desktopDrawerWidth}px)` },
          ml: { xs: 0, md: `${desktopDrawerWidth}px` },
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          color: 'text.primary',
          transition,
        }}
      >
        <Toolbar>
          {/* Hamburger: on mobile opens overlay drawer; hidden on desktop (toggle lives in drawer) */}
          <IconButton
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { xs: 'flex', md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1, fontWeight: 600 }}>
            Wardriving Contest Platform
          </Typography>
          <Tooltip title={isDarkMode ? 'Light mode' : 'Dark mode'}>
            <IconButton onClick={onToggleTheme} color="inherit">
              {isDarkMode ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Sign out">
            <IconButton onClick={handleLogout} color="inherit" sx={{ ml: 0.5 }}>
              <LogoutIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Mobile drawer (temporary overlay) */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        {fullDrawerContent}
      </Drawer>

      {/* Desktop drawer (persistent — collapses to mini) */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', md: 'block' },
          width: desktopDrawerWidth,
          flexShrink: 0,
          transition,
          '& .MuiDrawer-paper': {
            width: desktopDrawerWidth,
            boxSizing: 'border-box',
            overflowX: 'hidden',
            borderRight: '1px solid',
            borderColor: 'divider',
            transition,
          },
        }}
        open
      >
        {drawerOpen ? fullDrawerContent : miniDrawerContent}
      </Drawer>

      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          minWidth: 0,
          minHeight: '100vh',
          bgcolor: 'background.default',
          transition,
          overflow: 'auto',
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  )
}
