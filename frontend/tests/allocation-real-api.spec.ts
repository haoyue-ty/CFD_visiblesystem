import { test, expect } from '@playwright/test'

test('explicit allocation outage stays unsupported without a fake map', async ({ page }) => {
  await page.route('**/api/v1/allocations/**', route => route.fulfill({ status: 503,
    contentType: 'application/json', body: JSON.stringify({ availability: 'ERROR',
      error: { code: 'FEATURE_NOT_ENABLED', message: 'Allocation adapter has not been delivered' } }) }))
  await page.goto('/lab/experiments/case8?config=D_u&tab=allocation')
  await expect(page.getByTestId('case8-allocation')).toBeVisible()

  // The tab must NOT render a map from the real provider while the loader is off.
  await expect(page.getByTestId('allocation-map')).toHaveCount(0)
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(0)

  // It must show a real, explained state rather than silence.
  const unsupported = page.locator('[data-state="unsupported"]')
  const missing = page.locator('[data-state="missing"]')
  await expect(unsupported.or(missing).first()).toBeVisible()

  // Critically: no mock badge on the real provider (no cross-provider fallback).
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
})

test('real Lab -> Case8 -> Allocation -> D_u -> all Gates -> Evidence', async ({ page }, testInfo) => {
  test.setTimeout(90_000)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/lab')
  await page.getByTestId('open-case8').click()
  await page.getByTestId('config-D_u').click()
  await page.getByTestId('tab-allocation').click()
  await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
  await expect(page.getByTestId('alloc-representation-type')).toHaveText('FACE_FIELD')
  await expect(page.getByTestId('alloc-semantic-id')).toHaveText('Case8_face_Pi_at_integrated')
  await expect(page.getByTestId('alloc-mask-type')).toHaveText('CASE8_NATIVE_FACE_SHOCK_WINDOW')
  await expect(page.getByTestId('alloc-mask-counts')).toHaveText('640, 648')
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
  await expect(page.getByTestId('face-allocation-canvas').nth(0)).toHaveAttribute('width', '129')
  await expect(page.getByTestId('face-allocation-canvas').nth(1)).toHaveAttribute('width', '128')
  await expect(page.getByTestId('allocation-map')).toContainText('CARTESIAN_X_FACE')
  await expect(page.getByTestId('allocation-map')).toContainText('CARTESIAN_Y_FACE')
  await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(0)
  await expect(page.getByTestId('alloc-budget')).toHaveText('0.0027771079325925934')
  await expect(page.getByTestId('alloc-spatial-included')).toContainText('no')
  await expect(page.getByTestId('alloc-data-origin')).toHaveText('DIAGNOSTIC_RERUN')
  await page.screenshot({ path: testInfo.outputPath('du-face.png'), fullPage: true })
  await page.getByTestId('alloc-evidence').getByTestId('evidence-link').first().click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await expect(page.getByTestId('evidence-experiment')).toHaveText('case8')
  await expect(page.getByTestId('evidence-config')).toHaveText('D_u')
  // Phase11 also registers the actual unified method code as a distinct dependency.
  await expect(page.getByTestId('evidence-assets').locator('tbody tr')).toHaveCount(9)
  await expect(page.getByTestId('evidence-assets')).toContainText('solver/fluxes/cross_mode_ec_unified_v1.py')
  await expect(page.getByTestId('evidence-drift')).toHaveText('No')
  await page.getByTestId('back-to-result').click()
  await page.getByTestId('alloc-family-cell').click()
  const budgets: Record<string, string> = {
    Acoustic: '0.0028004425253788713', Pressure: '0.0028430539591530325', Ungated: '0.0028272752981764065',
  }
  for (const [config, budget] of Object.entries(budgets)) {
    await page.getByTestId(`alloc-gate-${config}`).click()
    await expect(page.getByTestId('alloc-identity')).toHaveText(`gate / ${config}`)
    await expect(page.getByTestId('alloc-representation-type')).toHaveText('CELL_FIELD')
    await expect(page.getByTestId('alloc-semantic-id')).toHaveText('Gate_cell_Pi_at_integrated')
    await expect(page.getByTestId('alloc-mask-type')).toHaveText('GATE_CELL_SHOCK_WINDOW')
    await expect(page.getByTestId('alloc-mask-id')).toHaveText('mask.gate.cell-window')
    await expect(page.getByTestId('alloc-mask-counts')).toHaveText('672')
    await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(1)
    await expect(page.getByTestId('cell-allocation-canvas')).toHaveAttribute('width', '128')
    await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(0)
    await expect(page.getByTestId('alloc-budget')).toHaveText(budget)
    await expect(page.getByTestId('alloc-integral-rule')).toHaveText('sum(values)=E_at')
    await expect(page.getByTestId('alloc-spatial-included')).toContainText('yes')
    await expect(page.getByTestId('alloc-data-origin')).toHaveText('FROZEN_PRODUCTION')
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
    await page.screenshot({ path: testInfo.outputPath(`${config}-cell.png`), fullPage: true })
    await page.getByTestId('alloc-evidence').getByTestId('evidence-link').first().click()
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await expect(page.getByTestId('evidence-experiment')).toHaveText('gate')
    await expect(page.getByTestId('evidence-config')).toHaveText(config)
    await expect(page.getByTestId('evidence-params')).toContainText('q_at')
    await expect(page.getByTestId('evidence-assets').locator('tbody tr')).toHaveCount(6)
    await expect(page.getByTestId('evidence-assets')).toContainText('solver/fluxes/cross_mode_ec_unified_v1.py')
    await expect(page.getByTestId('evidence-verification')).toContainText('FROZEN_VERIFIED')
    await expect(page.getByTestId('evidence-drift')).toHaveText('No')
    await page.getByTestId('back-to-result').click()
    await expect(page.getByTestId('alloc-identity')).toHaveText(`gate / ${config}`)
  }
  expect(errors).toEqual([])
})

for (const mutation of ['representation', 'semantic', 'mask', 'measure']) {
  test(`rejects an API ${mutation} mismatch without drawing a field`, async ({ page }) => {
    await page.route('**/api/v1/allocations/case8.D_u.allocation/metadata', async route => {
      const response = await route.fetch()
      const payload = await response.json()
      if (mutation === 'representation') payload.data.representation_type = 'CELL_FIELD'
      if (mutation === 'semantic') payload.data.semantic_id = 'Gate_cell_Pi_at_integrated'
      if (mutation === 'mask') payload.data.masks[0].id = 'mask.gate.cell-window'
      if (mutation === 'measure') payload.data.measure.includes_spatial_measure = true
      await route.fulfill({ response, json: payload })
    })
    await page.goto('/lab/experiments/case8?config=D_u&tab=allocation')
    await expect(page.getByTestId('case8-allocation').getByRole('alert')).toBeVisible()
    await expect(page.getByTestId('allocation-map')).toHaveCount(0)
  })
}
