import { test, expect } from '../../frontend/node_modules/@playwright/test'

/**
 * Phase 6B Window 4 — Allocation UI (mock development project).
 *
 * The central requirement under test: the FACE_FIELD and CELL_FIELD views must
 * NOT be presented as the same scientific object. Concretely that means:
 *   - different representation_type values
 *   - different mask identities and mask types
 *   - different measure definitions and integral rules
 *   - two different canvases (native face raster vs cell-centre raster)
 *   - the face view shows TWO orientations, the cell view shows ONE field
 *
 * Plus the mandated provenance blocks: representation_type, mask, definition,
 * verification, evidence.
 */

async function openAllocation(page: import('../../frontend/node_modules/@playwright/test').Page) {
  await page.goto('/lab/experiments/case8?config=D_u&tab=allocation')
  await expect(page.getByTestId('case8-allocation')).toBeVisible()
}

test.describe('Allocation tab — Case8 D_u FACE_FIELD', () => {
  test('shows representation_type FACE_FIELD with face measure and two orientations', async ({ page }) => {
    await openAllocation(page)
    await expect(page.getByTestId('alloc-family-face')).toHaveAttribute('aria-pressed', 'true')

    await expect(page.getByTestId('alloc-representation-type')).toHaveText('FACE_FIELD')
    await expect(page.getByTestId('alloc-measure-definition')).toHaveText('face integrated')
    await expect(page.getByTestId('alloc-semantic-id')).toHaveText('Case8_face_Pi_at_integrated')

    // Native face integration: spatial measure is NOT yet applied.
    await expect(page.getByTestId('alloc-spatial-included')).toContainText('no')
    await expect(page.getByTestId('alloc-integral-rule')).toHaveText('dy*sum(xfaces)+dx*sum(yfaces)')

    // Two separate orientation figures, never one averaged cell field.
    await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
    await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(0)
    await expect(page.getByTestId('alloc-face-note')).toContainText('never summed')
  })

  test('shows the per-orientation mask identity and both mask counts', async ({ page }) => {
    await openAllocation(page)
    await expect(page.getByTestId('alloc-mask-id')).toHaveText('mask.case8.native-face-shock-window')
    await expect(page.getByTestId('alloc-mask-type')).toHaveText('CASE8_NATIVE_FACE_SHOCK_WINDOW')
    await expect(page.getByTestId('alloc-mask-counts')).toHaveText('640, 648')
  })

  test('shows definition, verification and evidence blocks', async ({ page }) => {
    await openAllocation(page)
    await expect(page.getByTestId('alloc-definition')).toContainText('separate x/y normal faces')
    await expect(page.getByTestId('alloc-verification')).toContainText('NOT_APPLICABLE')
    await expect(page.getByTestId('alloc-evidence').getByTestId('evidence-link').first()).toBeVisible()
  })

  test('summary shows budget and inside fraction', async ({ page }) => {
    await openAllocation(page)
    await expect(page.getByTestId('allocation-summary')).toHaveAttribute('data-measure', 'face integrated')
    await expect(page.getByTestId('alloc-budget')).toHaveText('0.0027771079325925934')
    await expect(page.getByTestId('alloc-inside')).toHaveText('0.9980884346017243')
  })
})

test.describe('Allocation tab — Gate CELL_FIELD', () => {
  test('switching family shows CELL_FIELD with cell measure and one field', async ({ page }) => {
    await openAllocation(page)
    await page.getByTestId('alloc-family-cell').click()

    await expect(page.getByTestId('alloc-representation-type')).toHaveText('CELL_FIELD')
    await expect(page.getByTestId('alloc-measure-definition')).toHaveText('cell integrated')
    await expect(page.getByTestId('alloc-semantic-id')).toHaveText('Gate_cell_Pi_at_integrated')

    // Cell integration already includes the spatial measure.
    await expect(page.getByTestId('alloc-spatial-included')).toContainText('yes')
    await expect(page.getByTestId('alloc-integral-rule')).toHaveText('sum(cells); no additional dx/dy/dt')

    // One cell figure, no face figures.
    await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(1)
    await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(0)
  })

  test('all three Gate configs render a cell map with matched-budget summaries', async ({ page }) => {
    await openAllocation(page)
    await page.getByTestId('alloc-family-cell').click()

    const expected: Record<string, { budget: string; inside: string }> = {
      Acoustic: { budget: '0.0028004425253788713', inside: '0.9983067757919961' },
      Pressure: { budget: '0.0028430539591530325', inside: '0.9916868280217838' },
      Ungated: { budget: '0.0028272752981764065', inside: '0.8923001329707689' },
    }
    for (const [cfg, values] of Object.entries(expected)) {
      await page.getByTestId(`alloc-gate-${cfg}`).click()
      await expect(page.getByTestId('alloc-identity')).toHaveText(`gate / ${cfg}`)
      await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(1)
      await expect(page.getByTestId('alloc-budget')).toHaveText(values.budget)
      await expect(page.getByTestId('alloc-inside')).toHaveText(values.inside)
    }
  })

  test('cell mask identity is distinct from the Case8 face mask', async ({ page }) => {
    await openAllocation(page)
    // Case8 face mask first.
    await expect(page.getByTestId('alloc-mask-type')).toHaveText('CASE8_NATIVE_FACE_SHOCK_WINDOW')
    await expect(page.getByTestId('alloc-mask-id')).toHaveText('mask.case8.native-face-shock-window')

    // Gate cell mask: different type, different id, single count.
    await page.getByTestId('alloc-family-cell').click()
    await expect(page.getByTestId('alloc-mask-type')).toHaveText('GATE_CELL_SHOCK_WINDOW')
    await expect(page.getByTestId('alloc-mask-id')).toHaveText('mask.gate.cell-shock-window')
    await expect(page.getByTestId('alloc-mask-counts')).toHaveText('672')
  })
})

test.describe('The two representations are never the same object', () => {
  test('FACE and CELL differ in representation, measure, mask and raster', async ({ page }) => {
    await openAllocation(page)

    const face = {
      representation: await page.getByTestId('alloc-representation-type').textContent(),
      measure: await page.getByTestId('alloc-measure-definition').textContent(),
      maskType: await page.getByTestId('alloc-mask-type').textContent(),
      rule: await page.getByTestId('alloc-integral-rule').textContent(),
      faces: await page.getByTestId('face-allocation-canvas').count(),
      cells: await page.getByTestId('cell-allocation-canvas').count(),
    }

    await page.getByTestId('alloc-family-cell').click()
    await expect(page.getByTestId('alloc-representation-type')).toHaveText('CELL_FIELD')

    const cell = {
      representation: await page.getByTestId('alloc-representation-type').textContent(),
      measure: await page.getByTestId('alloc-measure-definition').textContent(),
      maskType: await page.getByTestId('alloc-mask-type').textContent(),
      rule: await page.getByTestId('alloc-integral-rule').textContent(),
      faces: await page.getByTestId('face-allocation-canvas').count(),
      cells: await page.getByTestId('cell-allocation-canvas').count(),
    }

    expect(face.representation).not.toBe(cell.representation)
    expect(face.measure).not.toBe(cell.measure)
    expect(face.maskType).not.toBe(cell.maskType)
    expect(face.rule).not.toBe(cell.rule)
    // Face view renders two figures; cell view renders one. Never the same raster.
    expect(face.faces).toBe(2)
    expect(face.cells).toBe(0)
    expect(cell.faces).toBe(0)
    expect(cell.cells).toBe(1)
  })
})

test.describe('Allocation capability gating', () => {
  test('allocation tab stays disabled for A/B/C and enabled for D_u', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=A_u&tab=overview')
    await expect(page.getByTestId('tab-allocation')).toBeDisabled()
    await page.getByTestId('config-D_u').click()
    await expect(page.getByTestId('tab-allocation')).toBeEnabled()
  })

  test('mock badge is visible on the allocation tab', async ({ page }) => {
    await openAllocation(page)
    await expect(page.getByTestId('case8-allocation').getByTestId('mock-badge').first()).toContainText('MOCK')
  })
})
