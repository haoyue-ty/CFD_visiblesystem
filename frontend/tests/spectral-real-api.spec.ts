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
  await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
  await expect(page.getByTestId('spectral-scope')).toContainText('Selective modal response')

  // Region 1: the four registered configurations, one exact q_at resolved.
  await page.getByTestId('spectral-q-0.396').click()
  await expect(page.getByTestId('spectral-qat')).toContainText('0.396')
  await expect(page.getByTestId('spectral-curve-canvas')).toBeVisible()
  await expect(page.getByTestId('curve-provenance')).toContainText('registry_revision=')

  // Region 2: the mode-record metadata resolves from the frozen registry, but the
  // vector payload cannot be fetched: ARRAY01 is wired to the case8 service only, so a
  // spectral eigenmode result_id is not routable. The page must still name the record
  // facts honestly and mark the values slot MISSING — never a blank region, never a
  // fabricated canvas. (Window 2 ARRAY01 routing gap; see handoff report.)
  await expect(page.getByTestId('mode-index')).toHaveText('1')
  await expect(page.getByTestId('mode-rank')).toHaveText('0')
  await expect(page.getByTestId('mode-shape')).toContainText('128')
  await expect(page.getByTestId('eigenmode-canvas')).toHaveCount(0)
  const modeValuesMissing = page.getByTestId('spectral-mode-region').locator('[data-state="missing"]').first()
  await expect(modeValuesMissing).toBeVisible()
  await expect(modeValuesMissing).not.toBeEmpty()

  // Region 3: recorded validation rates; the linear history stays explicitly absent.
  await expect(page.getByTestId('growth-cfd')).not.toHaveText('unavailable')
  await expect(page.getByTestId('growth-linear-missing')).toContainText('not saved')
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
})
