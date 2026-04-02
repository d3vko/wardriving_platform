import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import { login as apiLogin, register as apiRegister } from '@/api/auth'
import { API_BASE, getTokens, setTokens, clearTokens } from '@/api/client'

interface User {
  username: string
  id?: number
  email?: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string, passwordConfirm: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
  } catch {
    return null
  }
}

function getUsernameFromToken(token: string): string {
  const payload = decodeJwtPayload(token)
  return (payload?.username ?? payload?.user_id ?? 'Usuario') as string
}

function getExpiresInMs(token: string): number {
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return 0
  return (payload.exp as number) * 1000 - Date.now() - 30_000
}

function buildInitialState(): AuthState {
  const tokens = getTokens()
  if (!tokens?.access) return { user: null, accessToken: null, isAuthenticated: false }

  const payload = decodeJwtPayload(tokens.access)
  if (!payload?.exp || (payload.exp as number) * 1000 < Date.now()) {
    clearTokens()
    return { user: null, accessToken: null, isAuthenticated: false }
  }

  const username = getUsernameFromToken(tokens.access)
  return {
    user: { username },
    accessToken: tokens.access,
    isAuthenticated: true,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(buildInitialState)
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const scheduleRefresh = useCallback((accessToken: string) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    const ms = getExpiresInMs(accessToken)
    if (ms <= 0) return
    refreshTimerRef.current = setTimeout(async () => {
      const tokens = getTokens()
      if (!tokens?.refresh) return
      try {
        const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh: tokens.refresh }),
        })
        if (res.ok) {
          const data = await res.json()
          setTokens(data.access, tokens.refresh)
          const username = getUsernameFromToken(data.access)
          setState((prev) => ({
            ...prev,
            accessToken: data.access,
            user: { ...prev.user, username },
          }))
          scheduleRefresh(data.access)
        }
      } catch {
        /* silent */
      }
    }, ms)
  }, [])

  useEffect(() => {
    if (state.accessToken) scheduleRefresh(state.accessToken)
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    }
  }, [state.accessToken, scheduleRefresh])

  useEffect(() => {
    const handler = () => {
      clearTokens()
      setState({ user: null, accessToken: null, isAuthenticated: false })
    }
    window.addEventListener('wardrive:logout', handler)
    return () => window.removeEventListener('wardrive:logout', handler)
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const data = await apiLogin(username, password)
    setTokens(data.access, data.refresh)
    setState({
      user: { username: data.username || username },
      accessToken: data.access,
      isAuthenticated: true,
    })
    scheduleRefresh(data.access)
  }, [scheduleRefresh])

  const register = useCallback(async (
    username: string,
    email: string,
    password: string,
    passwordConfirm: string,
  ) => {
    const data = await apiRegister(username, email, password, passwordConfirm)
    setTokens(data.tokens.access, data.tokens.refresh)
    setState({
      user: { username: data.user.username, id: data.user.id, email: data.user.email },
      accessToken: data.tokens.access,
      isAuthenticated: true,
    })
    scheduleRefresh(data.tokens.access)
  }, [scheduleRefresh])

  const logout = useCallback(() => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    clearTokens()
    setState({ user: null, accessToken: null, isAuthenticated: false })
  }, [])

  const value = useMemo(
    () => ({ ...state, login, register, logout }),
    [state, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
