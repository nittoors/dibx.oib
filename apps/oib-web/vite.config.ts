import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')

  return {
    base: '/OIBReadiness/',
    plugins: [react()],
    build: {
      assetsInlineLimit: 0,
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html'],
      },
    },
  }
})
