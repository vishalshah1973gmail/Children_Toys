import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    // Cloudflare tunnel hostname; Vite blocks unknown Host headers otherwise.
    allowedHosts: ['toybox.demoaiprojects.com'],
    proxy: {
      // The browser calls same-origin /api, so a public visitor never needs localhost:8000.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Product images are served straight off the backend's disk.
      '/static': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 5173,
    host: true,
    allowedHosts: ['toybox.demoaiprojects.com'],
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/static': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
