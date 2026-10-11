import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const workspace = fileURLToPath(new URL('..', import.meta.url))
const frontend = fileURLToPath(new URL('.', import.meta.url))
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
const apiPort = process.env.E2E_API_PORT ?? '5162'
const uiPort = process.env.E2E_PRODUCTION_PORT ?? '4462'
const api = `http://127.0.0.1:${apiPort}`
const baseURL = `http://127.0.0.1:${uiPort}`
export default defineConfig({
  testDir: './tests', testMatch: 'phase-b-exports.spec.ts', workers: 1, retries: 0, timeout: 90000,
  use: { baseURL, viewport: { width: 1440, height: 1000 }, acceptDownloads: true },
  webServer: [
    { command: `"${python}" -B -c "from waitress import serve; from backend import create_app; serve(create_app(), host='127.0.0.1', port=${apiPort}, threads=12)"`,
      cwd: workspace, url: `${api}/api/v2/cases`, reuseExistingServer: false,
      env: { DEEPSEEK_API_KEY: '', PYTHONDONTWRITEBYTECODE: '1' } },
    { command: `npm run preview -- --port ${uiPort} --strictPort`, cwd: frontend, url: baseURL,
      env: { API_PROXY_TARGET: api }, reuseExistingServer: false },
  ],
  outputDir: './test-results/phase-b',
  reporter: [['list'], ['json', { outputFile: '../.cache/phase-b/frontend-results.json' }], ['junit', { outputFile: '../.cache/phase-b/frontend-results.xml' }]],
})
