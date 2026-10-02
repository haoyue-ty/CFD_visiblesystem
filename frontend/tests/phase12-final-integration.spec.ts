import { test, expect } from '@playwright/test'

test('V1 Lab catalog opens all six delivered experiments from production API', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(String(e)))
  for (const [id, ready] of [['case8', 'config-D_u'], ['gate', 'cell-allocation-canvas'], ['entropy-closure', 'closure-run'],
    ['spectrum', 'spectral-curve-canvas'], ['modal-validation', 'growth-validation-canvas'], ['cylinder', 'config-D_u']] as const) {
    await page.goto('/home')
    await page.getByRole('navigation', { name: 'System navigation' }).getByRole('link', { name: 'Lab', exact: true }).click()
    await expect(page.getByTestId(`lab-delivery-${id}`)).toHaveText('IMPLEMENTED')
    await page.getByTestId(`open-${id}`).click()
    await expect(page.getByTestId(ready).first()).toBeVisible()
    await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
    await page.reload()
    await expect(page.getByTestId(ready).first()).toBeVisible()
  }
  expect(errors).toEqual([])
})

test('V1 config-disabled Allocation keeps URL, explanation, Back/Forward and no invented field', async ({ page }) => {
  await page.goto('/lab/experiments/case8?config=D_u&tab=overview')
  await expect(page.getByTestId('case8-independent-workspace-note')).toContainText('no recorded spectral capability')
  await expect(page.getByRole('tablist', { name: 'Case8 tabs' }).getByRole('tab', { name: 'Spectral' })).toHaveCount(0)
  await page.getByTestId('tab-spectral').click()
  await expect(page.getByTestId('spectral-curve-canvas')).toBeVisible()
  await expect(page.getByTestId('spectral-note')).toContainText('not Case8 data')
  await page.goto('/lab/experiments/case8?config=D_u&tab=allocation')
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
  await page.getByTestId('config-A_u').click()
  await expect(page).toHaveURL(/config=A_u.*tab=allocation/)
  await expect(page.getByTestId('tab-allocation')).toBeDisabled()
  await expect(page.getByTestId('allocation-disabled-reason')).toContainText('only D_u')
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(0)
  await page.goBack()
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
  await page.goForward()
  await page.reload()
  await expect(page.getByTestId('allocation-disabled-reason')).toBeVisible()
  await expect(page.getByTestId('tab-allocation')).toBeDisabled()
})

for (const id of ['gate', 'spectrum', 'modal-validation']) {
  test(`V1 ${id} hides absent capabilities and preserves unsupported deep link`, async ({ page }) => {
    await page.goto(`/lab/experiments/${id}?tab=flow`)
    await expect(page.getByTestId('unsupported-tab')).toContainText('UNSUPPORTED')
    await expect(page.getByTestId('tab-flow')).toHaveCount(0)
    await expect(page.getByTestId('tab-entropy')).toHaveCount(0)
    await expect(page).toHaveURL(/tab=flow/)
    await page.getByTestId('tab-overview').click()
    await page.getByTestId('tab-evidence').click()
    await page.getByTestId('evidence-link').first().click()
    await expect(page.getByTestId('evidence-quick-view')).toBeVisible()
    await page.getByTestId('quick-full-record').click()
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await page.reload()
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await page.getByTestId('back-to-result').click()
    await expect(page.getByTestId('tab-evidence')).toHaveAttribute('aria-selected', 'true')
  })
}

test('V1 metadata API failure preserves location and explicit error without scientific fallback', async ({ page }) => {
  await page.route('**/api/v1/experiments/spectrum', route => route.fulfill({ status: 503, contentType: 'application/json',
    body: JSON.stringify({ availability: 'ERROR', error: { message: 'Acceptance injected metadata outage' } }) }))
  await page.goto('/lab/experiments/spectrum?spectral_mode=8')
  await expect(page.locator('body')).toContainText('Acceptance injected metadata outage')
  await expect(page).toHaveURL(/spectral_mode=8/)
  await expect(page.getByTestId('spectral-curve-canvas')).toHaveCount(0)
  await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
})

for (const id of ['case8', 'cylinder', 'entropy-closure']) {
  test(`V1 ${id} unknown view remains an explicit unsupported location`, async ({ page }) => {
    await page.goto(`/lab/experiments/${id}?tab=unrecorded-view`)
    await expect(page.getByTestId('unsupported-tab')).toBeVisible()
    await expect(page).toHaveURL(/tab=unrecorded-view/)
    await expect(page.locator('canvas')).toHaveCount(0)
  })
}
