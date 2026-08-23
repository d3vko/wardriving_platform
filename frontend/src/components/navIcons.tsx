import type { CSSProperties, ReactNode, SVGProps } from 'react'
import brandKombiUrl from '@/assets/brand-kombi.png'

const wrapStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 20,
  lineHeight: 0,
  verticalAlign: '-0.2em',
}

function NavSvg({ children, ...props }: SVGProps<SVGSVGElement> & { children: ReactNode }) {
  return (
    <span className="anticon nav-rf-icon" role="img" style={wrapStyle}>
      <svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor" aria-hidden {...props}>
        {children}
      </svg>
    </span>
  )
}

/** Casa sólida, puerta recortada. */
export function NavHomeIcon() {
  return (
    <NavSvg>
      <path
        fillRule="evenodd"
        d="M12 2.4 2.6 10.4a1 1 0 0 0-.3.7V21a.9.9 0 0 0 .9.9h6.2V14.2h5.2V21.9h6.2a.9.9 0 0 0 .9-.9v-9.9a1 1 0 0 0-.3-.7L12 2.4Zm0 2.3 7.4 6.3V20.1h-4.4v-6.8a.9.9 0 0 0-.9-.9H9.9a.9.9 0 0 0-.9.9v6.8H4.6v-9.1L12 4.7Z"
      />
    </NavSvg>
  )
}

/** Combi 3/4 + WiFi: silueta de la imagen de referencia (mask). */
export function NavBrandIcon() {
  return (
    <span
      className="anticon nav-rf-icon nav-brand-icon"
      role="img"
      aria-hidden
      style={{
        display: 'inline-block',
        width: 32,
        height: 32,
        flexShrink: 0,
        backgroundColor: 'currentColor',
        WebkitMaskImage: `url(${brandKombiUrl})`,
        maskImage: `url(${brandKombiUrl})`,
        WebkitMaskRepeat: 'no-repeat',
        maskRepeat: 'no-repeat',
        WebkitMaskPosition: 'center',
        maskPosition: 'center',
        WebkitMaskSize: 'contain',
        maskSize: 'contain',
      }}
    />
  )
}

/** Arcos WiFi + pin: ítem de menú Wardriving. */
export function NavWifiMapIcon() {
  return (
    <NavSvg>
      <path d="M12 2.4c-3.3 0-6.3 1.25-8.55 3.3l1.85 1.85A9.1 9.1 0 0 1 12 4.9c2.5 0 4.8.9 6.7 2.65l1.85-1.85A11.5 11.5 0 0 0 12 2.4Z" />
      <path d="M12 6.85A7 7 0 0 0 7.05 9l1.8 1.8A4.7 4.7 0 0 1 12 9.15c1.25 0 2.4.45 3.25 1.35L17.05 8.7A7 7 0 0 0 12 6.85Z" />
      <path d="M12 11.15a2.7 2.7 0 0 0-1.95.8L12 13.9l1.95-1.95A2.7 2.7 0 0 0 12 11.15Z" />
      <path
        fillRule="evenodd"
        d="M12 15.35 8.55 19.5a.9.9 0 0 0 .7 1.5h5.5a.9.9 0 0 0 .7-1.5L12 15.35Zm0 2.55a.95.95 0 1 1 0-1.9.95.95 0 0 1 0 1.9Z"
      />
    </NavSvg>
  )
}

/** Torre de celosía + ondas + barras de señal (referencia LTE). */
export function NavLteIcon() {
  return (
    <NavSvg
      fill="none"
      stroke="currentColor"
      strokeWidth={1.55}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="10" cy="4.15" r="1.15" fill="currentColor" stroke="none" />
      <path d="M7.15 2.55c-1.15.85-1.15 2.35 0 3.2" />
      <path d="M5.55 1.55c-1.85 1.35-1.85 3.95 0 5.3" />
      <path d="M12.85 2.55c1.15.85 1.15 2.35 0 3.2" />
      <path d="M14.45 1.55c1.85 1.35 1.85 3.95 0 5.3" />
      <path d="M8.85 5.55 6.2 21.2h7.6L11.15 5.55" />
      <path d="M8.35 10.4h3.3M7.55 15.5h4.9M6.2 21.2h7.6" />
      <path d="M8.95 5.7 12.35 15.5M11.05 5.7 7.65 15.5" />
      <path d="M7.55 15.5 13.8 21.2M12.45 15.5 6.2 21.2" />
      <rect x="16.05" y="17.4" width="1.45" height="3.8" rx="0.55" fill="currentColor" stroke="none" />
      <rect x="17.85" y="15.6" width="1.45" height="5.6" rx="0.55" fill="currentColor" stroke="none" />
      <rect x="19.65" y="13.6" width="1.45" height="7.6" rx="0.55" fill="currentColor" stroke="none" />
      <rect x="21.45" y="11.5" width="1.45" height="9.7" rx="0.55" fill="currentColor" stroke="none" />
    </NavSvg>
  )
}

/** Tres barras redondeadas de altura creciente. */
export function NavAnalyticsIcon() {
  return (
    <NavSvg>
      <rect x="3.4" y="13.2" width="4.4" height="8" rx="1.2" />
      <rect x="9.8" y="8.4" width="4.4" height="12.8" rx="1.2" />
      <rect x="16.2" y="3.8" width="4.4" height="17.4" rx="1.2" />
    </NavSvg>
  )
}

/** Nube con flecha de subida recortada. */
export function NavUploadIcon() {
  return (
    <NavSvg>
      <path
        fillRule="evenodd"
        d="M8.2 19.4h7.8A4.6 4.6 0 0 0 20.4 12a4.5 4.5 0 0 0-3.4-4.3 6.4 6.4 0 0 0-12.3 1.8 4.8 4.8 0 0 0 .7 9.9h2.8Zm3.8-3.2V11l-1.8 1.8-1.3-1.3L12 7.8l3.3 3.5-1.3 1.3L13.2 11v5.2h-1.2Z"
      />
    </NavSvg>
  )
}

/** Documento con flecha de descarga. */
export function NavKmlIcon() {
  return (
    <NavSvg>
      <path
        fillRule="evenodd"
        d="M6.2 2.4h7.2L18.8 7.8V21a.9.9 0 0 1-.9.9H6.2a.9.9 0 0 1-.9-.9V3.3a.9.9 0 0 1 .9-.9Zm7.4 1.8v4.2h4.2l-4.2-4.2ZM11 9.6h2.4v4h2.2L12 17.4 8.8 13.6H11v-4Z"
      />
    </NavSvg>
  )
}
