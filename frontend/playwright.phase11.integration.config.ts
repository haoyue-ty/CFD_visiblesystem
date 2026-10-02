import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import accepted from './playwright.phase10.integration.config'

export default defineConfig({
  ...accepted,
  workers: 1,
  retries: 0,
  outputDir: fileURLToPath(new URL('./test-results/phase11-final', import.meta.url)),
  reporter: [
    ['list'],
    ['json', { outputFile: fileURLToPath(new URL('../.cache/phase11/playwright.json', import.meta.url)) }],
    ['junit', { outputFile: fileURLToPath(new URL('../.cache/phase11/playwright.xml', import.meta.url)) }],
  ],
})
