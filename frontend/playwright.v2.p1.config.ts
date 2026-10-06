import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const frontend = fileURLToPath(new URL('./', import.meta.url))
const workspace = fileURLToPath(new URL('..', import.meta.url))
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
const apiTarget = 'http://127.0.0.1:5121'
const baseURL = 'http://127.0.0.1:4421'

export default defineConfig({
  testDir: './tests', testMatch: '**/v2-p1-experiments.spec.ts', workers: 1, retries: 0,
  use: { baseURL, browserName: 'chromium', screenshot: 'only-on-failure' },
  outputDir: './test-results/v2-p1', reporter: [['list'], ['json', { outputFile: '../docs/v2/p1_browser_results.json' }]],
  webServer: [
    { command: `"${python}" -B -m scripts.serve_backend`, cwd: workspace, url: `${apiTarget}/api/v2/cases`,
      env: { API_PORT: '5121', DEEPSEEK_API_KEY: '' }, reuseExistingServer: false },
    { command: 'npm run preview -- --port 4421 --strictPort', cwd: frontend, url: baseURL,
      env: { API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
  ],
})
