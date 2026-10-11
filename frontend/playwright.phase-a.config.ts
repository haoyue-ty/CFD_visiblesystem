import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import accepted from './playwright.phase11.integration.config'
const frontend = fileURLToPath(new URL('./', import.meta.url))
const workspace = fileURLToPath(new URL('..', import.meta.url))
const python = fileURLToPath(new URL('../.venv/Scripts/python.exe', import.meta.url))
const apiPort = process.env.E2E_API_PORT ?? '5151'
const uiPort = process.env.E2E_PRODUCTION_PORT ?? '4451'
const mockPort = process.env.E2E_MOCK_PORT ?? '4551'
const apiTarget = `http://127.0.0.1:${apiPort}`
const baseURL = `http://127.0.0.1:${uiPort}`

export default defineConfig({
  ...accepted,
  projects: accepted.projects!.map(project => project.name === 'phase5-10-real-api' || project.name === 'phase8-real-api'
    ? { ...project, use: { ...project.use, baseURL } }
    : project.name === 'unit' ? project : { ...project, use: { ...project.use, baseURL: `http://127.0.0.1:${mockPort}` } }).concat([
      { name: 'v2-p7-compatibility', testDir: './live-tests', testMatch: '**/v2-p7.spec.ts', use: { baseURL } },
    ]),
  webServer: [
    { command: `"${python}" -B -m scripts.serve_backend`, cwd: workspace, url: `${apiTarget}/api/v2/cases`,
      env: { API_PORT: apiPort, DEEPSEEK_API_KEY: '', PYTHONDONTWRITEBYTECODE: '1' }, reuseExistingServer: false },
    { command: `npm run preview -- --port ${uiPort} --strictPort`, cwd: frontend, url: baseURL,
      env: { API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
    { command: `npm run dev -- --port ${mockPort} --strictPort`, cwd: frontend, url: `http://127.0.0.1:${mockPort}`,
      env: { VITE_DATA_PROVIDER: 'MOCK', API_PROXY_TARGET: apiTarget }, reuseExistingServer: false },
  ],
  outputDir: './test-results/phase-a',
  reporter: [['list'], ['json', { outputFile: '../.cache/phase-a/frontend-results.json' }], ['junit', { outputFile: '../.cache/phase-a/frontend-results.xml' }]],
})
