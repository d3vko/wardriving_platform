import { apiFetch, apiFetchBlob, apiFetchBlobWithMeta } from '@/api/client'

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
  /** Exact match on uploaded_by (scoped server-side to the authenticated user) */
  uploaded_by?: string
  /** ISO 8601: first_seen >= (normalized server-side) */
  first_seen_after?: string
  /** ISO 8601: first_seen <= (normalized server-side) */
  first_seen_before?: string
}

function listQueryFromParams(params: PlacesListParams): string {
  const q = new URLSearchParams()
  if (params.page != null) q.set('page', String(params.page))
  if (params.page_size != null) q.set('page_size', String(params.page_size))
  if (params.uploaded_by) q.set('uploaded_by', params.uploaded_by)
  if (params.first_seen_after) q.set('first_seen_after', params.first_seen_after)
  if (params.first_seen_before) q.set('first_seen_before', params.first_seen_before)
  const qs = q.toString()
  return qs ? `?${qs}` : ''
}

export function fetchWifiPlaces(params: PlacesListParams): Promise<PaginatedPlaces> {
  return apiFetch<PaginatedPlaces>(`/wardrive/wifi/${listQueryFromParams(params)}`)
}

export function fetchLtePlaces(params: PlacesListParams): Promise<PaginatedPlaces> {
  return apiFetch<PaginatedPlaces>(`/wardrive/lte/${listQueryFromParams(params)}`)
}

export type KmlDownloadParams = {
  first_seen_after: string
  first_seen_before: string
}

function kmlQueryFromParams(params: KmlDownloadParams): string {
  const q = new URLSearchParams({
    first_seen_after: params.first_seen_after,
    first_seen_before: params.first_seen_before,
  })
  return `?${q.toString()}`
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

/** Long-running KML export over HTTP (streamed server-side; avoids WS idle timeouts). */
export async function downloadWifiKml(
  params: KmlDownloadParams,
): Promise<{ isZip: boolean }> {
  const { blob, contentType } = await apiFetchBlobWithMeta(
    `/wardrive/wifi/kml/${kmlQueryFromParams(params)}`,
  )
  const isZip = contentType?.includes('zip') ?? false
  downloadBlob(blob, isZip ? 'wifi_scans.zip' : 'wifi_scans.kml')
  return { isZip }
}

export async function downloadLteKml(params: KmlDownloadParams): Promise<void> {
  const blob = await apiFetchBlob(`/wardrive/lte/kml/${kmlQueryFromParams(params)}`)
  downloadBlob(blob, 'lte_scans.kml')
}
