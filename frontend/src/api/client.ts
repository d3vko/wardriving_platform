export const API_BASE = '/wardriving/v1'

const STORAGE_KEY = 'wardrive-auth'

function getTokens(): { access: string; refresh: string } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function setTokens(access: string, refresh: string): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ access, refresh }))
}

function clearTokens(): void {
  localStorage.removeItem(STORAGE_KEY)
}

async function doRefresh(refresh: string): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!res.ok) return null
    const data = await res.json()
    const tokens = getTokens()
    if (tokens) setTokens(data.access, tokens.refresh)
    return data.access as string
  } catch {
    return null
  }
}

/** Use before WebSocket connect if access may be invalid; same refresh as apiFetch. */
export async function refreshAccessTokenOrThrow(): Promise<string> {
  const tokens = getTokens()
  if (!tokens?.refresh) {
    clearTokens()
    window.dispatchEvent(new CustomEvent('wardrive:logout'))
    throw new ApiError(401, 'Session expired. Please sign in again.')
  }
  const access = await doRefresh(tokens.refresh)
  if (!access) {
    clearTokens()
    window.dispatchEvent(new CustomEvent('wardrive:logout'))
    throw new ApiError(401, 'Session expired. Please sign in again.')
  }
  return access
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public data?: unknown,
  ) {
    super(detail)
    this.name = 'ApiError'
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let detail = res.statusText
  try {
    const json = await res.json()
    detail =
      json?.detail ??
      json?.non_field_errors?.[0] ??
      Object.values(json).flat().join(' ') ??
      detail
  } catch {
    /* ignore */
  }
  return new ApiError(res.status, String(detail))
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit & { skipAuth?: boolean } = {},
): Promise<T> {
  const { skipAuth = false, ...init } = options
  const url = `${API_BASE}${path}`

  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (!skipAuth) {
    const tokens = getTokens()
    if (tokens?.access) {
      headers.set('Authorization', `Bearer ${tokens.access}`)
    }
  }

  let res = await fetch(url, { ...init, headers })

  if (res.status === 401 && !skipAuth) {
    const tokens = getTokens()
    if (tokens?.refresh) {
      const newAccess = await doRefresh(tokens.refresh)
      if (newAccess) {
        headers.set('Authorization', `Bearer ${newAccess}`)
        res = await fetch(url, { ...init, headers })
      } else {
        clearTokens()
        window.dispatchEvent(new CustomEvent('wardrive:logout'))
        throw new ApiError(401, 'Session expired. Please sign in again.')
      }
    }
  }

  if (!res.ok) throw await parseError(res)

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function apiFetchBlob(
  path: string,
  options: RequestInit & { skipAuth?: boolean } = {},
): Promise<Blob> {
  const { skipAuth = false, ...init } = options
  const url = `${API_BASE}${path}`
  const headers = new Headers(init.headers)

  if (!skipAuth) {
    const tokens = getTokens()
    if (tokens?.access) {
      headers.set('Authorization', `Bearer ${tokens.access}`)
    }
  }

  let res = await fetch(url, { ...init, headers })

  if (res.status === 401 && !skipAuth) {
    const tokens = getTokens()
    if (tokens?.refresh) {
      const newAccess = await doRefresh(tokens.refresh)
      if (newAccess) {
        headers.set('Authorization', `Bearer ${newAccess}`)
        res = await fetch(url, { ...init, headers })
      } else {
        clearTokens()
        window.dispatchEvent(new CustomEvent('wardrive:logout'))
        throw new ApiError(401, 'Session expired. Please sign in again.')
      }
    }
  }

  if (!res.ok) throw await parseError(res)
  return res.blob()
}

export { getTokens, setTokens, clearTokens }
