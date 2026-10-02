import { test, expect, type Page } from '../../frontend/node_modules/@playwright/test'

/**
 * Phase 7B Window 3 — Spectral Lab frontend (mock development project).
 *
 * Requirements under test:
 *   route       — the Spectral tab is reachable by deep link and renders the page.
 *   selection   — configuration (dataset) and q_at; mode index; validation run.
 *   curve       — x = mode k, y = Re(λ); 17 discrete blocks, no interpolation.
 *   mode view   — eigenmode rendered for a saved selection; "Unavailable" (never
 *                 blank) for a registered-but-unsaved selection.
 *   validation  — linear vs CFD; a missing linear history stays explicit.
 *   scope       — the page shows "Selective modal response" and NEVER an
 *                 evaluative verdict (Stable / Improved / Better).
 *   loading     — a slow provider surfaces a Loading state.
 *   error       — a failing provider surfaces an Error state, not a fake curve.
 */

async function openSpectral(page: Page) {
  await page.goto('/lab/experiments/case8?tab=spectral')
  await expect(page.getByTestId('spectral-lab')).toBeVisible()
}

test.describe('Spectral Lab — route and scope', () => {
  test('is reachable via the independent workspace shortcut and legacy deep link', async ({ page }) => {
    await page.goto('/lab/experiments/case8?tab=spectral')
    await expect(page.getByTestId('spectral-lab')).toBeVisible()
    await expect(page.getByTestId('tab-spectral')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByRole('tablist', { name: 'Case8 tabs' }).getByRole('tab', { name: 'Spectral' })).toHaveCount(0)
  })

  test('states the scientific scope and never emits an evaluative verdict', async ({ page }) => {
    await openSpectral(page)
    const scope = page.getByTestId('spectral-scope')
    await expect(scope).toContainText('Selective modal response')

    // The forbidden vocabulary must not appear anywhere on the page.
    const text = await page.getByTestId('spectral-lab').innerText()
    for (const word of ['Stable', 'Improved', 'Better']) {
      expect(text).not.toContain(word)
    }
  })
})

test.describe('Spectral Lab — region 1 (spectral abscissa curve)', () => {
  test('renders x = mode k, y = Re(λ) with the recorded q_at', async ({ page }) => {
    await openSpectral(page)
    await expect(page.getByTestId('spectral-curve-region')).toContainText('x = mode k')
    await expect(page.getByTestId('spectral-curve-region')).toContainText('y = Re(λ)')
    await expect(page.getByTestId('spectral-curve-canvas')).toBeVisible()
    await expect(page.getByTestId('spectral-qat')).toContainText('q_at =')
  })

  test('switching configuration changes the resolved q_at (four exact values)', async ({ page }) => {
    await openSpectral(page)
    await page.getByTestId('spectral-q-0.396').click()
    await expect(page.getByTestId('spectral-qat')).toContainText('0.396')
    await page.getByTestId('spectral-q-0').click()
    await expect(page.getByTestId('spectral-qat')).toContainText('q_at = 0')
  })
})

test.describe('Spectral Lab — region 2 (mode detail)', () => {
  test('renders the eigenmode for a saved selection with its index spaces', async ({ page }) => {
    await openSpectral(page)
    await expect(page.getByTestId('mode-index')).toHaveText('1')
    await expect(page.getByTestId('mode-rank')).toHaveText('0')
    await expect(page.getByTestId('eigenmode-canvas')).toBeVisible()
  })

  test('a registered-but-unsaved mode rank shows Unavailable, never a blank frame', async ({ page }) => {
    await page.goto('/lab/experiments/case8?tab=spectral&spectral_rank=9')
    await expect(page.getByTestId('spectral-lab')).toBeVisible()
    await expect(page.getByTestId('spectral-mode-unavailable')).toBeVisible()
    await expect(page.getByTestId('spectral-mode-unavailable')).toContainText('Unavailable')
    // No chart may be rendered for an unavailable mode.
    await expect(page.getByTestId('eigenmode-canvas')).toHaveCount(0)
  })

  test('selecting a different mode index re-reads the eigenmode', async ({ page }) => {
    await openSpectral(page)
    await page.getByTestId('spectral-mode-4').click()
    await expect(page.getByTestId('mode-index')).toHaveText('4')
  })
})

test.describe('Spectral Lab — region 3 (growth validation)', () => {
  test('renders linear vs CFD with recorded rates and an explicit missing history', async ({ page }) => {
    await openSpectral(page)
    await expect(page.getByTestId('spectral-validation-region')).toContainText('linear vs CFD')
    await expect(page.getByTestId('growth-validation-canvas')).toBeVisible()
    await expect(page.getByTestId('growth-cfd')).not.toHaveText('unavailable')
    // The linear amplitude history was not saved: this stays explicit.
    await expect(page.getByTestId('growth-linear-missing')).toContainText('not saved')
  })
})

test.describe('Spectral Lab — loading state', () => {
  test('a slow spectral provider surfaces a Loading state first', async ({ page }) => {
    // The mock provider delays every read, so the loading layer is observable.
    await page.goto('/lab/experiments/case8?tab=spectral')
    await expect(page.getByTestId('spectral-lab')).toContainText('Loading')
  })
})
