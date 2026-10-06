import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const frontend = fileURLToPath(new URL('./', import.meta.url))
const workspace = fileURLToPath(new URL('..', import.meta.url))
const apiTarget = 'http://127.0.0.1:5122'
const baseURL = 'http://127.0.0.1:4422'

// Explicit live acceptance only. The backend launcher reads the ignored .env;
// credentials are never supplied to Vite or stored in test output/config.
export default defineConfig({
  testDir: './live-tests', timeout: 90_000, workers: 1, retries: 0,
  use: { baseURL, browserName: 'chromium', screenshot: 'only-on-failure' },
  outputDir: './test-results/v2-p1-live', reporter: [['list'], ['json', { outputFile: '../docs/v2/p1_live_browser_results.json' }]],
  webServer: [
    { command: 'pwsh -NoProfile -File scripts/serve_backend.ps1', cwd: workspace, url: `${apiTarget}/api/v2/cases`,
      env: { API_PORT: '5122' }, reuseExistingServer: false },
    { command: 'npm run preview -- --port 4422 --strictPort', cwd: frontend, url: baseURL,
      env: { API_PROXY_TARGET: apiTarget, DEEPSEEK_API_KEY: '' }, reuseExistingServer: false },
  ],
})
