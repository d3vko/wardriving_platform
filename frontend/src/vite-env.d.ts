/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ANALYTICS_DEFAULT_START_DATE: string
  readonly VITE_ANALYTICS_DEFAULT_END_DATE: string
  readonly VITE_ANALYTICS_API_URL: string
  readonly VITE_API_TARGET: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_FAVICON_URL: string
  readonly VITE_EVENT_HOME_TITLE: string
  readonly VITE_EVENT_HOME_BADGE: string
  readonly VITE_EVENT_INTRO_TEXT: string
  readonly VITE_EVENT_DYNAMICS_TITLE: string
  readonly VITE_EVENT_DYNAMICS_TEXT: string
  readonly VITE_EVENT_LOGO_SECTION_TITLE: string
  readonly VITE_EVENT_LOGO_SECTION_TEXT: string
  readonly VITE_EVENT_LOGO_URL: string
  readonly VITE_EVENT_LOGO_ALT: string
  readonly VITE_EVENT_LOGO_LINK_URL: string
  readonly VITE_EVENT_LOGO_LINK_LABEL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
