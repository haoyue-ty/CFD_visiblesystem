import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
const frontend = fileURLToPath(new URL('./', import.meta.url))
const root = fileURLToPath(new URL('../', import.meta.url))
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
export default defineConfig({
  testDir: './tests', testMatch: 'closure-real-api.spec.ts', timeout: 90_000, expect: { timeout: 30_000 }, workers: 1, retries: 0,
  use: { browserName: 'chromium', baseURL: 'http://127.0.0.1:4573', screenshot: 'only-on-failure' },
  outputDir: 'test-results/closure',
  reporter: [['list'], ['json', { outputFile: '../.cache/phase9-closure/WINDOW3_PLAYWRIGHT.json' }], ['junit', { outputFile: '../.cache/phase9-closure/WINDOW3_TESTS.xml' }]],
  webServer: [
    { command: `"${python}" -B -m scripts.serve_backend`, cwd: root, url: 'http://127.0.0.1:5073/api/v1/system', env: { API_PORT: '5073' }, reuseExistingServer: false, timeout: 120_000 },
    { command: 'npm run preview -- --port 4573 --strictPort', cwd: frontend, url: 'http://127.0.0.1:4573', env: { API_PROXY_TARGET: 'http://127.0.0.1:5073' }, reuseExistingServer: false },
  ],
})
