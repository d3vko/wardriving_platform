import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import App from './App'
import { appConfig } from '@/config/eventConfig'

const sentryDsn = (import.meta.env.VITE_SENTRY_DSN || '').trim()
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: (import.meta.env.VITE_SENTRY_ENVIRONMENT || 'container').trim(),
    tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || 0),
    sendDefaultPii: true,
  })
}

const root = document.getElementById('root')
if (!root) throw new Error('Root element not found')

document.title = appConfig.appTitle
const favicon = document.querySelector("link[rel='icon']") ?? document.createElement('link')
favicon.setAttribute('rel', 'icon')
favicon.setAttribute('href', appConfig.appFaviconUrl)
document.head.appendChild(favicon)

createRoot(root).render(
  <StrictMode>
    <Sentry.ErrorBoundary fallback={<p>Something went wrong.</p>}>
      <App />
    </Sentry.ErrorBoundary>
  </StrictMode>,
)
