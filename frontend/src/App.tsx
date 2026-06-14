import { useMemo } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { ThemeModeProvider } from '@/context/ThemeModeContext'
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

function AppRoutes() {
  const router = useMemo(
    () =>
      createBrowserRouter(
        [
          { path: '/login', element: <Login /> },
          { path: '/register', element: <Register /> },
          { path: '/forgot-password', element: <ForgotPassword /> },
          { path: '/reset-password', element: <ResetPassword /> },
          {
            element: (
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            ),
            children: [
              { index: true, element: <Home /> },
              { path: 'map', element: <WardrivingMap /> },
              { path: 'analytics', element: <Analytics /> },
              { path: 'upload', element: <Upload /> },
              { path: 'downloads', element: <KmlDownloads /> },
              { path: '*', element: <Navigate to="/" replace /> },
            ],
          },
        ],
        { basename: '/ctf' },
      ),
    [],
  )

  return <RouterProvider router={router} />
}

export default function App() {
  return (
    <ThemeModeProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ThemeModeProvider>
  )
}
