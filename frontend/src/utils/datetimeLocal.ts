/** Converts ISO datetime to `<input type="date">` value (browser local date). */
export function isoToDateInputValue(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function clampDate(date: Date, minDate: Date, maxDate: Date): Date {
  if (date.getTime() < minDate.getTime()) return new Date(minDate)
  if (date.getTime() > maxDate.getTime()) return new Date(maxDate)
  return date
}

export function dateInputToDayRangeIso(
  fromDate: string,
  toDate: string,
  bounds?: { minIso?: string; maxIso?: string },
): { startIso: string; endIso: string; fromDate: string; toDate: string } {
  const parsedFrom = new Date(`${fromDate}T00:00:00`)
  const parsedTo = new Date(`${toDate}T00:00:00`)
  const minDate = new Date(bounds?.minIso ?? '1970-01-01T00:00:00Z')
  const maxDate = new Date(bounds?.maxIso ?? '9999-12-31T23:59:59Z')

  const normalizedFrom = Number.isNaN(parsedFrom.getTime()) ? new Date(minDate) : parsedFrom
  const normalizedTo = Number.isNaN(parsedTo.getTime()) ? new Date(maxDate) : parsedTo
  const orderedFrom = normalizedFrom.getTime() <= normalizedTo.getTime() ? normalizedFrom : normalizedTo
  const orderedTo = normalizedFrom.getTime() <= normalizedTo.getTime() ? normalizedTo : normalizedFrom

  const dayStart = new Date(orderedFrom)
  dayStart.setHours(0, 0, 0, 0)
  const dayEnd = new Date(orderedTo)
  dayEnd.setHours(23, 59, 59, 999)

  const minStart = new Date(minDate)
  minStart.setHours(0, 0, 0, 0)
  const maxEnd = new Date(maxDate)
  maxEnd.setHours(23, 59, 59, 999)

  const clampedStart = clampDate(dayStart, minStart, maxEnd)
  const clampedEnd = clampDate(dayEnd, minStart, maxEnd)

  return {
    startIso: clampedStart.toISOString(),
    endIso: clampedEnd.toISOString(),
    fromDate: isoToDateInputValue(clampedStart.toISOString()),
    toDate: isoToDateInputValue(clampedEnd.toISOString()),
  }
}
