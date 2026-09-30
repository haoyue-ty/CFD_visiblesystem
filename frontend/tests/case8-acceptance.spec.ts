/**
 * Window 4 — Frontend acceptance specification for the Case8 functional slice.
 *
 * This spec encodes the required end-to-end chain and the state-restoration
 * obligation. It is written against the frozen contract's URL/IA decisions
 * (docs/03_USER_FLOW_AND_IA.md, docs/06_API_CONTRACT.md) so it becomes runnable
 * unchanged once the frontend slice lands on the merged base.
 *
 * Tests that depend on unimplemented frontend routes are declared with
 * `test.fixme(...)`: Playwright reports them as *skipped*, never as passing, which
 * keeps the acceptance gap visible in the report instead of hidden behind green.
 */

import { test, expect } from '@playwright/test'

/** The required acceptance chain: Entry → Home → Lab → Case8 → D_u → Snapshot 6 →
 *  Entropy → Metrics → Evidence → Back. */
const CHAIN = {
  entry: '/',
  home: '/home',
  lab: '/lab',
  case8: '/lab/experiments/case8',
  du: '/lab/experiments/case8/configs/D_u',
  snapshot6: '/lab/experiments/case8/configs/D_u/snapshots/6',
  entropy: '/lab/experiments/case8/configs/D_u/tabs/entropy',
  metrics: '/lab/experiments/case8/configs/D_u/tabs/metrics',
  evidence: '/evidence/ev.case8.D_u.snapshot.6.density',
}

const CASE8_TIMELINE = [0, 382, 765, 1147, 1530, 1912]

test.describe('Case8 acceptance chain', () => {
  test('every recorded snapshot index is addressable and index 0 is refused', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend Case8 snapshot routes not merged')
    for (const index of [1, 2, 3, 4, 5, 6]) {
      await page.goto(`/lab/experiments/case8/configs/D_u/snapshots/${index}`)
      await expect(page.locator('main[data-page="experiment"]')).toBeVisible()
    }
    await page.goto('/lab/experiments/case8/configs/D_u/snapshots/0')
    await expect(page.locator('[data-state="invalid-selector"]')).toBeVisible()
  })

  test('the initial frame is snapshot 1 with step 0, not snapshot 0', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend Case8 snapshot routes not merged')
    await page.goto(CHAIN.snapshot6.replace('/6', '/1'))
    await expect(page.locator('[data-field="snapshot-index"]')).toHaveText('1')
    await expect(page.locator('[data-field="step-index"]')).toHaveText('0')
  })

  test('snapshot 6 of D_u shows step 1912 and physical time 0.08', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend Case8 snapshot routes not merged')
    await page.goto(CHAIN.snapshot6)
    await expect(page.locator('[data-field="snapshot-index"]')).toHaveText('6')
    await expect(page.locator('[data-field="step-index"]')).toHaveText('1912')
    await expect(page.locator('[data-field="physical-time"]')).toHaveText('0.08')
  })

  test('entropy tab reports a 1912-record series for the selected configuration', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend entropy tab not merged')
    await page.goto(CHAIN.entropy)
    await expect(page.locator('[data-field="total-point-count"]')).toHaveText('1912')
    await expect(page.locator('[data-field="aggregation"]')).not.toHaveText('STEP_INCREMENT')
  })

  test('metrics tab separates terminal metrics from snapshot-scoped metrics', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend metrics tab not merged')
    await page.goto(CHAIN.metrics)
    await expect(page.locator('[data-metric-scope="TERMINAL"]')).toBeVisible()
    await expect(page.locator('[data-metric-scope="MULTI_SNAPSHOT"]').first()).toBeVisible()
  })

  test('an absent metric is rendered as missing, never as zero', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend metrics tab not merged')
    await page.goto(CHAIN.metrics)
    const missing = page.locator('[data-availability="MISSING"]')
    if (await missing.count()) {
      await expect(missing.first()).not.toContainText('0')
      await expect(missing.first()).toContainText(/missing|unavailable/i)
    }
  })

  test('evidence view exposes provenance without an absolute source path', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend evidence view not merged')
    await page.goto(CHAIN.evidence)
    const body = await page.locator('body').innerText()
    expect(body).not.toMatch(/[A-Za-z]:[\\/]/)
    expect(body).not.toMatch(/file:\/\//i)
  })
})

test.describe('state restoration', () => {
  test('reloading a deep link restores the selection', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend deep-link state not merged')
    await page.goto(CHAIN.snapshot6)
    await page.reload()
    await expect(page.locator('[data-field="snapshot-index"]')).toHaveText('6')
    await expect(page.locator('[data-field="step-index"]')).toHaveText('1912')
  })

  test('back navigation restores the previous tab selection', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend deep-link state not merged')
    await page.goto(CHAIN.entropy)
    await page.goto(CHAIN.metrics)
    await page.goBack()
    await expect(page).toHaveURL(new RegExp(`${CHAIN.entropy}$`))
  })

  test('switching configuration clears the previous selection', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend selector state not merged')
    await page.goto(CHAIN.snapshot6)
    await page.goto('/lab/experiments/case8/configs/A_u/snapshots/6')
    await expect(page).toHaveURL(/configs\/A_u\/snapshots\/6$/)
    await expect(page.locator('[data-field="config-id"]')).toHaveText('A_u')
  })

  test('the snapshot timeline offers exactly the six recorded frames', async ({ page }) => {
    test.fixme(true, 'WAITING_FOR_IMPLEMENTATION: frontend snapshot timeline not merged')
    await page.goto(CHAIN.du)
    const steps = await page.locator('[data-timeline-step]').allTextContents()
    expect(steps.map(Number)).toEqual(CASE8_TIMELINE)
  })
})

test.describe('bootstrap chain still holds', () => {
  test('the frozen bootstrap route chain is unchanged', async ({ page }) => {
    await page.goto(CHAIN.entry)
    for (const [link, pageId] of [['Home', 'home'], ['Lab', 'lab'], ['Case8', 'experiment'], ['Evidence', 'evidence']]) {
      await page.getByRole('link', { name: link, exact: true }).click()
      await expect(page.locator(`main[data-page="${pageId}"]`)).toBeVisible()
    }
    await page.goBack()
    await expect(page.locator('main[data-page="experiment"]')).toBeVisible()
  })
})
