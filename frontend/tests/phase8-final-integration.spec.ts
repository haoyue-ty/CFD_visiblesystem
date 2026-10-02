import { test, expect } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const output = fileURLToPath(new URL('../../.cache/phase8-final/', import.meta.url))
test('Phase8D real Cylinder D_u journey, D_u versus D_u and actual cumulative2D absence', async ({ page }) => {
  const requests: { url: string; status: number }[] = []
  const errors: string[] = []
  page.on('response', response => {
    if (response.url().includes('/api/v1/')) requests.push({ url: response.url(), status: response.status() })
  })
  page.on('pageerror', error => errors.push(error.message))
  mkdirSync(output, { recursive: true })
  const shots: string[] = []
  async function shot(name: string) {
    const path = `${output}${name}.png`
    await page.screenshot({ path, fullPage: true })
    shots.push(path)
  }
  await page.goto('/lab/experiments/cylinder?config=D_u&tab=flow&snapshot=5')
  await expect(page.getByTestId('snapshot-meta')).toContainText('completed step=9757')
  await expect(page.getByTestId('instantaneous-field')).toHaveAttribute('height', '31')
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
  await shot('01-cylinder-du-flow')
  await page.getByTestId('tab-entropy').click()
  await expect(page.locator('[data-point-count="9757"]')).toHaveCount(4)
  await shot('02-cylinder-du-entropy')
  await page.getByTestId('tab-sectors').click()
  await expect(page.getByTestId('sector-table').locator('tbody tr')).toHaveCount(16)
  await expect(page.getByTestId('front-band')).toContainText('REGION_SCALAR')
  await expect(page.getByTestId('cumulative-2d-missing')).toContainText('Unavailable / Missing')
  await expect(page.getByTestId('cumulative-2d-missing').locator('canvas,svg,img')).toHaveCount(0)
  await shot('03-cylinder-du-sector-allocation-missing')
  await page.getByTestId('tab-metrics').click()
  await expect(page.locator('[data-metric="cylinder_front_HF_RMS"]')).toContainText('Detector:')
  await shot('04-cylinder-du-metrics')
  await page.getByTestId('tab-evidence').click()
  const metricEvidence = page.locator('a[data-testid="evidence-link"][href*="ev.cylinder.D_u.metrics"]')
  await expect(metricEvidence).toBeVisible()
  await metricEvidence.click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await expect(page.getByTestId('evidence-config')).toHaveText('D_u')
  await shot('05-cylinder-du-evidence')
  await page.getByTestId('back-to-result').click()
  await page.getByRole('link', { name: /Cross-flow Compare/ }).click()
  await expect(page.getByTestId('case8-config')).toHaveValue('D_u')
  await expect(page.getByTestId('cylinder-config')).toHaveValue('D_u')
  await expect(page.getByTestId('case8-side').getByTestId('face-allocation-canvas')).toHaveCount(2)
  await expect(page.getByTestId('cylinder-side').getByTestId('angular-sector-chart')).toBeVisible()
  await expect(page.getByTestId('descriptive-only')).toContainText('DESCRIPTIVE_ONLY')
  await expect(page.getByTestId('no-unified-ranking')).toContainText('NO_UNIFIED_RANKING')
  await expect(page.getByTestId('cross-flow-limitations')).toContainText('Limitations')
  await shot('06-cross-flow-du-versus-du')

  const overviewResponse = await page.request.get('/api/v1/experiments/cylinder/configs/D_u/allocation')
  expect(overviewResponse.status()).toBe(200)
  const overview = await overviewResponse.json()
  expect(overview.availability).toBe('PARTIAL')
  expect(overview.data.cumulative_2d.availability).toBe('MISSING')
  expect(overview.data.cumulative_2d).not.toHaveProperty('value')
  expect(overview.data.cumulative_2d.error.evidence_refs.length).toBeGreaterThan(0)
  const missingRequests = []
  for (const path of [
    '/api/v1/experiments/cylinder/configs/D_u/allocation/cumulative-2d',
    '/api/v1/results/cylinder.D_u.cumulative2d/arrays/pi_at',
  ]) {
    const response = await page.request.get(path)
    const body = await response.json()
    expect(response.status()).toBe(404)
    expect(body).not.toHaveProperty('data')
    expect(body).not.toHaveProperty('values')
    missingRequests.push({ path, status: response.status(), body })
  }
  const missingEvidence = []
  for (const id of overview.data.cumulative_2d.error.evidence_refs) {
    const response = await page.request.get(`/api/v1/evidence/${id}`)
    expect(response.status()).toBe(200)
    missingEvidence.push(await response.json())
  }
  const comparisonResponse = await page.request.get('/api/v1/comparisons/case8-cylinder?case8_config=D_u&cylinder_config=D_u')
  expect(comparisonResponse.status()).toBe(200)
  const comparison = await comparisonResponse.json()
  expect(comparison.data.ranking_policy).toBe('NO_UNIFIED_RANKING')
  expect(comparison.data.comparability).toHaveLength(4)
  expect(comparison.data.comparability.every((r: { status: string }) => r.status === 'DESCRIPTIVE_ONLY')).toBe(true)
  expect(errors).toEqual([])
  expect(requests.filter(r => r.url.includes('/comparisons/case8-cylinder')).length).toBeGreaterThan(0)
  expect(requests.filter(r => r.url.includes('/cylinder/configs/D_u/entropy-history')).length).toBeGreaterThanOrEqual(2)
  writeFileSync(`${output}real-browser-evidence.json`, JSON.stringify({
    status: 'PASS', mockedRoutes: 0, requests, errors, screenshots: shots,
    allocationOverview: overview, missingRequests, missingEvidence, comparison,
  }, null, 2))
})
