import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { appConfig } from '@/config/eventConfig'

const root = document.getElementById('root')
if (!root) throw new Error('Root element not found')

document.title = appConfig.appTitle
const favicon = document.querySelector("link[rel='icon']") ?? document.createElement('link')
favicon.setAttribute('rel', 'icon')
favicon.setAttribute('href', appConfig.appFaviconUrl)
document.head.appendChild(favicon)

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
