import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
const workspace = fileURLToPath(new URL('..', import.meta.url))
const python = process.env.E2E_PYTHON ?? fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
const apiPort = process.env.E2E_API_PORT ?? '5088'
const uiPort = process.env.E2E_PRODUCTION_PORT ?? '4388'
const apiTarget = `http://127.0.0.1:${apiPort}`
const uiTarget = `http://127.0.0.1:${uiPort}`
export default defineConfig({
  testDir: './tests', testMatch: ['cylinder-crossflow-real-api.spec.ts', 'routes.spec.ts', 'case8-real-integration.spec.ts', 'allocation-real-api.spec.ts'],
  timeout: 90_000, expect: { timeout: 30_000 }, workers: 2,
  reporter: [['list'], ['json', { outputFile: '../.cache/phase8/playwright-window3.json' }]],
  use: { baseURL: uiTarget, browserName: 'chromium', screenshot: 'only-on-failure' },
  webServer: [
    { command: `"${python}" -m scripts.serve_backend`, cwd: workspace, url: `${apiTarget}/api/v1/system`, env: { API_PORT: apiPort }, reuseExistingServer: false },
    { command: `npm run preview -- --port ${uiPort} --strictPort`, url: uiTarget, env: { API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
  ],
})
