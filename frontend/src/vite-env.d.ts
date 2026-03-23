/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ANALYTICS_DEFAULT_START_DATE: string
  readonly VITE_ANALYTICS_DEFAULT_END_DATE: string
  readonly VITE_ANALYTICS_API_URL: string
  readonly VITE_API_TARGET: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
