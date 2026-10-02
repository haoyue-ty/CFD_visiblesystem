import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  testMatch: '*.unit.spec.ts',
  workers: 1,
  retries: 0,
  reporter: [
    ['list'],
    ['json', { outputFile: '../.cache/phase9-final/frontend-unit.json' }],
    ['junit', { outputFile: '../.cache/phase9-final/frontend-unit.xml' }],
  ],
})
