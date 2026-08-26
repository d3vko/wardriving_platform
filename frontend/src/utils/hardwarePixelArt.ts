const HARDWARE_PIXELART_BASE = `${import.meta.env.BASE_URL}assets/hardware`

export function slugifyDeviceSource(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_')
}

export function hardwarePixelArtUrl(value: string): string {
  return `${HARDWARE_PIXELART_BASE}/${slugifyDeviceSource(value)}_pixelart.png`
}

export const UNKNOWN_HARDWARE_PIXELART_URL = `${HARDWARE_PIXELART_BASE}/unknown_pixelart.png`
