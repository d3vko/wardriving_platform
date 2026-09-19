import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import { maplibreGL } from '@maplibre/maplibre-gl-leaflet'

import 'maplibre-gl/dist/maplibre-gl.css'

/** OSM Americana StyleJSON (MapLibre). Metabase no puede usar este URL: solo acepta PNG XYZ. */
export const AMERICANA_STYLE_URL = 'https://americanamap.org/style.json'

const AMERICANA_ATTRIBUTION =
  '<a href="https://tiles.openstreetmap.us/">Tiles by OSM US</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://openmaptiles.org/">OpenMapTiles</a> · <a href="https://github.com/osm-americana/openstreetmap-americana">Americana</a>'

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
    })
    layer.addTo(map)
    return () => {
      map.removeLayer(layer)
    }
  }, [map, url])

  return null
}
