import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ConfigProvider, theme as antdTheme } from 'antd'
import { getAntdTheme, type ColorMode } from '@/theme'

import 'antd/dist/reset.css'
import '@/app.css'

const STORAGE_KEY = 'wardrive-color-mode'

function getInitialMode(): ColorMode {
  const stored = localStorage.getItem(STORAGE_KEY) as ColorMode | null
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

interface ThemeModeContextValue {
  isDarkMode: boolean
  toggleTheme: () => void
}

const ThemeModeContext = createContext<ThemeModeContextValue | null>(null)

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ColorMode>(getInitialMode)

  const toggleTheme = () => {
    setMode((prev) => {
      const next = prev === 'light' ? 'dark' : 'light'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }

  const theme = useMemo(() => {
    const base = getAntdTheme(mode)
    const algorithms =
      mode === 'dark'
        ? [antdTheme.darkAlgorithm, antdTheme.compactAlgorithm]
        : [antdTheme.defaultAlgorithm, antdTheme.compactAlgorithm]
    return { ...base, algorithm: algorithms }
  }, [mode])

  return (
    <ThemeModeContext.Provider value={{ isDarkMode: mode === 'dark', toggleTheme }}>
      <ConfigProvider theme={theme}>{children}</ConfigProvider>
    </ThemeModeContext.Provider>
  )
}

export function useThemeMode(): ThemeModeContextValue {
  const ctx = useContext(ThemeModeContext)
  if (!ctx) throw new Error('useThemeMode must be used within ThemeModeProvider')
  return ctx
}
