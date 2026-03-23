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
  /** Contiene (icontains) en uploaded_by */
  uploaded_by?: string
  /** ISO 8601: first_seen >= */
  first_seen_after?: string
  /** ISO 8601: first_seen <= */
  first_seen_before?: string
}

function buildPlacesUrl(
  resource: 'wifi-places' | 'lte-places',
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
  return apiFetch<PaginatedPlaces>(buildPlacesUrl('wifi-places', params))
}

export function fetchLtePlaces(params: PlacesListParams): Promise<PaginatedPlaces> {
  return apiFetch<PaginatedPlaces>(buildPlacesUrl('lte-places', params))
}

type KmlKind = 'wifi' | 'lte'

function kmlPath(kind: KmlKind): string {
  return kind === 'wifi' ? '/wardrive/wifi-places/kml/' : '/wardrive/lte-places/kml/'
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

export async function downloadWifiKml(): Promise<void> {
  const blob = await apiFetchBlob(kmlPath('wifi'), { method: 'GET' })
  downloadBlob(blob, 'wifi_scans.kml')
}

export async function downloadLteKml(): Promise<void> {
  const blob = await apiFetchBlob(kmlPath('lte'), { method: 'GET' })
  downloadBlob(blob, 'lte_scans.kml')
}
