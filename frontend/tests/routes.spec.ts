import { test, expect } from '@playwright/test'

/**
 * Bootstrap-era route smoke test, updated for the Window 3 functional shell.
 * Each route must open and survive a reload.
 */
for (const [path, pageId] of [
  ['/', 'entry'], ['/home', 'home'], ['/lab', 'lab'],
  ['/lab/experiments/case8', 'experiment'],
  ['/evidence/mock.evidence.case8.D_u.metric.width', 'evidence'],
] as const) {
  test(`opens and reloads ${path}`, async ({ page }) => {
    await page.goto(path)
    await expect(page.locator(`main[data-page="${pageId}"]`)).toBeVisible()
    await page.reload()
    await expect(page.locator(`main[data-page="${pageId}"]`)).toBeVisible()
  })
}
