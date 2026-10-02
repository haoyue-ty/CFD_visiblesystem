import { test, expect } from '@playwright/test'

test('real vertical slice and four-configuration acceptance', async ({ page }) => {
  // This single test loads five full real histories plus the complete navigation chain.
  test.setTimeout(90_000)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await page.getByTestId('enter-system').click()
  await page.getByTestId('home-to-lab').click()
  await page.getByTestId('open-case8').click()
  await expect(page.locator('main h1')).toHaveText('Case8 — D_u')
  await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
  await page.getByTestId('tab-flow').click()
  await page.getByTestId('snapshot-6').click()
  await page.getByTestId('field-density').click()
  await expect(page.getByTestId('snapshot-step')).toHaveText('1912')
  await expect(page.getByTestId('snapshot-physical-time')).toHaveText('0.08')
  await expect(page.getByTestId('snapshot-canvas')).toHaveAttribute('width', '128')
  await expect(page.getByTestId('snapshot-canvas')).toHaveAttribute('height', '32')
  await page.getByTestId('tab-entropy').click()
  await expect(page.locator('[data-field="total-point-count"]')).toHaveText('1912')
  await page.getByTestId('scalar-step-input').fill('1200')
  await page.getByTestId('scalar-step-apply').click()
  await expect(page.getByTestId('dual-time-notice')).toBeVisible()
  await page.getByTestId('tab-metrics').click()
  await expect(page.getByTestId('metrics-panel')).toContainText('MULTI_SNAPSHOT')
  await page.getByTestId('evidence-link').first().click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await expect(page.getByTestId('evidence-config')).toHaveText('D_u')
  await expect(page.getByTestId('evidence-verification')).not.toContainText('FROZEN_VERIFIED')
  await page.getByTestId('back-to-result').click()
  await expect(page).toHaveURL(url => url.searchParams.get('config') === 'D_u' && url.searchParams.get('tab') === 'metrics')

  let snapshots = 0
  let rows = 0
  for (const config of ['A_u', 'B_u', 'C_u', 'D_u']) {
    await page.getByTestId(`config-${config}`).click()
    await page.getByTestId('tab-flow').click()
    await expect(page.getByTestId('snapshot-label')).toHaveText('Snapshot 6 / 6')
    await expect(page.locator('[data-timeline-step]')).toHaveCount(6)
    snapshots += await page.locator('[data-timeline-step]').count()
    await expect(page.getByTestId('snapshot-canvas')).toBeVisible()
    await expect(page.locator('[data-origin="MOCK"]')).toHaveCount(0)
    const historyResponse = page.waitForResponse(response => response.url().includes(`/configs/${config}/entropy-history`) && response.url().includes('limit=2000'))
    await page.getByTestId('tab-entropy').click()
    const response = await historyResponse
    expect(response.ok()).toBeTruthy()
    const history = (await response.json()).data
    expect(history.config_id).toBe(config)
    for (const series of history.series) {
      expect(series.total_point_count).toBe(1912)
      expect(series.points).toHaveLength(1912)
      expect(series.result.data_origin).toBe('VERIFIED_PRODUCTION')
      expect(series.result.result_id).not.toMatch(/^mock\./)
    }
    rows += history.series[0].total_point_count
    await expect(page.locator('[data-field="total-point-count"]')).toHaveText('1912')
  }
  expect(snapshots).toBe(24)
  expect(rows).toBe(7648)
  expect(errors).toEqual([])
})

test('real API outage shows an error without a mock fallback', async ({ page }) => {
  await page.route('**/api/v1/**', route => route.abort())
  await page.goto('/lab/experiments/case8?config=D_u&tab=flow')
  await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByTestId('snapshot-canvas')).toHaveCount(0)
  await expect(page.locator('[data-origin="MOCK"]')).toHaveCount(0)
})
