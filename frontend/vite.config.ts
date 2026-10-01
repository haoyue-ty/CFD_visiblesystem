import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig(({ mode }) => {
  const apiTarget = loadEnv(mode, '.', 'API_PROXY_TARGET').API_PROXY_TARGET ?? 'http://127.0.0.1:5000'
  return {
    plugins: [vue()],
    server: { proxy: { '/api': apiTarget } },
    preview: { proxy: { '/api': apiTarget } },
  }
})
