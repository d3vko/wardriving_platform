import { apiFetch, apiFetchBlob } from '@/api/client'

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

function buildPlacesUrl(
  resource: 'wifi' | 'lte',
  params: PlacesListParams,
): string {
  const sp = new URLSearchParams()
  if (params.page != null) sp.set('page', String(params.page))
  if (params.page_size != null) sp.set('page_size', String(params.page_size))
  if (params.uploaded_by) sp.set('uploaded_by', params.uploaded_by)
  if (params.first_seen_after) sp.set('first_seen_after', params.first_seen_after)
  if (params.first_seen_before) sp.set('first_seen_before', params.first_seen_before)
  const q = sp.toString()
  return `/wardrive/${resource}/${q ? `?${q}` : ''}`
}

export function fetchWifiPlaces(params: PlacesListParams): Promise<PaginatedPlaces> {
  return apiFetch<PaginatedPlaces>(buildPlacesUrl('wifi', params))
}

export function fetchLtePlaces(params: PlacesListParams): Promise<PaginatedPlaces> {
  return apiFetch<PaginatedPlaces>(buildPlacesUrl('lte', params))
}

type KmlKind = 'wifi' | 'lte'

/** Required query params for KML export (the API returns 400 if either is missing). */
export type KmlDownloadParams = {
  first_seen_after: string
  first_seen_before: string
}

function kmlPath(kind: KmlKind, params: KmlDownloadParams): string {
  const base = kind === 'wifi' ? '/wardrive/wifi/kml/' : '/wardrive/lte/kml/'
  const sp = new URLSearchParams()
  sp.set('first_seen_after', params.first_seen_after)
  sp.set('first_seen_before', params.first_seen_before)
  return `${base}?${sp.toString()}`
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

export async function downloadWifiKml(params: KmlDownloadParams): Promise<void> {
  const blob = await apiFetchBlob(kmlPath('wifi', params), { method: 'GET' })
  downloadBlob(blob, 'wifi_scans.kml')
}

export async function downloadLteKml(params: KmlDownloadParams): Promise<void> {
  const blob = await apiFetchBlob(kmlPath('lte', params), { method: 'GET' })
  downloadBlob(blob, 'lte_scans.kml')
}
