import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
const workspace = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig({
  timeout: 30_000,
  expect: { timeout: 10_000 },
  workers: 2,
  reporter: [['list'], ['json', { outputFile: '../.cache/phase5/playwright.json' }]],
  use: { browserName: 'chromium' },
  projects: [
    { name: 'real-api', testDir: './tests', use: { baseURL: 'http://127.0.0.1:4373' } },
    { name: 'window3-mock-development', testDir: '../tests/window3_frontend', use: { baseURL: 'http://127.0.0.1:4473' } },
    { name: 'window4-allocation-ui', testDir: '../tests/window4_allocation', use: { baseURL: 'http://127.0.0.1:4473' } },
  ],
  webServer: [
    { command: `"${python}" -m scripts.serve_backend`, cwd: workspace, url: 'http://127.0.0.1:5000/api/v1/system', reuseExistingServer: false },
    { command: 'npm run preview -- --port 4373 --strictPort', url: 'http://127.0.0.1:4373', reuseExistingServer: false },
    { command: 'npm run dev -- --port 4473 --strictPort', url: 'http://127.0.0.1:4473', env: { VITE_DATA_PROVIDER: 'MOCK' }, reuseExistingServer: false },
  ],
})
