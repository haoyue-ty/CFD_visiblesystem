import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
const workspace = fileURLToPath(new URL('..', import.meta.url))
const apiPort = process.env.E2E_API_PORT ?? '5000'
const productionPort = process.env.E2E_PRODUCTION_PORT ?? '4373'
const mockPort = process.env.E2E_MOCK_PORT ?? '4473'
const apiTarget = `http://127.0.0.1:${apiPort}`
const productionUrl = `http://127.0.0.1:${productionPort}`
const mockUrl = `http://127.0.0.1:${mockPort}`

export default defineConfig({
  timeout: 30_000,
  expect: { timeout: 10_000 },
  workers: 2,
  reporter: [['list'], ['json', { outputFile: '../.cache/phase6/playwright.json' }]],
  use: { browserName: 'chromium' },
  projects: [
    { name: 'real-api', testDir: './tests', use: { baseURL: productionUrl } },
    { name: 'window3-mock-development', testDir: '../tests/window3_frontend', use: { baseURL: mockUrl } },
    { name: 'window4-allocation-ui', testDir: '../tests/window4_allocation', use: { baseURL: mockUrl } },
  ],
  webServer: [
    { command: `"${python}" -m scripts.serve_backend`, cwd: workspace, url: `${apiTarget}/api/v1/system`, env: { API_PORT: apiPort }, reuseExistingServer: false },
    { command: `npm run preview -- --port ${productionPort} --strictPort`, url: productionUrl, env: { API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
    { command: `npm run dev -- --port ${mockPort} --strictPort`, url: mockUrl, env: { VITE_DATA_PROVIDER: 'MOCK', API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
  ],
})
