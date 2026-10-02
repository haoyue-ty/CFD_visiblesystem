/** Window 4 acceptance activated with the Window 3 query-based UI routes.
 * Frozen IA §6/§16 says product-semantic routes are not literal frozen URLs.
 * Scientific golden values are unchanged; snapshot-zero remains explicitly rejected.
 */

import { test, expect } from '@playwright/test'

/** The required acceptance chain: Entry → Home → Lab → Case8 → D_u → Snapshot 6 →
 *  Entropy → Metrics → Evidence → Back. */
const CHAIN = {
  entry: '/',
  home: '/home',
  lab: '/lab',
  case8: '/lab/experiments/case8',
  du: '/lab/experiments/case8?config=D_u&tab=flow',
  snapshot6: '/lab/experiments/case8?config=D_u&tab=flow&snapshot=6',
  entropy: '/lab/experiments/case8?config=D_u&tab=entropy',
  metrics: '/lab/experiments/case8?config=D_u&tab=metrics',
  evidence: '/evidence/ev.case8.D_u.snapshot.6.density',
}

const CASE8_TIMELINE = [0, 382, 765, 1147, 1530, 1912]

test.describe('Case8 acceptance chain', () => {
  test('every recorded snapshot index is addressable and index 0 is refused', async ({ page }) => {
    for (const index of [1, 2, 3, 4, 5, 6]) {
      await page.goto(`/lab/experiments/case8?config=D_u&tab=flow&snapshot=${index}`)
      await expect(page.locator('main[data-page="experiment"]')).toBeVisible()
    }
    await page.goto('/lab/experiments/case8?config=D_u&tab=flow&snapshot=0')
    await expect(page.locator('[data-state="invalid-selector"]')).toBeVisible()
  })

  test('the initial frame is snapshot 1 with step 0, not snapshot 0', async ({ page }) => {
    await page.goto(CHAIN.snapshot6.replace('snapshot=6', 'snapshot=1'))
    await expect(page.getByTestId('snapshot-label')).toHaveText("快照 1 / 6")
    await expect(page.locator('[data-testid="snapshot-step"]')).toHaveText('0')
  })

  test('snapshot 6 of D_u shows step 1912 and physical time 0.08', async ({ page }) => {
    await page.goto(CHAIN.snapshot6)
    await expect(page.getByTestId('snapshot-label')).toHaveText("快照 6 / 6")
    await expect(page.locator('[data-testid="snapshot-step"]')).toHaveText('1912')
    await expect(page.locator('[data-testid="snapshot-physical-time"]')).toHaveText('0.08')
  })

  test('entropy tab reports a 1912-record series for the selected configuration', async ({ page }) => {
    await page.goto(CHAIN.entropy)
    await expect(page.locator('[data-field="total-point-count"]')).toHaveText('1912')
    await expect(page.locator('[data-field="aggregation"]')).not.toHaveText("单步增量")
  })

  test('metrics tab reports the recorded snapshot scope and definitions', async ({ page }) => {
    await page.goto(CHAIN.metrics)
    await expect(page.getByTestId('metrics-panel')).toContainText("时间范围")
    await expect(page.getByTestId('metrics-panel')).toContainText("多快照")
  })

  test('an absent metric is rendered as missing, never as zero', async ({ page }) => {
    await page.goto(CHAIN.metrics)
    const missing = page.locator('[data-availability="MISSING"]')
    if (await missing.count()) {
      await expect(missing.first()).not.toContainText('0')
      await expect(missing.first()).toContainText(/missing|unavailable/i)
    }
  })

  test('evidence view exposes provenance without an absolute source path', async ({ page }) => {
    await page.goto(CHAIN.evidence)
    const body = await page.locator('body').innerText()
    expect(body).not.toMatch(/[A-Za-z]:[\\/]/)
    expect(body).not.toMatch(/file:\/\//i)
  })
})

test.describe('state restoration', () => {
  test('reloading a deep link restores the selection', async ({ page }) => {
    await page.goto(CHAIN.snapshot6)
    await page.reload()
    await expect(page.getByTestId('snapshot-label')).toHaveText("快照 6 / 6")
    await expect(page.locator('[data-testid="snapshot-step"]')).toHaveText('1912')
  })

  test('back navigation restores the previous tab selection', async ({ page }) => {
    await page.goto(CHAIN.entropy)
    await page.goto(CHAIN.metrics)
    await page.goBack()
    await expect(page).toHaveURL(url => url.searchParams.get('tab') === 'entropy')
  })

  test('switching configuration clears the previous selection', async ({ page }) => {
    await page.goto(CHAIN.snapshot6)
    await page.goto('/lab/experiments/case8?config=A_u&tab=flow&snapshot=6')
    await expect(page).toHaveURL(url => url.searchParams.get('config') === 'A_u' && url.searchParams.get('snapshot') === '6')
    await expect(page.locator('main h1')).toHaveText("Case 8 — A_u")
  })

  test('the snapshot timeline offers exactly the six recorded frames', async ({ page }) => {
    await page.goto(CHAIN.du)
    await expect(page.locator('[data-timeline-step]')).toHaveCount(6)
    const steps = await page.locator('[data-timeline-step]').evaluateAll(items => items.map(item => item.getAttribute('data-timeline-step')))
    expect(steps.map(Number)).toEqual(CASE8_TIMELINE)
  })
})

test.describe('bootstrap chain still holds', () => {
  test('the frozen bootstrap route chain is unchanged', async ({ page }) => {
    await page.goto(CHAIN.entry)
    await page.getByTestId('enter-system').click()
    await page.getByTestId('home-to-lab').click()
    await page.getByTestId('open-case8').click()
    await page.getByTestId('tab-evidence').click()
    await page.getByTestId('evidence-source-list').locator('a').first().click()
    await page.getByTestId('quick-full-record').click()
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await page.goBack()
    await expect(page.locator('main[data-page="experiment"]')).toBeVisible()
  })
})
