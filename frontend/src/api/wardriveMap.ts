import {
  ApiError,
  getTokens,
  refreshAccessTokenOrThrow,
} from '@/api/client'

export type WardrivingPlace = {
  mac: string
  vendor: string
  ssid: string
  auth_mode: string
  device_source: string
  signal_streng: string
  uploaded_by: string
  type: string
  current_latitude: number
  current_longitude: number
}

export type PaginatedPlaces = {
  count: number
  next: string | null
  previous: string | null
  results: WardrivingPlace[]
}

export type PlacesListParams = {
  page?: number
  page_size?: number
  /** Case-insensitive substring match on uploaded_by */
  uploaded_by?: string
  /** ISO 8601: first_seen >= (normalized server-side) */
  first_seen_after?: string
  /** ISO 8601: first_seen <= (normalized server-side) */
  first_seen_before?: string
}

function wsScheme(): string {
  return window.location.protocol === 'https:' ? 'wss:' : 'ws:'
}

function randomId(): string {
  // Algunos entornos no traen `crypto.randomUUID` (p.ej. navegadores viejos o
  // ejecución fuera del browser). Usamos fallback seguro.
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(16)
    crypto.getRandomValues(bytes)
    // UUID v4: set version (4) and variant (10xx)
    bytes[6] = (bytes[6] & 0x0f) | 0x40
    bytes[8] = (bytes[8] & 0x3f) | 0x80
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
  }

  // Fallback último recurso (no criptográficamente fuerte)
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function wardriveListWsPath(resource: 'wifi' | 'lte'): string {
  return `/wardriving/v1/wardrive/${resource}/`
}

function wardriveKmlWsPath(kind: 'wifi' | 'lte'): string {
  return `/wardriving/v1/wardrive/${kind}/kml/`
}

function buildWsUrl(path: string, token: string): string {
  const q = new URLSearchParams({ token })
  return `${wsScheme()}//${window.location.host}${path}?${q.toString()}`
}

function listPayloadFromParams(params: PlacesListParams, id: string): Record<string, unknown> {
  const out: Record<string, unknown> = { id }
  if (params.page != null) out.page = params.page
  if (params.page_size != null) out.page_size = params.page_size
  if (params.uploaded_by) out.uploaded_by = params.uploaded_by
  if (params.first_seen_after) out.first_seen_after = params.first_seen_after
  if (params.first_seen_before) out.first_seen_before = params.first_seen_before
  return out
}

async function getAccessTokenForWs(): Promise<string> {
  const t = getTokens()
  if (t?.access) return t.access
  return refreshAccessTokenOrThrow()
}

function fetchPlacesViaWs(
  resource: 'wifi' | 'lte',
  params: PlacesListParams,
  accessToken: string,
): Promise<PaginatedPlaces> {
  return new Promise((resolve, reject) => {
    const path = wardriveListWsPath(resource)
    const ws = new WebSocket(buildWsUrl(path, accessToken))
    const id = randomId()
    const payload = listPayloadFromParams(params, id)
    const timeoutMs = 90_000
    let settled = false
    let retried401 = false

    const timer = window.setTimeout(() => {
      if (settled) return
      settled = true
      ws.close()
      reject(new Error('Wardriving map request timed out.'))
    }, timeoutMs)

    const finish = (fn: () => void) => {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      fn()
    }

    ws.onopen = () => {
      ws.send(JSON.stringify(payload))
    }

    ws.onmessage = (ev) => {
      if (typeof ev.data !== 'string') return
      let msg: {
        id?: string
        ok?: boolean
        data?: PaginatedPlaces
        status?: number
        detail?: unknown
      }
      try {
        msg = JSON.parse(ev.data) as typeof msg
      } catch {
        finish(() => reject(new Error('Invalid WebSocket response')))
        ws.close()
        return
      }
      if (msg.id !== id) return
      finish(() => {
        ws.close()
        if (msg.ok && msg.data) {
          resolve(msg.data)
        } else {
          reject(
            new ApiError(
              msg.status ?? 500,
              String(msg.detail ?? 'Request failed'),
              msg,
            ),
          )
        }
      })
    }

    ws.onerror = () => {
      finish(() => reject(new Error('WebSocket connection error')))
    }

    ws.onclose = (ev) => {
      if (settled) return
      if (ev.code === 4001 && !retried401) {
        retried401 = true
        void refreshAccessTokenOrThrow()
          .then((newToken) =>
            fetchPlacesViaWs(resource, params, newToken).then(resolve, reject),
          )
          .catch(reject)
        return
      }
      finish(() =>
        reject(
          new Error(
            ev.reason || `WebSocket closed (${ev.code})`,
          ),
        ),
      )
    }
  })
}

export async function fetchWifiPlaces(
  params: PlacesListParams,
): Promise<PaginatedPlaces> {
  const token = await getAccessTokenForWs()
  return fetchPlacesViaWs('wifi', params, token)
}

export async function fetchLtePlaces(
  params: PlacesListParams,
): Promise<PaginatedPlaces> {
  const token = await getAccessTokenForWs()
  return fetchPlacesViaWs('lte', params, token)
}

export type KmlDownloadParams = {
  first_seen_after: string
  first_seen_before: string
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function downloadKmlViaWs(
  kind: 'wifi' | 'lte',
  params: KmlDownloadParams,
  accessToken: string,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const path = wardriveKmlWsPath(kind)
    const ws = new WebSocket(buildWsUrl(path, accessToken))
    ws.binaryType = 'blob'
    const id = randomId()
    const payload = {
      id,
      first_seen_after: params.first_seen_after,
      first_seen_before: params.first_seen_before,
    }
    let meta: { filename?: string } | null = null
    let retried401 = false
    let settled = false
    const timer = window.setTimeout(() => {
      if (settled) return
      settled = true
      ws.close()
      reject(new Error('KML download timed out.'))
    }, 300_000)

    const finish = (fn: () => void) => {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      fn()
    }

    ws.onopen = () => {
      ws.send(JSON.stringify(payload))
    }

    ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        let msg: {
          id?: string
          ok?: boolean
          type?: string
          filename?: string
          status?: number
          detail?: unknown
        }
        try {
          msg = JSON.parse(ev.data) as typeof msg
        } catch {
          finish(() => reject(new Error('Invalid KML response')))
          ws.close()
          return
        }
        if (msg.id !== id) return
        if (!msg.ok) {
          finish(() => {
            ws.close()
            reject(
              new ApiError(
                msg.status ?? 400,
                String(msg.detail ?? 'KML export failed'),
                msg,
              ),
            )
          })
          return
        }
        meta = { filename: msg.filename }
        return
      }
      const blob =
        ev.data instanceof Blob
          ? ev.data
          : new Blob([ev.data as ArrayBuffer], {
              type: 'application/vnd.google-earth.kml+xml',
            })
      const name =
        meta?.filename ?? (kind === 'wifi' ? 'wifi_scans.kml' : 'lte_scans.kml')
      finish(() => {
        downloadBlob(blob, name)
        ws.close()
        resolve()
      })
    }

    ws.onerror = () => {
      finish(() => reject(new Error('WebSocket error during KML download')))
    }

    ws.onclose = (ev) => {
      if (settled) return
      if (ev.code === 4001 && !retried401) {
        retried401 = true
        void refreshAccessTokenOrThrow()
          .then((t) => downloadKmlViaWs(kind, params, t).then(resolve, reject))
          .catch(reject)
        return
      }
      finish(() =>
        reject(new Error(ev.reason || `WebSocket closed (${ev.code})`)),
      )
    }
  })
}

export async function downloadWifiKml(params: KmlDownloadParams): Promise<void> {
  const token = await getAccessTokenForWs()
  return downloadKmlViaWs('wifi', params, token)
}

export async function downloadLteKml(params: KmlDownloadParams): Promise<void> {
  const token = await getAccessTokenForWs()
  return downloadKmlViaWs('lte', params, token)
}
