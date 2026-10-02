import { test, expect } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

test('Entry → Home → seven real Scenes → Evidence Detail → Scene → Lab → original Scene', async ({ page }) => {
  test.setTimeout(180_000)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const ready = ['entropy-terminal', 'mechanism-architecture', 'mechanism-architecture', 'gate-Ungated', 'guided-modal-table', 'sector-table', 'evidence-record']
  await page.goto('/')
  await page.getByTestId('enter-system').click()
  await expect(page.locator('main[data-page="home"]')).toBeVisible()
  await page.getByTestId('home-start-explore').click()
  for (let scene = 1; scene <= 7; scene++) {
    await expect(page.getByTestId('scene-progress')).toHaveText(`Scene ${scene} / 7`)
    await expect(page.getByTestId(ready[scene - 1]!)).toBeVisible()
    await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
    if (scene === 1) await expect(page.getByTestId('scene-conclusion')).toContainText('magnitude alone cannot explain')
    if (scene === 2) await expect(page.getByTestId('node-acoustic-gate')).toHaveAttribute('data-role', 'TRIGGER')
    if (scene === 3) {
      await page.getByTestId('node-tangential-output').click()
      await expect(page.getByTestId('selected-node')).toContainText('δ_t does not enter gate')
      await expect(page.getByTestId('output-state')).toContainText('Inactive / zero')
      await page.getByTestId('mechanism-state').selectOption('WEAKLY_2D')
      await expect(page.getByTestId('output-state')).toContainText('Active')
      await expect(page.getByTestId('near1d-gap')).toContainText('No authoritative')
    }
    if (scene === 4) await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(3)
    if (scene === 5) {
      await expect(page.getByTestId('guided-modal-table').locator('tbody tr')).toHaveCount(17)
      await expect(page.getByTestId('spectral-scientific-limit')).toContainText('does not imply uniform modal damping')
    }
    if (scene === 6) {
      await expect(page.getByTestId('scene-conclusion')).toContainText('pathway budget ≠ pathway allocation ≠ macroscopic consequence')
      await expect(page.getByTestId('descriptive-only')).toContainText('DESCRIPTIVE_ONLY')
      await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
      await expect(page.getByTestId('cumulative-2d-missing')).toContainText('Missing')
    }
    if (scene < 7) await page.getByTestId('scene-next').click()
  }
  await expect(page.getByRole('heading', { name: 'Source assets', exact: true })).toBeVisible()
  await page.locator('a[data-testid="evidence-link"][href*="ev.case8.D_u.entropy"]').first().click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.locator('main[data-page="evidence"]')).toBeVisible()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  const output = fileURLToPath(new URL('../../.cache/phase10-final/', import.meta.url))
  mkdirSync(output, { recursive: true })
  await page.screenshot({ path: `${output}journey-evidence.png`, fullPage: true })
  await page.getByTestId('back-to-result').click()
  await expect(page.getByTestId('scene-progress')).toHaveText('Scene 7 / 7')
  await page.getByTestId('scene-nav-3').click()
  await page.getByTestId('mechanism-state').selectOption('WEAKLY_2D')
  await page.getByTestId('node-tangential-output').click()
  await page.getByTestId('explore-open-lab').click()
  await expect(page).toHaveURL(/\/lab\/mechanism.*source_scene=3/)
  await page.reload()
  await expect(page.getByTestId('mechanism-state')).toHaveValue('WEAKLY_2D')
  await page.getByTestId('mechanism-return').click()
  await expect(page.getByTestId('scene-progress')).toHaveText('Scene 3 / 7')
  await expect(page.getByTestId('mechanism-state')).toHaveValue('WEAKLY_2D')
  await expect(page.getByTestId('selected-node')).toContainText('δ_t does not enter gate')
  expect(errors).toEqual([])
})
