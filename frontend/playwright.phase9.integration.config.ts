import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import phase8 from './playwright.phase8.integration.config'

const frontend = fileURLToPath(new URL('./', import.meta.url))
const root = fileURLToPath(new URL('../', import.meta.url))
const real = phase8.projects!.find(project => project.name === 'real-api')!

export default defineConfig({
  ...phase8,
  workers: 1,
  retries: 0,
  projects: [
    ...phase8.projects!.map(project => project.name === 'real-api' ? {
      ...project,
      testIgnore: ['**/cylinder-crossflow-real-api.spec.ts', '**/phase8-final-integration.spec.ts', '**/closure-real-api.spec.ts', '**/*.unit.spec.ts'],
      timeout: 90_000,
      expect: { timeout: 30_000 },
    } : project),
    {
      ...real,
      name: 'phase9-real-api',
      testDir: `${frontend}tests`,
      testMatch: 'closure-real-api.spec.ts',
      timeout: 90_000,
      expect: { timeout: 30_000 },
    },
  ],
  outputDir: `${frontend}test-results/phase9-final`,
  reporter: [
    ['list'],
    ['json', { outputFile: `${root}.cache/phase9-final/playwright.json` }],
    ['junit', { outputFile: `${root}.cache/phase9-final/playwright.xml` }],
  ],
})
