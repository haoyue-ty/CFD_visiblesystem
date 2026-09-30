import { test, expect } from '@playwright/test'

for (const [path, pageId] of [
  ['/', 'entry'], ['/home', 'home'], ['/lab', 'lab'],
  ['/lab/experiments/case8', 'experiment'], ['/evidence/bootstrap', 'evidence'],
]) {
  test(`opens and reloads ${path}`, async ({ page }) => {
    await page.goto(path)
    await expect(page.locator(`main[data-page="${pageId}"] h1`)).toHaveText('ShockPath Bootstrap')
    await page.reload()
    await expect(page.locator(`main[data-page="${pageId}"] h1`)).toHaveText('ShockPath Bootstrap')
  })
}

test('navigation follows the bootstrap chain', async ({ page }) => {
  await page.goto('/')
  for (const [link, pageId] of [['Home', 'home'], ['Lab', 'lab'], ['Case8', 'experiment'], ['Evidence', 'evidence']]) {
    await page.getByRole('link', { name: link, exact: true }).click()
    await expect(page.locator(`main[data-page="${pageId}"]`)).toBeVisible()
  }
  await page.goBack()
  await expect(page.locator('main[data-page="experiment"]')).toBeVisible()
})
