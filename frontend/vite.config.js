import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.VITE_FRONTEND_PORT) || 3000,
    proxy: {
      '/api': {
        target: `http://localhost:${Number(process.env.VITE_BACKEND_PORT) || 5000}`,
        changeOrigin: true
      }
    }
  }
})
