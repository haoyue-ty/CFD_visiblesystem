import { defineConfig } from '@playwright/test'

/**
 * Window 3 spectral acceptance against ALREADY-RUNNING servers.
 *
 * The main config starts its own webServers; in this environment those cannot bind
 * from the sandboxed test runner, so this override reuses the servers started
 * outside the sandbox:
 *   - backend  http://127.0.0.1:5000  (scripts.serve_backend)
 *   - mock SPA http://127.0.0.1:4473  (vite dev, VITE_DATA_PROVIDER=MOCK)
 */
export default defineConfig({
  timeout: 30_000,
  expect: { timeout: 10_000 },
  workers: 1,
  reporter: [['list']],
  use: { browserName: 'chromium' },
  projects: [
    { name: 'window3-spectral-ui', testDir: '../tests/window3_spectral', use: { baseURL: 'http://127.0.0.1:4473' } },
    { name: 'window3-spectral-real-api', testDir: './tests', testMatch: /spectral-real-api\.spec\.ts/, use: { baseURL: 'http://127.0.0.1:4373' } },
  ],
})
