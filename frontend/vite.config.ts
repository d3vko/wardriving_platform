import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

// En contenedor (podman-compose) se resuelve por nombre de servicio.
// Fuera del contenedor (dev en host), usa VITE_API_TARGET=http://localhost:8000
const API_TARGET = process.env.VITE_API_TARGET ?? 'http://wardrive:8000'
const MAP_PROXY_TARGET =
  process.env.VITE_MAP_PROXY_TARGET ??
  (API_TARGET.includes('wardrive:') ? 'http://wardrive_proxy:8000' : API_TARGET)

export default defineConfig({
  plugins: [react()],
  base: '/ctf/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    exclude: ['maplibre-gl'],
  },
  worker: {
    format: 'es',
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/wardriving': {
        target: API_TARGET,
        changeOrigin: true,
        ws: true,
        // Misma convención que nginx: el backend Django recibe /v1/... sin prefijo /wardriving
        rewrite: (path) => path.replace(/^\/wardriving/, ''),
      },
      '/map-tiles': {
        target: MAP_PROXY_TARGET,
        changeOrigin: true,
      },
      '/map-americana': {
        target: MAP_PROXY_TARGET,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          antd: ['antd', '@ant-design/icons', '@ant-design/plots'],
        },
      },
    },
  },
})
