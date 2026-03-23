import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

// En contenedor (podman-compose) se resuelve por nombre de servicio.
// Fuera del contenedor (dev en host), usa VITE_API_TARGET=http://localhost:8000
const API_TARGET = process.env.VITE_API_TARGET ?? 'http://wardrive:8000'

export default defineConfig({
  plugins: [react()],
  base: '/ctf/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/wardriving': {
        target: API_TARGET,
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
          mui: ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
        },
      },
    },
  },
})
