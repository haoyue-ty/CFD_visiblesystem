import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import base from './playwright.config'
import phase8 from './playwright.phase8.config'

const frontend = fileURLToPath(new URL('./', import.meta.url))
const servers = (Array.isArray(base.webServer) ? base.webServer : [base.webServer]).map((server, index) => ({
  ...server!, ...(index === 0 ? {} : { cwd: frontend }),
}))

export default defineConfig({
  ...base, retries: 0,
  projects: [
    ...base.projects!.map(project => ({
      ...project, testDir: resolve(frontend, project.testDir!),
      ...(project.name === 'real-api' ? { testIgnore: ['**/cylinder-crossflow-real-api.spec.ts', '**/phase8-final-integration.spec.ts'] } : {}),
    })),
    {
      ...base.projects![0], name: 'phase8-real-api', testDir: resolve(frontend, 'tests'),
      testMatch: ['cylinder-crossflow-real-api.spec.ts', 'phase8-final-integration.spec.ts'],
      timeout: 180_000, expect: phase8.expect,
    },
  ],
  webServer: servers,
  outputDir: resolve(frontend, 'test-results/phase8-final'),
  reporter: [['list'], ['json', { outputFile: resolve(frontend, '../.cache/phase8-final/playwright.json') }]],
})
