import { test, expect, type Page } from '@playwright/test'
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
const base = '/lab/experiments/entropy-closure'
const legal = ['D_u-cfl-0.2', 'D_u-cfl-0.1', 'D_u-cfl-0.05', 'D_u-cfl-0.025', 'B_u-cfl-0.05']
const output = fileURLToPath(new URL('../../.cache/phase9-closure/', import.meta.url))
async function open(page: Page, run = legal[0], tab = 'overview', offset = 0) {
  await page.goto(`${base}?run=${run}&tab=${tab}&offset=${offset}`)
  await expect(page.getByTestId('closure-run')).toHaveValue(run)
}
test('Lab opens Closure and traverses D_u .05 stages, steps, Evidence and B_u recorded zero', async ({ page }) => {
  await page.goto('/lab')
  await page.getByTestId('open-entropy-closure').click()
  await expect(page.getByTestId('closure-run')).toBeVisible()
  await page.getByTestId('closure-run').selectOption(legal[2])
  await page.getByTestId('tab-semi-discrete').click()
  await expect(page.getByTestId('closure-history')).toHaveAttribute('data-granularity', 'PER_STAGE')
  await page.getByTestId('tab-fully-discrete').click()
  await expect(page.getByTestId('closure-history')).toHaveAttribute('data-granularity', 'PER_STEP')
  await expect(page.getByTestId('refinement-table').locator('tbody tr')).toHaveCount(4)
  await expect(page.getByTestId('closure-refinement').getByRole('img')).toHaveAttribute('data-point-count', '4')
  await page.locator('a[data-testid="evidence-link"][href*="ev.entropy-closure.D_u.temporal-refinement"]').click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await page.getByTestId('back-to-result').click()
  await expect(page.getByTestId('tab-fully-discrete')).toHaveAttribute('aria-selected', 'true')
  await page.getByTestId('tab-evidence').click()
  await page.locator(`a[data-testid="evidence-link"][href*="ev.entropy-closure.${legal[2]}.run"]`).first().click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-config')).toHaveText(legal[2])
  await page.getByTestId('back-to-result').click()
  await page.getByTestId('closure-run').selectOption(legal[4])
  await page.getByTestId('tab-semi-discrete').click()
  await expect(page.getByTestId('bu-zero-channel')).toContainText('recorded zero channel')
  await expect(page.getByTestId('closure-history')).toHaveAttribute('data-granularity', 'PER_STAGE')
  await page.getByRole('checkbox', { name: 'D_at', exact: true }).check()
  await expect(page.locator('[data-series="D_at"] td').first()).toHaveText('0')
})

test('CLO01 supplies exactly five complete legal selections; every run is selectable', async ({ page, request }) => {
  const response = await request.get('/api/v1/experiments/entropy-closure/runs')
  expect(response.ok()).toBe(true)
  const registry = (await response.json()).data
  expect(registry.runs.map((r: { run_id: string }) => r.run_id)).toEqual(legal)
  await open(page)
  const selector = page.getByTestId('closure-run')
  expect(await selector.locator('option').evaluateAll(nodes => nodes.map(n => (n as HTMLOptionElement).value))).toEqual(legal)
  await expect(selector.locator('option')).toHaveText(['D_u — CFL 0.2', 'D_u — CFL 0.1', 'D_u — CFL 0.05', 'D_u — CFL 0.025', 'B_u — CFL 0.05'])
  await expect(page.locator('select')).toHaveCount(1)
  for (const run of legal) { await selector.selectOption(run); await expect(page.getByTestId('selected-run')).toContainText(registry.runs.find((r: { run_id: string }) => r.run_id === run).step_point_count.toString()) }
})
test('invalid config × CFL deep link produces no history request or result', async ({ page }) => {
  const histories: string[] = []
  page.on('request', r => { if (r.url().includes('-history')) histories.push(r.url()) })
  await page.goto(`${base}?run=B_u-cfl-0.1&tab=semi-discrete`)
  await expect(page.getByTestId('invalid-run')).toBeVisible()
  await expect(page.getByTestId('closure-history')).toHaveCount(0)
  expect(histories).toEqual([])
})
test('Semi-discrete preserves PER_STAGE records, clocks, definitions and optional channels', async ({ page, request }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
  await open(page, legal[0], 'semi-discrete')
  await expect(page.getByTestId('closure-history')).toHaveAttribute('data-granularity', 'PER_STAGE')
  await expect(page.getByTestId('stage-clock')).toContainText('3 RK stages per accepted step')
  await expect(page.getByTestId('stage-clock')).toContainText('NOT_ESTABLISHED')
  await expect(page.getByRole('img', { name: 'G, -D_total (display sign only)', exact: true })).toHaveAttribute('data-point-count', '1000')
  const raw = (await (await request.get(`/api/v1/experiments/entropy-closure/runs/${legal[0]}/stage-history?limit=1000`)).json()).data
  for (const field of ['G', 'D_total', 'R_SD', 'eps_SD']) {
    const s = raw.series.find((s: { series_id: string }) => s.series_id === field)
    await expect(page.locator(`[data-series="${field}"] td`).first()).toHaveText(String(s.points[0].value.value))
  }
  for (const field of ['D_bg', 'D_aa', 'D_at', 'R_decomp']) { await page.getByRole('checkbox', { name: field, exact: true }).check(); await expect(page.locator(`[data-series="${field}"]`)).toBeVisible() }
  await page.getByTestId('record-selector').fill('2')
  await expect(page.getByTestId('record-clock')).toContainText('accepted step=1 · source stage=3')
  await page.getByTestId('history-next').click()
  await expect(page.getByTestId('history-range')).toContainText('1001–2000')
  await expect(page.getByTestId('record-clock')).toContainText('accepted step=334 · source stage=2')
  expect(errors).toEqual([])
  mkdirSync(output, { recursive: true }); await page.screenshot({ path: `${output}semi-discrete.png`, fullPage: true })
})
test('Fully-discrete keeps increments, cumulative and terminal values distinct through final page', async ({ page, request }) => {
  await open(page, legal[0], 'fully-discrete')
  await expect(page.getByTestId('closure-history')).toHaveAttribute('data-granularity', 'PER_STEP')
  const raw = (await (await request.get(`/api/v1/experiments/entropy-closure/runs/${legal[0]}/step-history?limit=1`)).json()).data
  for (const field of ['DeltaS', 'E_obs_step', 'R_time_step', 'R_time_cumulative', 'E_bg_step', 'E_aa_step', 'E_at_step', 'E_total_independent_step']) {
    const s = raw.series.find((s: { series_id: string }) => s.series_id === field)
    await expect(page.locator(`[data-series="${field}"] td`).first()).toHaveText(String(s.points[0].value.value))
    await expect(page.locator(`[data-series="${field}"] td`).nth(2)).toHaveText(s.aggregation)
  }
  await expect(page.getByTestId('terminal-summary')).toContainText('R_total')
  await page.getByTestId('history-last').click()
  await expect(page.getByTestId('history-next')).toBeDisabled()
  const count = raw.series[0].total_point_count
  await expect(page.getByTestId('history-range')).toContainText(`of ${count}`)
  await page.getByTestId('record-selector').fill(String((count - 1) % 1000))
  const terminalText = await page.locator('[data-metric="R_total"] td').first().innerText()
  await expect(page.locator('[data-series="R_time_cumulative"] td').first()).toHaveText(terminalText)
  mkdirSync(output, { recursive: true }); await page.screenshot({ path: `${output}fully-discrete.png`, fullPage: true })
})
test('B_u D_at and E_at are recorded zeros, never missing', async ({ page }) => {
  await open(page, legal[4], 'semi-discrete')
  await expect(page.getByTestId('bu-zero-channel')).toHaveText('D_at=0 — recorded zero channel. E_at step increments and terminal total are recorded zero.')
  await page.getByRole('checkbox', { name: 'D_at', exact: true }).check()
  await expect(page.locator('[data-series="D_at"] td').first()).toHaveText('0')
  await page.getByTestId('tab-fully-discrete').click()
  await expect(page.locator('[data-series="E_at_step"] td').first()).toHaveText('0')
  await expect(page.locator('[data-metric="E_at_total"] td').first()).toHaveText('0')
})
test('four-point refinement and global/pairwise orders equal frozen CLO05', async ({ page, request }) => {
  await open(page)
  const summary = (await (await request.get('/api/v1/experiments/entropy-closure/refinement')).json()).data
  await expect(page.getByTestId('refinement-table').locator('tbody tr')).toHaveCount(4)
  await expect(page.getByTestId('closure-refinement').getByRole('img')).toHaveAttribute('data-point-count', '4')
  await expect(page.getByTestId('refinement-table').locator('tbody tr td:nth-child(2)')).toHaveText(['0.2', '0.1', '0.05', '0.025'])
  for (let i = 0; i < 4; i++) {
    const value = summary.metrics_by_run[i].metrics.find((m: { value: { metric_id: string } }) => m.value.metric_id === 'R_total').value.value.value
    await expect(page.getByTestId('refinement-table').locator('tbody tr').nth(i).locator('td').nth(2)).toHaveText(String(Math.abs(value)))
  }
  await expect(page.getByTestId('refinement-slope')).toContainText(String(summary.refinement_slope.value.value.value))
  for (const run of summary.metrics_by_run) for (const slot of run.metrics) if (slot.value.metric_id.startsWith('pairwise_slope')) await expect(page.getByTestId('refinement-table')).toContainText(`${slot.value.metric_id}=${slot.value.value.value}`)
})
test('scientific limitation remains visible on every tab, with no prohibited claim or spatial view', async ({ page }) => {
  const spatial: string[] = []; page.on('request', r => { if (/snapshots|fields|trajectory|arrays/.test(r.url())) spatial.push(r.url()) })
  await open(page)
  await expect(page.getByTestId('spatial-trajectory')).toHaveText('Spatial trajectory: MISSING / not recorded')
  await expect(page.getByRole('tab')).toHaveText(['Overview', 'Semi-discrete', 'Fully-discrete', 'Evidence'])
  for (const tab of ['overview', 'semi-discrete', 'fully-discrete', 'evidence']) {
    await page.getByTestId(`tab-${tab}`).click()
    await expect(page.getByTestId('fully-discrete-limitation')).toHaveText('Fully-discrete residual is a numerical diagnostic, not an exact fully-discrete entropy identity.')
  }
  expect(await page.locator('main').innerText()).not.toMatch(/exact entropy conservation|exact entropy stability theorem|SSP-RK3 guarantees exact closure/)
  expect(spatial).toEqual([])
  await page.goto(`${base}?run=${legal[0]}&tab=flow`)
  await expect(page.getByTestId('unsupported-tab')).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Flow', exact: true })).toHaveCount(0)
})
for (const [tab, group] of [['overview', 'run'], ['semi-discrete', 'stage'], ['fully-discrete', 'step'], ['evidence', 'run']] as const) {
  test(`Evidence ${group} returns current run/tab/page from ${tab}`, async ({ page }) => {
    await open(page, legal[2], tab, tab.includes('discrete') ? 1000 : 0)
    const url = page.url()
    const link = page.locator(`a[data-testid="evidence-link"][href*="ev.entropy-closure.${legal[2]}.${group}"]`).first()
    await expect(link).toBeVisible(); await link.click()
    await page.getByTestId('quick-full-record').click()
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await expect(page.getByTestId('evidence-config')).toHaveText(legal[2])
    await expect(page.getByTestId('evidence-experiment')).toHaveText('entropy-closure')
    await page.getByTestId('back-to-result').click(); await expect(page).toHaveURL(url)
    await expect(page.getByTestId(`tab-${tab}`)).toHaveAttribute('aria-selected', 'true')
  })
}
test('Evidence tab exposes all runs, both history groups, and refinement; refinement returns same run', async ({ page }) => {
  await open(page, legal[4], 'evidence')
  for (const run of legal) await expect(page.locator(`a[data-testid="evidence-link"][href*="ev.entropy-closure.${run}.run"]`).first()).toBeVisible()
  for (const group of ['stage', 'step']) await expect(page.locator(`a[data-testid="evidence-link"][href*="ev.entropy-closure.${legal[4]}.${group}"]`)).toBeVisible()
  const url = page.url()
  await page.locator('a[data-testid="evidence-link"][href*="ev.entropy-closure.D_u.temporal-refinement"]').click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await page.getByTestId('back-to-result').click(); await expect(page).toHaveURL(url)
})
test('changing run while history is in flight cannot show stale scientific data', async ({ page }) => {
  let started!: () => void
  const pending = new Promise<void>(resolve => { started = resolve })
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/runs/D_u-cfl-0.2/stage-history?*', async route => { started(); await gate; await route.continue().catch(() => {}) })
  await open(page, legal[0], 'semi-discrete')
  await pending
  await page.getByTestId('closure-run').selectOption(legal[4])
  await expect(page.getByTestId('bu-zero-channel')).toBeVisible()
  await expect(page.getByTestId('closure-history')).toBeVisible()
  release()
  await expect(page.getByTestId('closure-run')).toHaveValue(legal[4])
  await page.getByRole('checkbox', { name: 'D_at', exact: true }).check()
  await expect(page.locator('[data-series="D_at"] td').first()).toHaveText('0')
})
test('scientific missing response remains missing, without a substitute chart', async ({ page }) => {
  await page.route('**/stage-history?*', route => route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ availability: 'MISSING', error: { message: 'Registered saved scientific source is absent' } }) }))
  await open(page, legal[0], 'semi-discrete')
  await expect(page.locator('[data-state="missing"]')).toContainText('Registered saved scientific source is absent')
  await expect(page.getByTestId('closure-history')).toHaveCount(0)
})
test('non-production science is rejected even if API transport reports success', async ({ page }) => {
  await page.route('**/entropy-closure/runs', async route => {
    const response = await route.fetch()
    const payload = await response.json()
    payload.data.runs[0].terminal_summary[0].value.result.data_origin = 'MOCK'
    await route.fulfill({ response, json: payload })
  })
  await page.goto(base)
  await expect(page.getByRole('alert')).toContainText('API returned non-production science')
  await expect(page.getByTestId('closure-run')).toHaveCount(0)
  await expect(page.getByTestId('closure-refinement')).toHaveCount(0)
})
for (const [operation, path, tab, target] of [
  ['registry', '**/entropy-closure/runs', 'overview', 'CLO01 legal run registry'],
  ['stage', '**/stage-history?*', 'semi-discrete', 'recorded closure history'],
  ['step', '**/step-history?*', 'fully-discrete', 'recorded closure history'],
  ['refinement', '**/entropy-closure/refinement', 'overview', 'CLO05 frozen refinement'],
] as const) {
  test(`API ${operation} failure displays error and no mock fallback`, async ({ page }) => {
    await page.route(path, route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ availability: 'ERROR', error: { message: 'Scientific API deliberately unavailable' } }) }))
    await page.goto(`${base}?run=${legal[0]}&tab=${tab}`)
    await expect(page.getByRole('alert')).toContainText(`Error loading ${target}`)
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
    await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
    if (operation === 'stage' || operation === 'step') await expect(page.getByTestId('closure-history')).toHaveCount(0)
    if (operation === 'refinement') await expect(page.getByTestId('closure-refinement')).toHaveCount(0)
    if (operation === 'registry') await expect(page.getByTestId('closure-run')).toHaveCount(0)
  })
}
test('production artifacts contain no mock provider or synthetic scientific payload', async () => {
  const assets = fileURLToPath(new URL('../dist/assets/', import.meta.url))
  const files = readdirSync(assets).filter(f => f.endsWith('.js'))
  expect(files.length).toBeGreaterThan(0)
  const markers = ['createMockProvider', 'mock.case8.', 'mock.spectrum.', 'mock.modal-validation.', 'Mock data — not scientific results', 'Math.sin(i / 16)', 'MockProvider']
  const matches = files.flatMap(file => markers.filter(marker => readFileSync(`${assets}${file}`, 'utf8').includes(marker)).map(marker => ({ file, marker })))
  expect(matches).toEqual([])
  const report = { status: 'PASS', files, markers, matches, mock_in_production: false }
  mkdirSync(output, { recursive: true })
  writeFileSync(`${output}WINDOW3_PRODUCTION_SCAN.json`, JSON.stringify(report, null, 2))
})
