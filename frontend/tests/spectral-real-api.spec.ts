import { test, expect } from '@playwright/test'

/**
 * Phase 7B Window 3 — Spectral Lab against the REAL API provider.
 *
 * These assertions run in the `real-api` project (the production bundle at the
 * preview URL), where the page reads the frozen backend through /api/v1. They cover
 * the two states the mock project cannot exercise honestly:
 *   - a failing spectral API surfaces a real Error/Missing state, never a fabricated
 *     curve, and never a mock fallback (no MOCK badge on the real provider);
 *   - the happy path reads recorded frozen facts (q_at, curve canvas, no MOCK).
 */

test('real spectral outage is surfaced honestly with no fabricated curve', async ({ page }) => {
  await page.route('**/api/v1/spectra**', route => route.fulfill({
    status: 500, contentType: 'application/json',
    body: JSON.stringify({
      availability: 'ERROR',
      error: { code: 'SOURCE_ERROR', message: 'Recorded spectral source could not be read' },
    }),
  }))
  await page.goto('/lab/experiments/case8?tab=spectral')
  await expect(page.getByTestId('spectral-lab')).toBeVisible()

  // A real, explained state must appear.
  await expect(page.locator('[data-state="missing"], [data-state="unsupported"], .ls--error').first()).toBeVisible()
  // No chart may be rendered from a failed read.
  await expect(page.getByTestId('spectral-curve-canvas')).toHaveCount(0)
  await expect(page.getByTestId('eigenmode-canvas')).toHaveCount(0)
  // Critically: no cross-provider fallback to synthetic science.
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
})

test('real Spectral Lab reads recorded frozen facts', async ({ page }) => {
  test.setTimeout(60_000)
  await page.goto('/lab/experiments/case8?tab=spectral')
  await expect(page.getByTestId('provider-kind')).toHaveText("真实数据 API")
  await expect(page.getByTestId('spectral-scope')).toContainText("选择性模态响应")

  // Region 1: the four registered configurations, one exact q_at resolved.
  await page.getByTestId('spectral-q-0.396').click()
  await expect(page.getByTestId('spectral-qat')).toContainText('0.396')
  await expect(page.getByTestId('spectral-curve-canvas')).toBeVisible()
  await expect(page.getByTestId('curve-provenance')).toContainText("登记版本=")

  // Region 2: saved metadata and complex array both resolve through the real API.
  await expect(page.getByTestId('mode-index')).toHaveText('1')
  await expect(page.getByTestId('mode-rank')).toHaveText('0')
  await expect(page.getByTestId('mode-shape')).toContainText('128')
  await expect(page.getByTestId('eigenmode-canvas')).toBeVisible()

  // Region 3: recorded validation rates; the linear history stays explicitly absent.
  await expect(page.getByTestId('growth-cfd')).not.toHaveText("当前不可用")
  await expect(page.getByTestId('growth-linear-missing')).toContainText("未保存")
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
})


test('all four real configurations expose every recorded mode and restore evidence context', async ({ page }, testInfo) => {
  test.setTimeout(180_000)
  await page.goto('/lab/experiments/case8?tab=spectral')
  await expect(page.getByTestId('spectral-scientific-limit')).toHaveText("正熵产 ≠ 所有模态统一增强阻尼。")
  for (const q of [0, 0.132, 0.264, 0.396]) {
    await page.getByTestId(`spectral-q-${q}`).click()
    await expect(page.getByTestId('spectral-qat').locator('strong')).toHaveText(String(q))
    await expect(page.getByTestId('spectral-curve-canvas')).toBeVisible()
    for (let mode = 0; mode <= 16; mode++) {
      await page.getByTestId(`spectral-mode-${mode}`).click()
      await expect(page.getByTestId('mode-index')).toHaveText(String(mode))
      await expect(page.getByTestId('eigenmode-canvas')).toBeVisible()
      await expect(page.getByTestId('mode-provenance')).toContainText('spectral-registry-v1')
    }
    const text = (await page.locator('body').innerText()).toLowerCase()
    for (const phrase of ['all stable', 'always improved', 'universal']) expect(text).not.toContain(phrase)
  }
  await page.screenshot({ path: testInfo.outputPath('spectral-real.png'), fullPage: true })
  await expect(page).toHaveURL(/spectral_mode=16/)
  const refs = await page.getByTestId('spectral-evidence-link').locator('.sl__ev-id').allTextContents()
  expect(refs).toHaveLength(4)
  for (const ref of refs) {
    await page.getByText(ref, { exact: true }).locator('..').getByTestId('evidence-link').click()
    await page.getByTestId('quick-full-record').click()
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await expect(page.getByTestId('evidence-drift')).toHaveText("记录时源码与当前源码一致")
    await expect(page.getByTestId('evidence-verification')).toContainText("已冻结验收")
    await expect(page.getByTestId('current-source-hash')).toHaveText(/[a-f0-9]{64}/)
    await expect(page.getByTestId('evidence-record')).toContainText("正熵产 ≠ 所有模态统一增强阻尼")
    await expect(page.getByTestId('evidence-assets').locator('tbody tr')).not.toHaveCount(0)
    await page.getByTestId('back-to-result').click()
    await expect(page.getByTestId('spectral-qat').locator('strong')).toHaveText('0.396')
    await expect(page.getByTestId('mode-index')).toHaveText('16')
    await expect(page.getByTestId('eigenmode-canvas')).toBeVisible()
  }
})

test('real provider reports a missing saved vector explicitly', async ({ page }) => {
  await page.route('**/api/v1/spectra/*/eigenmodes/*', route => route.fulfill({
    status: 404, contentType: 'application/json',
    body: JSON.stringify({ availability: 'MISSING', error: { code: 'MISSING_EIGENMODE', message: 'Registered saved eigenmode asset is absent' } }),
  }))
  await page.goto('/lab/experiments/case8?tab=spectral')
  await expect(page.getByTestId('spectral-mode-unavailable')).toContainText("当前不可用")
  await expect(page.getByTestId('eigenmode-canvas')).toHaveCount(0)
  await expect(page.getByTestId('spectral-curve-canvas')).toBeVisible()
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
})


for (const fault of ['result identity', 'element count']) {
  test(`real eigenmode rejects an array ${fault} mismatch`, async ({ page }) => {
    await page.route('**/api/v1/results/spectrum.*/arrays/eigenvector', async route => {
      const response = await route.fetch()
      const body = await response.json()
      if (fault === 'result identity') body.data.result.result_id = 'spectrum.q-0.396.mode-16'
      else body.data.values.pop()
      await route.fulfill({ response, json: body })
    })
    await page.goto('/lab/experiments/case8?tab=spectral')
    await expect(page.getByTestId('spectral-mode-region').locator('.ls--error')).toBeVisible()
    await expect(page.getByTestId('spectral-mode-region')).toContainText('数组标识或描述符不一致')
    await expect(page.getByTestId('eigenmode-canvas')).toHaveCount(0)
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
  })
}
