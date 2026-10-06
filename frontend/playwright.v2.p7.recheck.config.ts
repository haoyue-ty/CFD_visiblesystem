import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import accepted from './playwright.phase11.integration.config'
export default defineConfig({
  ...accepted,
  outputDir: fileURLToPath(new URL('./test-results/v2-p7-recheck',import.meta.url)),
  reporter: [['list'],['json',{outputFile:fileURLToPath(new URL('../docs/v2/p7_v1_recheck.json',import.meta.url))}]],
})
