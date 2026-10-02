import { test, expect, type Page, type APIRequestContext } from '@playwright/test'
import type { components } from '../src/types/generated/api'
type Record = components['schemas']['EvidenceRecord']
async function dto(request: APIRequestContext, id = 'ev.case8.D_u.allocation'): Promise<Record> {
  const response = await request.get(`/api/v1/evidence/${id}`)
  expect(response.status()).toBe(200)
  return (await response.json()).data
}
async function openRecord(page: Page, id = 'ev.case8.D_u.allocation') {
  await page.goto(`/evidence/${id}`)
  await expect(page.getByTestId('evidence-record')).toBeVisible()
}

test('Evidence navigation opens CURRENT with bounded EVI01 pagination and server filters', async ({ page }, info) => {
  const calls: URL[] = []
  page.on('request', r => { const u = new URL(r.url()); if (u.pathname === '/api/v1/evidence') calls.push(u) })
  await page.goto('/home')
  await page.getByRole('navigation', { name: 'System navigation' }).getByRole('link', { name: 'Evidence', exact: true }).click()
  await expect(page.getByTestId('evidence-CURRENT')).toBeVisible()
  await expect(page.getByTestId('evidence-card')).toHaveCount(20)
  await expect(page.getByTestId('evidence-GAPS')).toHaveCount(0)
  await expect(page.getByTestId('evidence-HISTORY')).toHaveCount(0)
  await page.screenshot({ path: info.outputPath('evidence-current.png') })
  await page.getByTestId('evidence-next').click()
  await expect(page.getByTestId('evidence-page-range')).toContainText('21–40')
  await page.getByTestId('evidence-drift-filter').selectOption('FALSE')
  await expect(page).toHaveURL(/offset=20/)
  await expect(page.getByTestId('evidence-page-range')).toContainText('21–40')
  await page.getByTestId('evidence-previous').click()
  await expect(page.getByTestId('evidence-page-range')).toContainText('1–20')
  await page.getByTestId('evidence-experiment-filter').selectOption('gate')
  await expect(page.getByTestId('evidence-card')).toHaveCount(3)
  await page.getByTestId('evidence-status-filter').selectOption('FROZEN_VERIFIED')
  await expect(page.getByTestId('evidence-card')).toHaveCount(3)
  await expect(page.getByTestId('evidence-next')).toBeDisabled()
  expect(calls.some(u => u.searchParams.get('offset') === '20')).toBe(true)
  expect(calls.some(u => u.searchParams.get('experiment_id') === 'gate' && u.searchParams.get('status') === 'FROZEN_VERIFIED')).toBe(true)
  expect(calls.every(u => u.searchParams.get('limit') === '20' && u.searchParams.get('section') === 'CURRENT')).toBe(true)
  await expect(page.getByTestId('evidence-card').first()).not.toContainText(/\b[a-f0-9]{64}\b/)
  await page.reload()
  await expect(page.getByTestId('evidence-experiment-filter')).toHaveValue('gate')
})

test('GAPS exposes actual missing sources, effects and limits without repair actions', async ({ page }) => {
  await page.goto('/evidence')
  await page.getByTestId('section-GAPS').click()
  await expect(page.getByTestId('evidence-card')).toHaveCount(11)
  for (const label of ['Cylinder cumulative 2D', 'Near-1D five-epsilon authoritative raw', 'Spectrum serialized matrices']) {
    const card = page.getByTestId('evidence-card').filter({ has: page.getByRole('heading', { name: label, exact: true }) })
    await expect(card).toContainText('MISSING')
    await expect(card).toContainText('Why missing / limited:')
    await expect(card).toContainText('Affects:')
    await expect(card).toContainText('Does not affect:')
  }
  await expect(page.getByRole('button', { name: /^(Generate|Reconstruct|Interpolate|Fill)$/i })).toHaveCount(0)
  await expect(page.getByTestId('evidence-CURRENT')).toHaveCount(0)
})

test('HISTORY is a separate historical selection; details return exact center filters/page', async ({ page }) => {
  await page.goto('/evidence?section=HISTORY&status=SUPERSEDED&offset=20')
  await expect(page.getByTestId('evidence-HISTORY')).toContainText('not current formal results')
  await expect(page.getByTestId('evidence-card').first()).toContainText('HISTORY / SUPERSEDED')
  const original = page.url()
  await page.getByTestId('evidence-card').first().getByRole('link', { name: /View details/ }).click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await expect(page.getByTestId('evidence-verification')).toContainText('SUPERSEDED')
  await expect(page.getByTestId('evidence-historical')).toBeVisible()
  await page.getByTestId('back-to-result').click()
  await expect(page).toHaveURL(original)
})

test('P09 renders complete canonical method/config/assets/freeze/processing/definitions/limitations/relations', async ({ page, request }, info) => {
  const record = await dto(request)
  await openRecord(page)
  await expect(page.getByTestId('evidence-method')).toContainText(record.method_hash.state === 'KNOWN' ? record.method_hash.value : record.method_hash.reason)
  await expect(page.getByTestId('evidence-params')).toContainText('q_aa')
  for (const key of ['q_at', 'gate', 'grid', 'CFL', 'final_time', 'integrator']) await expect(page.getByTestId('evidence-params')).toContainText(key)
  await expect(page.getByTestId('evidence-source-asset')).toHaveCount(record.source_assets.length)
  for (const asset of record.source_assets) {
    const block = page.getByTestId('evidence-source-asset').filter({ has: page.getByRole('heading', { name: asset.asset_id, exact: true }) })
    for (const value of [asset.role, asset.source_display, asset.format, 'Recorded data hash', 'Current data hash', 'Canonical selected']) await expect(block).toContainText(value)
  }
  await expect(page.getByTestId('evidence-freeze')).toContainText('Manifest identity')
  await expect(page.getByTestId('evidence-freeze')).toContainText('Unknown')
  await expect(page.getByTestId('evidence-processing')).toContainText(record.processing[0]!.description)
  await expect(page.getByTestId('evidence-definitions')).toContainText(record.definitions[0]!.time_rule)
  await expect(page.getByTestId('evidence-definitions')).toContainText(record.definitions[0]!.spatial_rule)
  await expect(page.getByTestId('evidence-limitations')).toContainText(record.limitations[0]!.description)
  await expect(page.getByTestId('evidence-relations').getByRole('link', { name: 'ev.method.unified-v1', exact: true })).toBeVisible()
  await page.screenshot({ path: info.outputPath('evidence-detail.png') })
})

test('drift response remains inspectable, with distinct recorded/current facts and no availability claim', async ({ page, request }) => {
  const record = await dto(request)
  record.source_drift = { state: 'KNOWN', value: true }
  record.current_source_hash = { state: 'KNOWN', value: 'f'.repeat(64) }
  record.source_assets[0]!.data_drift = { state: 'KNOWN', value: true }
  record.source_assets[0]!.current_data_hash = { state: 'KNOWN', value: 'e'.repeat(64) }
  await page.route('**/api/v1/evidence/ev.case8.D_u.allocation', r => r.fulfill({ json: { availability: 'AVAILABLE', data: record } }))
  await openRecord(page)
  await expect(page.getByRole('alert').first()).toContainText('SOURCE DRIFT')
  await expect(page.getByTestId('current-source-hash')).toHaveText('f'.repeat(64))
  await expect(page.getByTestId('evidence-method')).toContainText('Recorded source hash')
  await expect(page.getByTestId('evidence-inspectability')).toContainText('does not establish Numerical Result Available')
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
})

test('source drift filters the current server page honestly without a forbidden query', async ({ page, request }) => {
  const data = (await (await request.get('/api/v1/evidence?section=CURRENT&experiment_id=gate&limit=20')).json()).data
  data.items[0].source_drift = { state: 'KNOWN', value: true }
  data.items[1].source_drift = { state: 'UNKNOWN', reason: 'No baseline' }
  const urls: string[] = []
  await page.route('**/api/v1/evidence?*', r => { urls.push(r.request().url()); return r.fulfill({ json: { availability: 'AVAILABLE', data } }) })
  await page.goto('/evidence?experiment=gate')
  await expect(page.getByTestId('evidence-card')).toHaveCount(3)
  await page.getByTestId('evidence-drift-filter').selectOption('TRUE')
  await expect(page.getByTestId('evidence-card')).toHaveCount(1)
  await expect(page.getByTestId('evidence-card')).toContainText('SOURCE DRIFT')
  await page.getByTestId('evidence-drift-filter').selectOption('UNKNOWN')
  await expect(page.getByTestId('evidence-card')).toHaveCount(1)
  await page.getByTestId('evidence-drift-filter').selectOption('FALSE')
  await expect(page.getByTestId('evidence-card')).toHaveCount(1)
  expect(urls.every(u => !new URL(u).searchParams.has('source_drift'))).toBe(true)
  await expect(page.getByText(/source drift filters the current server page only/)).toBeVisible()
})

test('public text strips unsafe locators; all links are application routes and never downloads', async ({ page, request }) => {
  const record = await dto(request)
  record.source_assets[0]!.source_display = 'source D:\\science\\secret.npz file:///D:/science/secret.npz'
  record.source_assets[0]!.relative_origin = { state: 'KNOWN', value: 'D:/science/secret.npz' }
  await page.route('**/api/v1/evidence/ev.case8.D_u.allocation', r => r.fulfill({ json: { availability: 'AVAILABLE', data: record } }))
  await openRecord(page)
  await expect(page.getByTestId('evidence-record')).toContainText('[source locator withheld]')
  await expect(page.locator('a[href^="file:"], a[href^="D:"], a[download]')).toHaveCount(0)
  expect(await page.getByTestId('evidence-record').innerText()).not.toMatch(/D:[\\/]|file:\/\//)
})

test('known superseded_by links to registered successor; unknown fields are never inferred', async ({ page, request }) => {
  const record = await dto(request)
  record.superseded_by = { state: 'KNOWN', value: 'ev.method.unified-v1' }
  record.config = { state: 'UNKNOWN', reason: 'Configuration was not recorded' }
  record.freeze_reference = { state: 'UNKNOWN', reason: 'Freeze was not recorded' }
  await page.route('**/api/v1/evidence/ev.case8.D_u.allocation', r => r.fulfill({ json: { availability: 'AVAILABLE', data: record } }))
  await openRecord(page)
  await expect(page.getByTestId('evidence-configuration')).toContainText('Unknown — Configuration was not recorded')
  await expect(page.getByTestId('evidence-params')).not.toContainText('0.396')
  await expect(page.getByTestId('evidence-freeze')).toContainText('Unknown — Freeze was not recorded')
  await page.getByRole('link', { name: 'ev.method.unified-v1 → associated successor evidence' }).click()
  await expect(page).toHaveURL(/\/evidence\/ev.method.unified-v1/)
})

for (const [url, stateId, stateText] of [
  ['/lab/experiments/case8?config=D_u&tab=allocation', 'allocation-view', ''],
  ['/lab/experiments/case8?config=D_u&tab=spectral&spectral_q=spectrum.q-0.396&spectral_mode=8', 'mode-index', '8'],
  ['/explore?scene=6&case8_config=D_u&cylinder_config=B_u&view=allocation', 'scene-progress', 'Scene 6 / 7'],
] as const) {
  test(`Quick close, Quick→Detail, Detail→Result and browser Back preserve ${url}`, async ({ page }, info) => {
    await page.goto(url)
    if (stateText) await expect(page.getByTestId(stateId)).toHaveText(stateText)
    else await expect(page.getByTestId('face-allocation-canvas').first()).toBeVisible()
    const original = page.url()
    const link = page.getByTestId('evidence-link').first()
    await link.click()
    await expect(page.getByTestId('evidence-quick-view')).toContainText('Result identity:')
    await expect(page.getByTestId('evidence-quick-view')).toContainText('Source summary:')
    await page.screenshot({ path: info.outputPath('evidence-quick-view.png') })
    await expect(page).toHaveURL(original)
    await page.getByTestId('quick-close').click()
    await expect(link).toBeFocused()
    await expect(page).toHaveURL(original)
    await link.click()
    await page.getByTestId('quick-full-record').click()
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await expect(page.getByTestId('evidence-quick-view')).toHaveCount(0)
    await page.getByTestId('back-to-result').click()
    await expect(page).toHaveURL(original)
    if (stateText) await expect(page.getByTestId(stateId)).toHaveText(stateText)
    await page.getByTestId('evidence-link').first().click()
    await page.getByTestId('quick-full-record').click()
    await page.goBack()
    await expect(page).toHaveURL(original)
    if (stateText) await expect(page.getByTestId(stateId)).toHaveText(stateText)
  })
}

test('Quick View traps focus, Escape closes, and changing route aborts stale evidence', async ({ page }) => {
  await page.goto('/lab/experiments/case8?config=D_u&tab=allocation')
  const link = page.getByTestId('evidence-link').first()
  await link.click()
  await expect(page.getByTestId('quick-close')).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(page.getByTestId('quick-full-record')).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByTestId('quick-close')).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByTestId('evidence-quick-view')).toHaveCount(0)
  await expect(link).toBeFocused()
  await link.click()
  await page.goto('/evidence')
  await expect(page.getByTestId('evidence-quick-view')).toHaveCount(0)
})

test('Mechanism own EVI03 evidence is non-numerical in Quick and P09', async ({ page }) => {
  await page.goto('/lab/mechanism?state=WEAKLY_2D&q_at=OFF&node=tangential-output')
  await page.locator('a[data-testid="evidence-link"][href*="ev.mechanism.theory-implementation"]').click()
  await expect(page.getByTestId('quick-non-numerical')).toContainText('NON-NUMERICAL EVIDENCE')
  await expect(page.getByTestId('quick-identity')).toContainText('No numerical result identity')
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-non-numerical')).toBeVisible()
  await expect(page.getByTestId('evidence-result-context')).toHaveCount(0)
})

test('Cylinder missing cumulative evidence stays MISSING and inspectable', async ({ page }) => {
  await openRecord(page, 'ev.missing.cylinder-cumulative2d')
  await expect(page.getByTestId('evidence-verification')).toContainText('MISSING')
  await expect(page.getByTestId('evidence-limitations')).toContainText('without full-trajectory 2D')
})

test('Closure evidence exposes recorded run and actual stage processing', async ({ page }) => {
  await openRecord(page, 'ev.entropy-closure.D_u-cfl-0.05.stage')
  await expect(page.getByTestId('evidence-config')).toHaveText('D_u-cfl-0.05')
  await expect(page.getByTestId('evidence-result-context').first()).toContainText('PER_STAGE')
  await expect(page.getByTestId('evidence-processing')).toContainText('FORMAT_MAPPING')
})

for (const [path, target] of [['/evidence', 'evidence index'], ['/evidence/ev.case8.D_u.allocation', 'evidence record']] as const) {
  for (const fault of ['http', 'network'] as const) test(`${target} ${fault} error is explicit and retry uses real API without fallback`, async ({ page }) => {
    const pattern = target === 'evidence index' ? '**/api/v1/evidence?*' : '**/api/v1/evidence/ev.case8.D_u.allocation'
    await page.route(pattern, r => fault === 'network' ? r.abort('failed') : r.fulfill({ status: 500, json: { availability: 'ERROR', error: { message: 'Registered source unavailable' } } }))
    await page.goto(path)
    await expect(page.getByRole('alert')).toContainText(`Error loading ${target}`)
    await expect(page.getByTestId('evidence-card')).toHaveCount(0)
    await expect(page.getByTestId('evidence-record')).toHaveCount(0)
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
    await page.unroute(pattern)
    await page.getByRole('button', { name: `Retry ${target}` }).click()
    await expect(page.getByTestId(target === 'evidence index' ? 'evidence-card' : 'evidence-record').first()).toBeVisible()
  })
}

test('Quick evidence API outage does not fabricate record; close preserves live result', async ({ page }) => {
  await page.goto('/lab/experiments/case8?config=D_u&tab=allocation')
  await expect(page.getByTestId('face-allocation-canvas').first()).toBeVisible()
  const original = page.url()
  await page.route('**/api/v1/evidence/**', r => r.abort('failed'))
  await page.getByTestId('evidence-link').first().click()
  await expect(page.getByRole('alert')).toContainText('Error loading evidence quick view')
  await expect(page.getByTestId('quick-identity')).toHaveCount(0)
  await page.getByTestId('quick-close').click()
  await expect(page).toHaveURL(original)
  await expect(page.getByTestId('face-allocation-canvas').first()).toBeVisible()
})

test('Allocation family, gate and comparison survive full record, browser Back and reload', async ({ page }) => {
  await page.goto('/lab/experiments/case8?config=D_u&tab=allocation')
  await page.getByTestId('alloc-family-cell').click()
  await page.getByTestId('alloc-gate-Ungated').click()
  await page.getByRole('button', { name: 'Open matched Gate comparison', exact: true }).click()
  await expect(page.getByTestId('gate-comparison')).toBeVisible()
  await expect(page).toHaveURL(/allocation_comparison=true/)
  const original = page.url()
  await page.getByTestId('alloc-evidence').getByTestId('evidence-link').first().click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-config')).toHaveText('Ungated')
  await page.goBack()
  await expect(page).toHaveURL(original)
  await expect(page.getByTestId('alloc-family-cell')).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByTestId('alloc-gate-Ungated')).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByTestId('gate-comparison')).toBeVisible()
  await page.reload()
  await expect(page.getByTestId('alloc-gate-Ungated')).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByTestId('gate-comparison')).toBeVisible()
})

test('unknown evidence ID has explicit missing state and no fabricated metadata', async ({ page }) => {
  await page.goto('/evidence/ev.unknown.window2')
  await expect(page.getByTestId('evidence-fallback')).toBeVisible()
  await expect(page.getByTestId('evidence-record')).toHaveCount(0)
})
