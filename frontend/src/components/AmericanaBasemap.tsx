import { useEffect, useRef } from 'react'
import {
  GeoJSONSource,
  LngLatBounds,
  Map as MaplibreMap,
  MapLayerMouseEvent,
  NavigationControl,
  Popup,
  setWorkerUrl,
} from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

import type { WardrivingPlace } from '@/api/wardriveMap'

import 'maplibre-gl/dist/maplibre-gl.css'

setWorkerUrl(maplibreWorkerUrl)

/** StyleJSON same-origin (wardrive_proxy). Teselas vectoriales OSM US van directo del browser. */
export const AMERICANA_STYLE_URL = '/map-americana/style.json'

const AMERICANA_ATTRIBUTION =
  '<a href="https://tiles.openstreetmap.us/">Tiles by OSM US</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://openmaptiles.org/">OpenMapTiles</a> · <a href="https://github.com/osm-americana/openstreetmap-americana">Americana</a>'

const DEFAULT_CENTER: [number, number] = [-3.7038, 40.4168]
const DEFAULT_ZOOM = 6
const SOURCE_ID = 'wardrive-places'
const LAYER_ID = 'wardrive-places-circles'

const NGINX_AMERICANA_PREFIXES: [string, string][] = [
  ['https://americanamap.org/style.json', '/map-americana/style.json'],
  ['https://americanamap.org/sprites/', '/map-americana/sprites/'],
  ['https://font.americanamap.org/', '/map-americana/fonts/'],
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

function isPlottable(p: WardrivingPlace): boolean {
  return (
    p.current_latitude != null &&
    p.current_longitude != null &&
    !(p.current_latitude === 0 && p.current_longitude === 0)
  )
}

function esc(value: string): string {
  return value.replace(/[&<>"']/g, (ch) => {
    switch (ch) {
      case '&':
        return '&amp;'
      case '<':
        return '&lt;'
      case '>':
        return '&gt;'
      case '"':
        return '&quot;'
      default:
        return '&#39;'
    }
  })
}

function placesToGeoJSON(places: WardrivingPlace[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: places.filter(isPlottable).map((p, i) => ({
      type: 'Feature' as const,
      id: i,
      geometry: {
        type: 'Point' as const,
        coordinates: [p.current_longitude, p.current_latitude],
      },
      properties: {
        vendor: p.vendor || '—',
        mac: p.mac || '—',
        ssid: p.ssid || '—',
        signal: p.signal_streng || '—',
        type: p.type || '—',
        auth: p.auth_mode || '—',
        device: p.device_source || '—',
        uploaded: p.uploaded_by || '—',
      },
    })),
  }
}

function fitPlaces(map: MaplibreMap, places: WardrivingPlace[]) {
  const pts = places.filter(isPlottable)
  if (pts.length === 0) {
    map.jumpTo({ center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM })
    return
  }
  const bounds = new LngLatBounds()
  for (const p of pts) {
    bounds.extend([p.current_longitude, p.current_latitude])
  }
  map.fitBounds(bounds, { padding: 48, maxZoom: 16, duration: 0 })
}

function ensurePlacesLayer(map: MaplibreMap) {
  if (map.getSource(SOURCE_ID)) return
  map.addSource(SOURCE_ID, {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })
  map.addLayer({
    id: LAYER_ID,
    type: 'circle',
    source: SOURCE_ID,
    paint: {
      'circle-radius': 8,
      'circle-opacity': 0.65,
      'circle-stroke-width': 1,
      'circle-stroke-color': [
        'match',
        ['get', 'signal'],
        'Excellent',
        '#15803d',
        'Good',
        '#16a34a',
        'Fair',
        '#c2410c',
        'Weak',
        '#b91c1c',
        '#B026FF',
      ],
      'circle-color': [
        'match',
        ['get', 'signal'],
        'Excellent',
        '#15803d',
        'Good',
        '#16a34a',
        'Fair',
        '#c2410c',
        'Weak',
        '#b91c1c',
        '#B026FF',
      ],
    },
  })
}

function popupHtml(props: Record<string, unknown>): string {
  const g = (k: string) => esc(String(props[k] ?? '—'))
  return `<div style="min-width:200px">
    <strong>${g('vendor')}</strong>
    <div><strong>MAC / ID:</strong> ${g('mac')}</div>
    <div><strong>SSID:</strong> ${g('ssid')}</div>
    <div><strong>Signal:</strong> ${g('signal')}</div>
    <div><strong>Type:</strong> ${g('type')} · <strong>Auth:</strong> ${g('auth')}</div>
    <div style="opacity:.7">${g('device')} · ${g('uploaded')}</div>
  </div>`
}

type AmericanaMapProps = {
  places: WardrivingPlace[]
}

export default function AmericanaBasemap({ places }: AmericanaMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MaplibreMap | null>(null)
  const placesRef = useRef(places)
  const popupRef = useRef<Popup | null>(null)
  placesRef.current = places

  useEffect(() => {
    const el = containerRef.current
    if (!el || mapRef.current) return

    const map = new MaplibreMap({
      container: el,
      style: styleUrl(),
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      attributionControl: { compact: true, customAttribution: AMERICANA_ATTRIBUTION },
      transformRequest: (resourceUrl: string) => ({ url: rewriteAmericanaUrl(resourceUrl) }),
    })
    map.addControl(new NavigationControl({ showCompass: false }), 'top-left')
    mapRef.current = map

    const sync = () => {
      ensurePlacesLayer(map)
      const src = map.getSource(SOURCE_ID) as GeoJSONSource
      src.setData(placesToGeoJSON(placesRef.current))
      fitPlaces(map, placesRef.current)
    }

    map.on('load', sync)

    map.on('click', LAYER_ID, (e: MapLayerMouseEvent) => {
      const f = e.features?.[0]
      if (!f?.geometry || f.geometry.type !== 'Point') return
      const [lng, lat] = f.geometry.coordinates
      popupRef.current?.remove()
      popupRef.current = new Popup({ closeButton: true, maxWidth: '280px' })
        .setLngLat([lng, lat])
        .setHTML(popupHtml((f.properties ?? {}) as Record<string, unknown>))
        .addTo(map)
    })
    map.on('mouseenter', LAYER_ID, () => {
      map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', LAYER_ID, () => {
      map.getCanvas().style.cursor = ''
    })

    const ro = new ResizeObserver(() => map.resize())
    ro.observe(el)

    return () => {
      ro.disconnect()
      popupRef.current?.remove()
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map?.isStyleLoaded()) return
    const src = map.getSource(SOURCE_ID) as GeoJSONSource | undefined
    if (!src) return
    src.setData(placesToGeoJSON(places))
    fitPlaces(map, places)
  }, [places])

  return <div ref={containerRef} className="americana-map" />
}
