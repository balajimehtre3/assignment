import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  preview: {
    allowedHosts: ['assignment-2-7l0e.onrender.com'],
  },

  server: {
    port: 5173,

    proxy: {
      '/api': {
        target: 'https://backend-two-xi-91.vercel.app',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})