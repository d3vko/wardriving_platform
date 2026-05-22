import { useMemo, useState } from 'react'
import { ThemeProvider } from '@mui/material/styles'
import { CssBaseline } from '@mui/material'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { getTheme } from '@/theme'
import { AuthProvider } from '@/context/AuthContext'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'
import Home from '@/pages/Home'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import ForgotPassword from '@/pages/ForgotPassword'
import ResetPassword from '@/pages/ResetPassword'
import Upload from '@/pages/Upload'
import Analytics from '@/pages/Analytics'
import WardrivingMap from '@/pages/WardrivingMap'
import KmlDownloads from '@/pages/KmlDownloads'

type ColorMode = 'light' | 'dark'

const STORAGE_KEY = 'wardrive-color-mode'

function getInitialMode(): ColorMode {
  const stored = localStorage.getItem(STORAGE_KEY) as ColorMode | null
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export default function App() {
  const [mode, setMode] = useState<ColorMode>(getInitialMode)

  const toggleTheme = () => {
    setMode((prev) => {
      const next = prev === 'light' ? 'dark' : 'light'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }

  const theme = useMemo(() => getTheme(mode), [mode])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter basename="/ctf">
          <Routes>
            {/* Rutas publicas (sin Layout) */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Rutas protegidas (con Layout) */}
            <Route
              element={
                <ProtectedRoute>
                  <Layout onToggleTheme={toggleTheme} isDarkMode={mode === 'dark'} />
                </ProtectedRoute>
              }
            >
              <Route index element={<Home />} />
              <Route path="map" element={<WardrivingMap />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="upload" element={<Upload />} />
              <Route path="downloads" element={<KmlDownloads />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
