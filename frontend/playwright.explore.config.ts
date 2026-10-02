import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const workspace = fileURLToPath(new URL('..', import.meta.url))
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
const apiPort = process.env.E2E_API_PORT ?? '5103'
const uiPort = process.env.E2E_PRODUCTION_PORT ?? '4373'
const baseURL = `http://127.0.0.1:${uiPort}`
const apiTarget = `http://127.0.0.1:${apiPort}`
export default defineConfig({
  testDir: './tests',
  timeout: 90_000,
  expect: { timeout: 30_000 },
  // Serialize expensive read-only source loading across scientific families.
  workers: 1,
  reporter: [['list'], ['json', { outputFile: '../.cache/phase10-window3/playwright.json' }]],
  use: { browserName: 'chromium', baseURL },
  webServer: [
    { command: `"${python}" -m scripts.serve_backend`, cwd: workspace, url: `${apiTarget}/api/v1/system`, env: { API_PORT: apiPort }, reuseExistingServer: false },
    { command: `npm run preview -- --port ${uiPort} --strictPort`, url: baseURL, env: { API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
  ],
})
