import { test, expect, type Page, type Locator, type APIRequestContext } from '@playwright/test'
import type { components } from '../src/types/generated/api'
type EvidenceRecord = components['schemas']['EvidenceRecord']
const blockedClaims = /\b(?:universally stable|always improved|uniformly damped|larger entropy means better|more localized is universally better)\b/i
async function read<T>(request: APIRequestContext, path: string): Promise<T> {
  const response = await request.get(path)
  expect(response.status()).toBe(200)
  expect(response.headers()['content-disposition']).toBeUndefined()
  const envelope = await response.json()
  expect(envelope.data).toBeDefined()
  return envelope.data
}
async function full(page: Page, link: Locator) {
  await link.click()
  await expect(page.getByTestId('evidence-quick-view')).toBeVisible()
  await expect(page.getByTestId('quick-identity')).toBeVisible()
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await expect(page.getByTestId('evidence-method')).toContainText('Recorded source hash')
  await expect(page.getByTestId('evidence-method')).toContainText('Current source hash')
  await expect(page.getByTestId('evidence-source-asset').first()).toBeVisible()
  await expect(page.locator('a[href^="file:"], a[href^="D:"], a[download]')).toHaveCount(0)
}
test('W3 Case8 D_u Allocation traces source/hash/processing and restores result', async ({ page }, info) => {
  await page.goto('/lab/experiments/case8?config=D_u&tab=allocation')
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
  await full(page, page.getByTestId('alloc-evidence').getByTestId('evidence-link').first())
  await expect(page.getByTestId('evidence-config')).toHaveText('D_u')
  await expect(page.getByTestId('evidence-processing')).toContainText('FORMAT_MAPPING')
  await expect(page.getByTestId('evidence-verification')).toContainText('FROZEN_ACCEPTED')
  await expect(page.getByTestId('evidence-limitations')).toContainText('diagnostic rerun')
  await page.screenshot({ path: info.outputPath('case8-detail.png'), fullPage: true })
  await page.getByTestId('back-to-result').click()
  await expect(page.getByTestId('tab-allocation')).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
})
test('W3 Gate Acoustic traces matched configuration, native map, mask and summary', async ({ page }) => {
  await page.goto('/lab/experiments/gate')
  const gate = page.getByTestId('gate-Acoustic')
  await expect(gate.getByTestId('cell-allocation-canvas')).toBeVisible()
  await expect(gate.getByTestId('matched-qat')).not.toHaveText('UNKNOWN')
  await expect(gate.getByTestId('gate-window')).toContainText('672')
  await full(page, gate.getByTestId('evidence-link').first())
  await expect(page.getByTestId('evidence-config')).toHaveText('Acoustic')
  await expect(page.getByTestId('evidence-params')).toContainText('q_at')
  await expect(page.getByTestId('evidence-definitions')).toContainText('mask.gate.cell-window')
  await expect(page.getByTestId('evidence-record')).toContainText('gate.Acoustic.allocation')
  await page.getByTestId('back-to-result').click()
  await expect(gate.getByTestId('cell-allocation-canvas')).toBeVisible()
})
test('W3 q_at=.396 mode8 traces eigenmode and Spectrum provenance without changing selectors', async ({ page, request }) => {
  const eigen = 'spectrum.q-0.396.mode-08.right.rank-00.complex_vector.stored_vector'
  const provenance = await read<components['schemas']['ResultProvenance']>(request, `/api/v1/results/${eigen}/provenance`)
  await page.goto('/lab/experiments/spectrum?spectral_q=spectrum.q-0.396&spectral_mode=8')
  await expect(page.getByTestId('mode-index')).toHaveText('8')
  await expect(page.getByTestId('spectral-qat').locator('strong')).toHaveText('0.396')
  await expect(page.getByTestId('eigenmode-canvas')).toBeVisible()
  const original = page.url()
  for (const id of [provenance.evidence_records[0]!.evidence_id, 'evidence.spectral.spectrum.q-0.396']) {
    await full(page, page.locator(`a[data-testid="evidence-link"][href*="${id}"]`).first())
    await expect(page.getByTestId('evidence-config')).toHaveText('spectrum.q-0.396')
    await expect(page.getByTestId('evidence-source-asset').first()).toContainText('Recorded data hash')
    await page.getByTestId('back-to-result').click()
    await expect(page).toHaveURL(original)
    await expect(page.getByTestId('mode-index')).toHaveText('8')
  }
})
test('W3 Modal Validation history resolves the actual selected eigenpair via SPEC05 and EVI03', async ({ page, request }, info) => {
  const run = 'modal-validation.m08_q0p396_eps1e-04'
  const validation = await read<components['schemas']['GrowthValidationView']>(request, `/api/v1/spectra/validation/${run}`)
  expect(validation.step_indices).toEqual(Array.from({ length: 33 }, (_, i) => i))
  expect(validation.mode_index).toBe(8)
  expect(validation.q_at).toBe(0.396)
  expect(validation.eigenmode_id).toMatch(/^spectrum\.q-0\.396\.mode-08\.right\.rank-/)
  const selected = await read<components['schemas']['ResultProvenance']>(request, `/api/v1/results/${validation.eigenmode_id}/provenance`)
  await page.goto(`/lab/experiments/modal-validation?spectral_q=spectrum.q-0.396&spectral_mode=8&spectral_run=${run}`)
  await expect(page.getByTestId('growth-validation-canvas')).toBeVisible()
  await expect(page.getByTestId('validation-provenance')).toContainText('spectral-registry-v1')
  await expect(page.getByTestId('growth-linear-missing')).toContainText('not saved')
  await full(page, page.locator(`a[data-testid="evidence-link"][href*="evidence.spectral.${run}.history"]`))
  await expect(page.getByTestId('evidence-source-asset').filter({ hasText: 'mode_selection.json' })).toHaveCount(1)
  await expect(page.getByTestId('evidence-params')).toContainText('mode')
  await page.getByTestId('back-to-result').click()
  // Existing UI keeps the selected-eigenpair identity in SPEC05, not a P09 relation link.
  // Follow that actual registered identity independently, without inventing a relation.
  await page.goto(`/evidence/${selected.evidence_records[0]!.evidence_id}`)
  await expect(page.getByTestId('evidence-record')).toContainText(validation.eigenmode_id)
  await info.attach('selected-eigenpair-relation', { body: JSON.stringify({ run, history: validation.result.result_id,
    eigenmode_id: validation.eigenmode_id, spectrum_record_id: validation.spectrum_record_id,
    evidence_ids: selected.provenance.evidence_refs, relation_transport: 'SPEC05 → EVI03; no dedicated P09 hyperlink' }), contentType: 'application/json' })
})
test('W3 Cylinder D_u sectors trace J2C-v2 sources and limitation', async ({ page }, info) => {
  await page.goto('/lab/experiments/cylinder?config=D_u&tab=sectors')
  await expect(page.getByTestId('sector-table').locator('tbody tr')).toHaveCount(16)
  await full(page, page.getByTestId('sector-allocation').locator('a[href*="ev.cylinder.D_u.sectors"]').first())
  await expect(page.getByTestId('evidence-config')).toHaveText('D_u')
  await expect(page.getByTestId('evidence-assets')).toContainText('J2C_cylinder_formal_v2')
  await expect(page.getByTestId('evidence-limitations')).toContainText('without full-trajectory 2D')
  await expect(page.getByTestId('evidence-verification')).toContainText('VERIFIED_NOT_FROZEN')
  await page.screenshot({ path: info.outputPath('cylinder-sector-detail.png'), fullPage: true })
  await page.getByTestId('back-to-result').click()
  await expect(page.getByTestId('sector-table').locator('tbody tr')).toHaveCount(16)
})
test('W3 Cross-flow D_u/D_u preserves independent evidence and descriptive policies', async ({ page }) => {
  await page.goto('/cross-flow?case8_config=D_u&cylinder_config=D_u&view=allocation')
  await expect(page.getByTestId('descriptive-only')).toContainText('DESCRIPTIVE_ONLY')
  await expect(page.getByTestId('no-unified-ranking')).toContainText('NO_UNIFIED_RANKING')
  for (const [side, id, experiment] of [
    ['case8-side', 'ev.case8.D_u.allocation', 'case8'],
    ['cylinder-side', 'ev.cylinder.D_u.sectors', 'cylinder'],
  ] as const) {
    await full(page, page.getByTestId(side).locator(`a[href*="${id}"]`).first())
    await expect(page.getByTestId('evidence-experiment')).toHaveText(experiment)
    await page.getByTestId('back-to-result').click()
    await expect(page.getByTestId('case8-config')).toHaveValue('D_u')
    await expect(page.getByTestId('cylinder-config')).toHaveValue('D_u')
  }
})
test('W3 Closure D_u CFL=.05 stage and step records retain freeze binding', async ({ page }) => {
  await page.goto('/lab/experiments/entropy-closure?run=D_u-cfl-0.05&tab=semi-discrete')
  for (const [tab, granularity, group] of [['semi-discrete', 'PER_STAGE', 'stage'], ['fully-discrete', 'PER_STEP', 'step']] as const) {
    await page.getByTestId(`tab-${tab}`).click()
    await expect(page.getByTestId('closure-history')).toHaveAttribute('data-granularity', granularity)
    await full(page, page.getByTestId('closure-history').locator(`a[href*="ev.entropy-closure.D_u-cfl-0.05.${group}"]`).first())
    await expect(page.getByTestId('evidence-config')).toHaveText('D_u-cfl-0.05')
    await expect(page.getByTestId('evidence-result-context').first()).toContainText(granularity)
    await expect(page.getByTestId('evidence-freeze')).toContainText('Manifest identity')
    await expect(page.getByTestId('evidence-freeze')).not.toContainText('Freeze was not recorded')
    await page.getByTestId('back-to-result').click()
    await expect(page.getByTestId('closure-run')).toHaveValue('D_u-cfl-0.05')
  }
})
test('W3 Mechanism SCHEMATIC theory/implementation stays nonnumerical', async ({ page }) => {
  await page.goto('/lab/mechanism')
  await full(page, page.locator('a[href*="ev.mechanism.theory-implementation"]').first())
  await expect(page.getByTestId('evidence-non-numerical')).toContainText('NON-NUMERICAL')
  await expect(page.getByTestId('evidence-limitations')).toContainText('SCHEMATIC')
  await expect(page.getByTestId('evidence-limitations')).toContainText('No numeric Near1D scan or CFD result is represented')
  await expect(page.getByTestId('evidence-result-context')).toHaveCount(0)
})
test('W3 three required GAPS have no values, fake plots or reconstruct actions', async ({ page, request }) => {
  for (const id of ['ev.missing.cylinder-cumulative2d', 'ev.inventory.missing_near1d_raw_epsilon_scan', 'ev.inventory.missing_persisted_jacobian_fourier_blocks']) {
    const record = await read<EvidenceRecord>(request, `/api/v1/evidence/${id}`)
    expect(record.result_ids).toEqual([])
    expect(record.result_contexts).toEqual([])
    expect(record.data_hash.state).not.toBe('KNOWN')
    await page.goto(`/evidence/${id}`)
    await expect(page.getByTestId('evidence-verification')).toContainText('MISSING')
    await expect(page.getByTestId('evidence-record').locator('canvas, svg, input[type="range"]')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /^(Generate|Reconstruct|Interpolate|Fill)$/i })).toHaveCount(0)
  }
})
test('W3 Home→Lab reaches each implemented module and Evidence navigation', async ({ page }) => {
  for (const [id, ready] of [['case8', 'config-D_u'], ['entropy-closure', 'closure-run'], ['cylinder', 'config-D_u']] as const) {
    await page.goto('/home')
    await page.getByRole('navigation', { name: 'System navigation' }).getByRole('link', { name: 'Lab', exact: true }).click()
    await page.getByTestId(`open-${id}`).click()
    await expect(page.getByTestId(ready)).toBeVisible()
    await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
    expect(await page.locator('body').innerText()).not.toMatch(blockedClaims)
  }
  // Gate, Spectrum and Modal Validation are delivered within the scientific
  // workspace; the frozen experiment catalog still marks their standalone cards PLANNED.
  await page.goto('/home')
  await page.getByRole('navigation', { name: 'System navigation' }).getByRole('link', { name: 'Lab', exact: true }).click()
  await page.getByTestId('open-case8').click()
  await page.getByTestId('tab-allocation').click()
  await page.getByTestId('alloc-family-cell').click()
  await page.getByTestId('alloc-gate-Acoustic').click()
  await expect(page.getByTestId('alloc-identity')).toHaveText('gate / Acoustic')
  await expect(page.getByTestId('cell-allocation-canvas').first()).toBeVisible()
  await page.getByTestId('tab-spectral').click()
  await expect(page.getByTestId('spectral-curve-canvas')).toBeVisible()
  await expect(page.getByTestId('growth-validation-canvas')).toBeVisible()
  await expect(page.getByTestId('growth-cfd')).not.toHaveText('unavailable')
  await page.goto('/lab')
  await page.getByRole('link', { name: '跨流动比较 Cross-flow', exact: true }).click()
  await expect(page.getByTestId('descriptive-only')).toBeVisible()
  await page.goto('/lab')
  await page.getByTestId('lab-open-mechanism').click()
  await expect(page.getByTestId('mechanism-architecture')).toBeVisible()
  await page.getByRole('navigation', { name: 'System navigation' }).getByRole('link', { name: 'Evidence', exact: true }).click()
  await expect(page.getByTestId('evidence-CURRENT')).toBeVisible()
})
