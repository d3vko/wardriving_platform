const ANALYTICS_API = (import.meta.env.VITE_ANALYTICS_API_URL || '/analytics/api').replace(
  /\/$/,
  '',
)

export const ANALYTICS_DEFAULTS = {
  startDate:
    import.meta.env.VITE_ANALYTICS_DEFAULT_START_DATE || '2025-01-01T00:00:00-06:00',
  endDate:
    import.meta.env.VITE_ANALYTICS_DEFAULT_END_DATE || '2026-05-30T00:00:00-06:00',
}

export type AnalyticsScope = 'self-analytics' | 'global-analytics'

export interface AnalyticsQueryParams {
  first_seen_start: string
  first_seen_end: string
  author?: string
}

export interface AnalyticsRow {
  [key: string]: string | number | null | undefined
}

export interface AnalyticsResult {
  rows: AnalyticsRow[]
  fields: { name: string; type: string }[]
}

interface RawAnalyticsResult {
  fields: { name: string; type: string }[]
  rows: (string | number | null)[][]
  rowCount?: number
}

function toNamedRows(raw: RawAnalyticsResult): AnalyticsResult {
  const names = raw.fields.map((f) => f.name)
  return {
    fields: raw.fields,
    rows: raw.rows.map((row) => {
      const obj: AnalyticsRow = {}
      names.forEach((name, i) => {
        obj[name] = row[i] ?? null
      })
      return obj
    }),
  }
}

export class AnalyticsError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'AnalyticsError'
  }
}

export async function fetchAnalyticsQuery(
  scope: AnalyticsScope,
  query: string,
  params: AnalyticsQueryParams,
): Promise<AnalyticsResult> {
  const searchParams = new URLSearchParams({
    first_seen_start: params.first_seen_start,
    first_seen_end: params.first_seen_end,
  })
  if (params.author) {
    searchParams.set('author', params.author)
  }

  const url = `${ANALYTICS_API}/queries/${scope}/${query}?${searchParams.toString()}`
  const res = await fetch(url)

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new AnalyticsError(res.status, text)
  }

  const raw: RawAnalyticsResult = await res.json()
  return toNamedRows(raw)
}

export async function fetchAuthModes(
  scope: AnalyticsScope,
  params: AnalyticsQueryParams,
): Promise<AnalyticsResult> {
  return fetchAnalyticsQuery(scope, 'auth-modes', params)
}

export async function fetchByDevice(
  scope: AnalyticsScope,
  params: AnalyticsQueryParams,
): Promise<AnalyticsResult> {
  return fetchAnalyticsQuery(scope, 'by-device', params)
}

export async function fetchBySignal(
  scope: AnalyticsScope,
  params: AnalyticsQueryParams,
): Promise<AnalyticsResult> {
  return fetchAnalyticsQuery(scope, 'by-signal', params)
}

export async function fetchByVendor(
  scope: AnalyticsScope,
  params: AnalyticsQueryParams,
): Promise<AnalyticsResult> {
  return fetchAnalyticsQuery(scope, 'by-vendor', params)
}

export async function fetchByAuthor(
  params: Omit<AnalyticsQueryParams, 'author'>,
): Promise<AnalyticsResult> {
  return fetchAnalyticsQuery('global-analytics', 'by-author', params)
}

export async function fetchDetail(
  scope: AnalyticsScope,
  params: AnalyticsQueryParams,
): Promise<AnalyticsResult> {
  return fetchAnalyticsQuery(scope, 'detail', params)
}
