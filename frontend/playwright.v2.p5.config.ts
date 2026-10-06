import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
const frontend = fileURLToPath(new URL('./', import.meta.url))
const workspace = fileURLToPath(new URL('..', import.meta.url))
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
export default defineConfig({
  testDir: './live-tests', testMatch: '**/v2-p5.spec.ts', workers: 1, retries: 0, timeout: 60000,
  expect: { timeout: 20000 }, use: { baseURL: 'http://127.0.0.1:4426', browserName: 'chromium', screenshot: 'only-on-failure' },
  outputDir: './test-results/v2-p5', reporter: [['list'], ['json', { outputFile: '../docs/v2/p5_browser_acceptance.json' }]],
  webServer: [
    { command: `"${python}" -B -m scripts.serve_backend`, cwd: workspace, url: 'http://127.0.0.1:5126/api/v2/cases',
      env: { API_PORT: '5126', DEEPSEEK_API_KEY: '' }, reuseExistingServer: false },
    { command: 'npm run preview -- --port 4426 --strictPort', cwd: frontend, url: 'http://127.0.0.1:4426',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:5126' }, reuseExistingServer: false },
  ],
})
