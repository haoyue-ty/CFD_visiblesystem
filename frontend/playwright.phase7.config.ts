import { defineConfig } from '@playwright/test'
import base from './playwright.config'

export default defineConfig(base, {
  reporter: [['list'], ['json', { outputFile: process.env.PHASE7_REPORT ?? '../.cache/phase7/playwright.json' }]],
})
