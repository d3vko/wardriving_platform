import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import { maplibreGL } from '@maplibre/maplibre-gl-leaflet'

import 'maplibre-gl/dist/maplibre-gl.css'

/** StyleJSON same-origin (wardrive_proxy). El JSON remoto sigue trayendo URLs absolutas; se reescriben abajo. */
export const AMERICANA_STYLE_URL = '/map-americana/style.json'

const AMERICANA_ATTRIBUTION =
  '<a href="https://tiles.openstreetmap.us/">Tiles by OSM US</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://openmaptiles.org/">OpenMapTiles</a> · <a href="https://github.com/osm-americana/openstreetmap-americana">Americana</a>'

/** Orígenes de Americana / OSM US → paths de nginx (antes de location / de Metabase). */
const NGINX_AMERICANA_PREFIXES: [string, string][] = [
  ['https://americanamap.org/style.json', '/map-americana/style.json'],
  ['https://americanamap.org/sprites/', '/map-americana/sprites/'],
  ['https://font.americanamap.org/', '/map-americana/fonts/'],
  ['https://tiles.openstreetmap.us/', '/map-americana/osm-us/'],
]

export function rewriteAmericanaUrl(url: string): string {
  for (const [remote, local] of NGINX_AMERICANA_PREFIXES) {
    if (url === remote || url.startsWith(remote)) {
      return local + url.slice(remote.length)
    }
  }
  return url
}

function styleUrl(): string {
  const fromEnv = import.meta.env.VITE_MAPLIBRE_STYLE_URL?.trim()
  return fromEnv || AMERICANA_STYLE_URL
}

export default function AmericanaBasemap() {
  const map = useMap()
  const url = styleUrl()

  useEffect(() => {
    const layer = maplibreGL({
      style: url,
      attributionControl: { compact: true, customAttribution: AMERICANA_ATTRIBUTION },
      transformRequest: (resourceUrl) => ({ url: rewriteAmericanaUrl(resourceUrl) }),
    })
    layer.addTo(map)
    return () => {
      map.removeLayer(layer)
    }
  }, [map, url])

  return null
}
