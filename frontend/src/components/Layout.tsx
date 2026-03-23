import { useState } from 'react'
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
  BarChart as BarChartIcon,
  CloudUpload as CloudUploadIcon,
  Settings as SettingsIcon,
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

const navItems = [
  { label: 'Dashboard', path: '/', icon: <HomeIcon /> },
  { label: 'Wardriving', path: '/wardriving', icon: <WifiFindIcon /> },
  { label: 'Analytics', path: '/analytics', icon: <BarChartIcon /> },
  { label: 'Upload', path: '/upload', icon: <CloudUploadIcon /> },
  { label: 'Settings', path: '/settings', icon: <SettingsIcon /> },
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

  const handleNav = (path: string) => {
    navigate(path)
    if (isMobile) setMobileOpen(false)
  }

  const isSelected = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)

  // Mini drawer: solo iconos con tooltip
  const miniDrawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', alignItems: 'center' }}>
      <Toolbar sx={{ width: '100%', justifyContent: 'center', minHeight: '64px !important' }}>
        <Tooltip title="Abrir menu" placement="right">
          <IconButton onClick={handleDrawerToggle} size="small">
            <MenuIcon />
          </IconButton>
        </Tooltip>
      </Toolbar>
      <Divider sx={{ width: '100%' }} />
      <List sx={{ flexGrow: 1, pt: 1, width: '100%', px: 0.5 }}>
        {navItems.map(({ label, path, icon }) => (
          <ListItem key={path} disablePadding sx={{ mb: 0.5, justifyContent: 'center' }}>
            <Tooltip title={label} placement="right">
              <ListItemButton
                selected={isSelected(path)}
                onClick={() => handleNav(path)}
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
                <ListItemIcon sx={{ minWidth: 0, justifyContent: 'center' }}>{icon}</ListItemIcon>
              </ListItemButton>
            </Tooltip>
          </ListItem>
        ))}
      </List>
      <Divider sx={{ width: '100%' }} />
      <Box sx={{ py: 1.5, display: 'flex', justifyContent: 'center' }}>
        <Tooltip title={user?.username ?? 'Usuario'} placement="right">
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
        <Tooltip title="Colapsar menu">
          <IconButton onClick={handleDrawerToggle} size="small">
            <ChevronLeftIcon />
          </IconButton>
        </Tooltip>
      </Toolbar>
      <Divider />
      <List sx={{ flexGrow: 1, px: 1, pt: 1 }}>
        {navItems.map(({ label, path, icon }) => (
          <ListItem key={path} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              selected={isSelected(path)}
              onClick={() => handleNav(path)}
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
              <ListItemIcon sx={{ minWidth: 36 }}>{icon}</ListItemIcon>
              <ListItemText primary={label} />
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
            {user?.username ?? 'Usuario'}
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
          {/* Hamburger: en mobile abre el drawer overlay; en desktop no aparece (el toggle esta en el drawer) */}
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
          <Tooltip title={isDarkMode ? 'Modo claro' : 'Modo oscuro'}>
            <IconButton onClick={onToggleTheme} color="inherit">
              {isDarkMode ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Cerrar sesion">
            <IconButton onClick={handleLogout} color="inherit" sx={{ ml: 0.5 }}>
              <LogoutIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Drawer mobile (overlay temporal) */}
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

      {/* Drawer desktop (persistent — se comprime a mini) */}
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

      {/* Contenido principal */}
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
