import { defineConfig } from '@playwright/test'

export default defineConfig({
  // Window 3 owns tests/window3_frontend at the repository root.
  testDir: '../tests/window3_frontend',
  timeout: 30_000,
  expect: { timeout: 7_000 },
  // Port 4373 is dedicated to the Window 3 frontend worktree; parallel Phase 5B
  // windows use 4173 and 4273 for their own preview servers.
  use: { baseURL: 'http://127.0.0.1:4373', browserName: 'chromium' },
  webServer: { command: 'npm run preview -- --port 4373 --strictPort', url: 'http://127.0.0.1:4373', reuseExistingServer: false },
})
