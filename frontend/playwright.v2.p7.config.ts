import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
const frontend = fileURLToPath(new URL('./', import.meta.url))
const workspace = fileURLToPath(new URL('..', import.meta.url))
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
export default defineConfig({
  testDir: './live-tests', testMatch: '**/v2-p7.spec.ts', workers: 1, retries: 0, timeout: 60000,
  expect: { timeout: 20000 }, use: { baseURL: 'http://127.0.0.1:4440', browserName: 'chromium', screenshot: 'only-on-failure' },
  outputDir: fileURLToPath(new URL('./test-results/v2-p7', import.meta.url)),
  reporter: [['list'], ['json', { outputFile: fileURLToPath(new URL('../docs/v2/p7_browser_acceptance.json', import.meta.url)) }]],
  webServer: [
    { command: `"${python}" -B -m scripts.serve_backend`, cwd: workspace, url: 'http://127.0.0.1:5130/api/v2/cases',
      env: { API_PORT: '5130', DEEPSEEK_API_KEY: '' }, reuseExistingServer: false },
    { command: 'npm run preview -- --port 4440 --strictPort', cwd: frontend, url: 'http://127.0.0.1:4440',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:5130' }, reuseExistingServer: false },
  ],
})
