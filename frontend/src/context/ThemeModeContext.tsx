import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { getTheme } from '@/theme'

type ColorMode = 'light' | 'dark'

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

  const theme = useMemo(() => getTheme(mode), [mode])

  return (
    <ThemeModeContext.Provider value={{ isDarkMode: mode === 'dark', toggleTheme }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  )
}

export function useThemeMode(): ThemeModeContextValue {
  const ctx = useContext(ThemeModeContext)
  if (!ctx) throw new Error('useThemeMode must be used within ThemeModeProvider')
  return ctx
}
