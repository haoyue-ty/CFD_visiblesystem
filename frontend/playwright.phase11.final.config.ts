import { defineConfig } from '@playwright/test'
import accepted from './playwright.phase11.integration.config'
import { fileURLToPath } from 'node:url'
export default defineConfig({
  ...accepted,
  outputDir: fileURLToPath(new URL('./test-results/phase11-final-qa', import.meta.url)),
  reporter: [
    ['list'],
    ['json', { outputFile: fileURLToPath(new URL('../.cache/phase11-final/playwright.json', import.meta.url)) }],
    ['junit', { outputFile: fileURLToPath(new URL('../.cache/phase11-final/playwright.xml', import.meta.url)) }],
  ],
})
