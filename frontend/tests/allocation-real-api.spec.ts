import { test, expect } from '@playwright/test'

/**
 * Phase 6B Window 4 — allocation through the REAL API provider.
 *
 * The allocation routes (ALLOC01/ALLOC03) are registered but their concrete
 * loader is not enabled, so the backend answers 503 FEATURE_NOT_ENABLED. The UI
 * must surface that as an explicit UNSUPPORTED region — never a blank map, never
 * a zero-filled field, and never a silent fallback to the mock provider.
 */
test('allocation tab reports the real capability state without a fake field', async ({ page }) => {
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
