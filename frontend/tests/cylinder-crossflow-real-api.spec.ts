import { test, expect } from '@playwright/test'
import { readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

for (const config of ['A_u', 'B_u', 'D_u']) {
  test(`Cylinder ${config}: exact tabs, selectors and five actual snapshots`, async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(`/lab/experiments/cylinder?config=${config}&tab=flow`)
    await expect(page.locator('main[data-page="cylinder"]')).toBeVisible()
    await expect(page.getByRole('tab')).toHaveText(['Overview', 'Flow', 'Entropy', 'Sector Allocation', 'Metrics', 'Evidence'])
    await expect(page.getByRole('group', { name: 'Cylinder config' }).getByRole('button')).toHaveText(['A_u', 'B_u', 'D_u'])
    await expect(page.getByTestId('config-C_u')).toHaveCount(0)
    await expect(page.getByTestId('snapshot-selector').locator('option')).toHaveCount(5)
    const steps = [0, 2439, 4878, 7318, 9757]
    for (let snapshot = 1; snapshot <= 5; snapshot++) {
      await page.getByTestId('snapshot-selector').selectOption(String(snapshot))
      await expect(page.getByTestId('snapshot-meta')).toContainText(`completed step=${steps[snapshot - 1]}`)
      await expect(page.getByTestId('snapshot-meta')).toContainText('physical time=')
      await expect(page.getByTestId('instantaneous-field')).toHaveAttribute('width', '128')
      await expect(page.getByTestId('instantaneous-field')).toHaveAttribute('height', '31')
      await expect(page.getByTestId('field-availability')).toContainText('radial_interior_pi_at: AVAILABLE')
    }
    await page.getByTestId('field-selector').selectOption('angular_interior_pi_at')
    await expect(page.getByTestId('instantaneous-field')).toHaveAttribute('height', '32')
    await page.getByTestId('field-selector').selectOption('density')
    await expect(page.locator('[data-state="missing"]')).toContainText('No saved instantaneous density')
    await expect(page.getByTestId('instantaneous-field')).toHaveCount(0)
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
    expect(errors).toEqual([])
  })
  test(`Cylinder ${config}: 16 trajectory sectors, front-band and cumulative2D Missing`, async ({ page }) => {
    await page.goto(`/lab/experiments/cylinder?config=${config}&tab=sectors`)
    await expect(page.getByTestId('angular-sector-chart')).toBeVisible()
    await expect(page.getByTestId('sector-table').locator('tbody tr')).toHaveCount(16)
    await expect(page.getByTestId('sector-allocation')).toContainText('trajectory-integrated · interior-only')
    await expect(page.getByTestId('front-band')).toContainText('REGION_SCALAR')
    await expect(page.getByTestId('front-band')).toContainText('Fraction:')
    await expect(page.getByTestId('front-band')).toContainText('mask.cylinder.fixed-front-band')
    await expect(page.getByTestId('front-band')).toContainText('Definition')
    await expect(page.getByTestId('cumulative-2d-missing')).toContainText('Unavailable / Missing')
    await expect(page.getByTestId('cumulative-2d-missing').locator('canvas')).toHaveCount(0)
    await expect(page.getByTestId('front-band').getByTestId('evidence-link').first()).toBeVisible()
    if (config === 'A_u') await expect(page.getByTestId('front-band')).toContainText('N/A (zero denominator)')
  })
}
test('Cylinder full 9757-record history retains scalar semantics and independent snapshot state', async ({ page }) => {
  const offsets: string[] = []
  page.on('request', r => { if (r.url().includes('/cylinder/configs/D_u/entropy-history')) offsets.push(new URL(r.url()).searchParams.get('offset') ?? '') })
  await page.goto('/lab/experiments/cylinder?config=D_u&tab=entropy&snapshot=3&step=123')
  await expect(page.getByTestId('cylinder-entropy-chart')).toBeVisible()
  await expect(page.locator('[data-point-count="9757"]')).toHaveCount(4)
  await expect(page.getByTestId('cylinder-history')).toContainText('source accepted interval start/end retained')
  await expect(page.getByTestId('cylinder-history')).toContainText('INTERIOR_ONLY')
  await expect(page.getByTestId('scalar-selected').first()).toContainText('completed step=123')
  await page.getByTestId('scalar-step').fill('9000')
  await expect(page).toHaveURL(/step=9000/)
  await page.getByTestId('tab-flow').click()
  await expect(page.getByTestId('snapshot-selector')).toHaveValue('3')
  await page.getByTestId('tab-entropy').click()
  await expect(page.getByTestId('scalar-selected').first()).toContainText('completed step=9000')
  expect(offsets).toContain('0'); expect(offsets).toContain('5000')
})
test('Cylinder local canonical metrics retain definitions, detectors, units, time and detector floor', async ({ page }) => {
  await page.goto('/lab/experiments/cylinder?config=D_u&tab=metrics')
  for (const id of ['cylinder_centerline_width', 'cylinder_front_mean_width', 'cylinder_front_RMS', 'cylinder_front_HF_RMS']) {
    const card = page.locator(`[data-metric="${id}"]`)
    await expect(card).toBeVisible()
    for (const phrase of ['Definition', 'Detector:', 'Unit', 'Time semantics', 'Limitation', 'View evidence']) await expect(card).toContainText(phrase)
  }
  await expect(page.locator('[data-metric="cylinder_front_mean_width"]')).toContainText('DETECTOR_LIMITED_SHARPNESS_READING')
  await expect(page.getByTestId('detector-floor').first()).toBeVisible()
})
test('Cylinder evidence return restores config, tab, snapshot, field and scalar state', async ({ page }) => {
  await page.goto('/lab/experiments/cylinder?config=B_u&tab=flow&snapshot=4&field=angular_interior_pi_at&step=123')
  await expect(page.getByTestId('instantaneous-field')).toBeVisible()
  await page.locator('figure').getByTestId('evidence-link').first().click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await expect(page.getByTestId('evidence-config')).toHaveText('B_u')
  await page.getByTestId('back-to-result').click()
  for (const [key, value] of Object.entries({ config: 'B_u', tab: 'flow', snapshot: '4', field: 'angular_interior_pi_at', step: '123' })) expect(new URL(page.url()).searchParams.get(key)).toBe(value)
  await expect(page.getByTestId('instantaneous-field')).toHaveAttribute('height', '32')
})
test('Cross-flow renders distinct scientific objects, policies, comparability and both evidence contexts', async ({ page }, info) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
  await page.goto('/cross-flow?case8_config=D_u&cylinder_config=B_u&view=allocation')
  await expect(page.getByTestId('descriptive-only')).toBeVisible()
  await expect(page.getByTestId('no-unified-ranking')).toBeVisible()
  const left = page.getByTestId('case8-side'), right = page.getByTestId('cylinder-side')
  await expect(left.getByTestId('face-allocation-canvas')).toHaveCount(2)
  await expect(left.getByTestId('angular-sector-chart')).toHaveCount(0)
  await expect(right.getByTestId('angular-sector-chart')).toBeVisible()
  await expect(right.getByTestId('face-allocation-canvas')).toHaveCount(0)
  await expect(right.getByTestId('front-band')).toBeVisible()
  await expect(right.getByTestId('cumulative-2d-missing')).toContainText('Missing')
  for (const word of ['Localization', 'HF', 'Width', 'Budget']) await expect(page.getByTestId('comparability-rules')).toContainText(word)
  await expect(page.getByTestId('cylinder-config').locator('option')).toHaveText(['A_u', 'B_u', 'D_u'])
  await page.screenshot({ path: info.outputPath('cross-flow-functional.png'), fullPage: true })
  await left.getByTestId('face-allocation-canvas').first().scrollIntoViewIfNeeded()
  await page.screenshot({ path: info.outputPath('cross-flow-renderers.png') })
  for (const side of [left, right]) {
    await side.getByTestId('evidence-link').first().click()
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await page.getByTestId('back-to-result').click()
    expect(new URL(page.url()).searchParams.get('case8_config')).toBe('D_u')
    expect(new URL(page.url()).searchParams.get('cylinder_config')).toBe('B_u')
    expect(new URL(page.url()).searchParams.get('view')).toBe('allocation')
  }
  await page.getByTestId('case8-config').selectOption('A_u')
  await expect(left).toContainText('No saved cumulative native-face allocation')
  await expect(left.getByTestId('face-allocation-canvas')).toHaveCount(0)
  await expect(right.getByTestId('angular-sector-chart')).toBeVisible()
  await page.reload()
  await expect(page.getByTestId('case8-config')).toHaveValue('A_u')
  await expect(page.getByTestId('cylinder-config')).toHaveValue('B_u')
  expect(errors).toEqual([])
})
for (const path of ['/lab/experiments/cylinder?tab=flow', '/lab/experiments/cylinder?tab=entropy', '/lab/experiments/cylinder?tab=sectors', '/lab/experiments/cylinder?tab=metrics', '/cross-flow']) {
  test(`API outage has no mock fallback: ${path}`, async ({ page }) => {
    await page.route('**/api/**', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ availability: 'ERROR', error: { message: 'Injected real API outage' } }) }))
    await page.goto(path)
    await expect(page.getByRole('alert').first()).toContainText('Injected real API outage')
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
    for (const id of ['instantaneous-field', 'angular-sector-chart', 'cylinder-entropy-chart', 'face-allocation-canvas']) await expect(page.getByTestId(id)).toHaveCount(0)
  })
}
test('field asset failure shows Missing without substituting another frame', async ({ page }) => {
  await page.route('**/cylinder/configs/D_u/snapshots/2/fields/**', route => route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ availability: 'MISSING', error: { message: 'Saved field unavailable' } }) }))
  await page.goto('/lab/experiments/cylinder?tab=flow&snapshot=2')
  await expect(page.locator('[data-state="missing"]')).toContainText('Saved field unavailable')
  await expect(page.getByTestId('instantaneous-field')).toHaveCount(0)
})
test('invalid snapshot and unsupported config deep links never create frames or C_u selector', async ({ page }) => {
  await page.goto('/lab/experiments/cylinder?config=C_u&tab=flow&snapshot=0')
  await expect(page.getByRole('alert')).toContainText('only recorded indices 1…5')
  await expect(page.getByTestId('config-C_u')).toHaveCount(0)
  await expect(page.getByTestId('instantaneous-field')).toHaveCount(0)
})
test('Lab navigation opens Cylinder and cross-flow routes', async ({ page }) => {
  await page.goto('/lab')
  await page.getByTestId('open-cylinder').click()
  await expect(page.locator('main[data-page="cylinder"]')).toBeVisible()
  await page.getByRole('link', { name: /Cross-flow Compare/ }).click()
  await expect(page.locator('main[data-page="cross-flow"]')).toBeVisible()
})
test('production bundle contains zero mock implementation or fixture identifiers', () => {
  const assets = fileURLToPath(new URL('../dist/assets', import.meta.url))
  const js = readdirSync(assets).filter(p => p.endsWith('.js')).map(p => readFileSync(`${assets}/${p}`, 'utf8')).join('\n')
  for (const marker of ['createMockProvider', 'MOCK_LAYOUT_ONLY', 'MOCK_SYNTHETIC_DATA', 'lim.mock.synthetic', 'mock.case8', 'mock.gate', 'mock.spectrum', 'mock.evidence', 'mockProvider', 'Synthetic Case8']) expect(js).not.toContain(marker)
})
test('Cylinder config changes retain selected tab and replace allocation identity', async ({ page }) => {
  await page.goto('/lab/experiments/cylinder?config=A_u&tab=sectors')
  for (const config of ['A_u', 'B_u', 'D_u']) {
    await page.getByTestId(`config-${config}`).click()
    await expect(page.getByTestId('front-band')).toContainText(`cylinder.${config}.metric.E_at_int`)
    await expect(page.getByTestId('cylinder-capability-gap')).toContainText('Unavailable / Missing')
    expect(new URL(page.url()).searchParams.get('tab')).toBe('sectors')
  }
})
