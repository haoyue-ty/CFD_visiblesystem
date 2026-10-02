import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import base from './playwright.config'

const frontend = fileURLToPath(new URL('./', import.meta.url))
const workspace = fileURLToPath(new URL('..', import.meta.url))
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
const apiPort = process.env.E2E_API_PORT ?? '5110'
const uiPort = process.env.E2E_PRODUCTION_PORT ?? '4410'
const mockPort = process.env.E2E_MOCK_PORT ?? '4510'
const apiTarget = `http://127.0.0.1:${apiPort}`
const baseURL = `http://127.0.0.1:${uiPort}`
const mockURL = `http://127.0.0.1:${mockPort}`

export default defineConfig({
  timeout: 90_000,
  expect: { timeout: 30_000 },
  workers: 1,
  retries: 0,
  projects: [
    { name: 'unit', testDir: './tests', testMatch: '**/*.unit.spec.ts' },
    {
      name: 'phase5-10-real-api', testDir: './tests',
      testIgnore: ['**/*.unit.spec.ts', '**/phase8-final-integration.spec.ts'],
      use: { baseURL },
    },
    {
      name: 'phase8-real-api', testDir: './tests',
      testMatch: '**/phase8-final-integration.spec.ts', timeout: 180_000,
      use: { baseURL },
    },
    ...base.projects!.filter(p => p.name !== 'real-api').map(p => ({
      ...p, testDir: resolve(frontend, p.testDir!), use: { baseURL: mockURL },
    })),
  ],
  use: { browserName: 'chromium', screenshot: 'only-on-failure' },
  webServer: [
    { command: `"${python}" -m scripts.serve_backend`, cwd: workspace, url: `${apiTarget}/api/v1/system`, env: { API_PORT: apiPort }, reuseExistingServer: false },
    { command: `npm run preview -- --port ${uiPort} --strictPort`, cwd: frontend, url: baseURL, env: { API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
    { command: `npm run dev -- --port ${mockPort} --strictPort`, cwd: frontend, url: mockURL, env: { VITE_DATA_PROVIDER: 'MOCK', API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
  ],
  outputDir: resolve(frontend, 'test-results/phase10-final'),
  reporter: [['list'], ['json', { outputFile: resolve(frontend, '../.cache/phase10-final/playwright.json') }]],
})
