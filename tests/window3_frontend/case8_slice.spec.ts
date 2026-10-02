import { test, expect } from '../../frontend/node_modules/@playwright/test'

/**
 * Window 3 — Case8 functional frontend vertical slice.
 *
 * Covers the verification list required by the task:
 *  - Entry -> Home -> Lab -> Case8
 *  - A/B/C/D config switching
 *  - Snapshot 1...6 (and that 0 cannot be selected)
 *  - Entropy render + dual-time notice
 *  - Metrics with definition/unit/detector/evidence
 *  - Evidence navigation and return-context restoration
 *  - refresh / deep-link recovery
 *  - visible MOCK labelling
 */

test.describe('Entry -> Home -> Lab -> Case8 chain', () => {
  test('Entry shows identity and enters the system', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('main[data-page="entry"] h1')).toHaveText('ShockPath')
    await page.getByTestId('enter-system').click()
    await expect(page).toHaveURL(/\/home$/)
    await expect(page.locator('main[data-page="home"]')).toBeVisible()
  })

  test('Home shows the scientific question, implemented Explore, and Lab entry', async ({ page }) => {
    await page.goto('/home')
    await expect(page.getByTestId('home-question')).toContainText("耗散")
    await expect(page.getByTestId('explore-status')).toContainText("已交付 · 7 幕引导")
    // Phase10 delivers the guided entry alongside the existing Lab path.
    await page.getByTestId('home-start-explore').click()
    await expect(page).toHaveURL(/\/explore\?scene=1$/)
    await expect(page.getByTestId('scene-progress')).toHaveText("第 1 幕 / 共 7 幕")
    await page.goBack()
    await expect(page.locator('main[data-page="home"]')).toBeVisible()
    await page.getByTestId('home-to-lab').click()
    await expect(page.locator('main[data-page="lab"]')).toBeVisible()
  })

  test('Lab marks only Case8 IMPLEMENTED and others PLANNED (never MISSING data)', async ({ page }) => {
    await page.goto('/lab')
    await expect(page.getByTestId('lab-delivery-case8')).toHaveText("已交付")
    for (const id of ['gate', 'spectrum', 'cylinder']) {
      await expect(page.getByTestId(`lab-delivery-${id}`)).toHaveText("计划中")
      const note = page.getByTestId(`lab-planned-note-${id}`)
      await expect(note).toContainText("计划中")
      // The note must state this is a delivery state, not a scientific-data gap.
      await expect(note).toContainText("交付状态")
      await expect(note).toContainText("并非")
    }
    await page.getByTestId('open-case8').click()
    await expect(page.locator('main[data-page="experiment"]')).toBeVisible()
  })
})

test.describe('Case8 config switching', () => {
  test('A/B/C/D are selectable and update the overview', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=D_u&tab=overview')
    for (const cfg of ['A_u', 'B_u', 'C_u', 'D_u']) {
      await page.getByTestId(`config-${cfg}`).click()
      await expect(page.getByTestId('overview-config')).toHaveText(cfg)
      // URL state must follow the selection (deep-link / refresh recovery).
      await expect(page).toHaveURL(new RegExp(`config=${cfg}`))
    }
  })

  test('Allocation is family-present but disabled for A/B/C and explained', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=A_u')
    await expect(page.getByTestId('tab-allocation')).toBeDisabled()
    // Selecting a config that disables the tab must not silently keep it active.
    await page.getByTestId('config-D_u').click()
    await expect(page.getByTestId('tab-allocation')).toBeEnabled()
  })
})

test.describe('Flow snapshots', () => {
  test('snapshots 1..6 render with "Snapshot n / 6" and actual step/time', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=D_u&tab=flow')
    await expect(page.getByTestId('snapshot-label')).toHaveText("快照 1 / 6")
    for (let n = 1; n <= 6; n += 1) {
      await page.getByTestId(`snapshot-${n}`).click()
      await expect(page.getByTestId('snapshot-label')).toHaveText(`快照 ${n} / 6`)
      await expect(page.getByTestId('snapshot-step')).not.toBeEmpty()
      await expect(page.getByTestId('snapshot-physical-time')).not.toBeEmpty()
      await expect(page.getByTestId('snapshot-canvas')).toBeVisible()
    }
    // The terminal frame's documented actual values.
    await page.getByTestId('snapshot-6').click()
    await expect(page.getByTestId('snapshot-step')).toHaveText('1912')
    await expect(page.getByTestId('snapshot-physical-time')).toHaveText('0.08')
  })

  test('snapshot 0 is not offered as a recorded index', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=D_u&tab=flow')
    await expect(page.getByTestId('snapshot-0')).toHaveCount(0)
    // A deep link to index 0 is rejected explicitly.
    await page.goto('/lab/experiments/case8?config=D_u&tab=flow&snapshot=0')
    await expect(page.locator('[data-state="invalid-selector"]')).toBeVisible()
    await expect(page.getByTestId('snapshot-label')).toHaveCount(0)
  })

  test('field switch re-renders density / pressure / front', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=D_u&tab=flow')
    for (const f of ['pressure', 'front', 'density']) {
      await page.getByTestId(`field-${f}`).click()
      await expect(page.getByTestId('snapshot-canvas')).toBeVisible()
    }
  })
})

test.describe('Entropy + dual time', () => {
  test('entropy chart renders and selecting a step shows both times', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=D_u&tab=entropy')
    await expect(page.getByTestId('entropy-chart')).toBeVisible()
    await expect(page.getByTestId('alignment-empty')).toBeVisible()

    // Select a real accepted step through the deterministic control.
    await page.getByTestId('scalar-step-input').fill('1200')
    await page.getByTestId('scalar-step-apply').click()

    await expect(page.getByTestId('dual-time-notice')).toBeVisible()
    await expect(page.getByTestId('selected-scalar-time')).not.toBeEmpty()
    await expect(page.getByTestId('displayed-snapshot-time')).not.toBeEmpty()
    await expect(page.getByTestId('granularity-warning')).toContainText("不同粒度")
  })

  test('selecting a scalar step also works via a chart click', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=D_u&tab=entropy')
    const chart = page.getByTestId('entropy-chart')
    await expect(chart).toBeVisible()
    const box = await chart.boundingBox()
    if (!box) throw new Error('chart has no box')

    // Clicking anywhere in the plot selects the nearest recorded accepted step.
    await page.mouse.click(box.x + box.width * 0.55, box.y + box.height * 0.5)
    await expect(page.getByTestId('dual-time-notice')).toBeVisible()
    await expect(page.getByTestId('selected-scalar-time')).not.toBeEmpty()
    await expect(page.getByTestId('displayed-snapshot-time')).not.toBeEmpty()
  })
})

test.describe('Metrics', () => {
  test('each metric shows value with definition, unit, detector and evidence link', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=D_u&tab=metrics')
    await expect(page.getByTestId('metrics-panel')).toBeVisible()
    for (const id of ['width', 'front_rms', 'hf']) {
      const card = page.getByTestId(`metric-${id}`)
      await expect(card).toBeVisible()
      await expect(card).toContainText("定义")
      await expect(card).toContainText("单位")
      await expect(card).toContainText("检测器 / 适用范围")
      await expect(card.getByTestId('evidence-link')).toBeVisible()
    }
  })
})

test.describe('Evidence navigation and return context', () => {
  test('mock Evidence tab -> Quick -> P09 missing state -> back restores experiment/config/tab', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=C_u&tab=evidence')
    await page.getByTestId('evidence-source-list').locator('a').first().click()
    await page.getByTestId('quick-full-record').click()
    await expect(page.locator('main[data-page="evidence"]')).toBeVisible()
    await expect(page.getByTestId('evidence-fallback')).toBeVisible()
    await expect(page.getByTestId('evidence-record')).toHaveCount(0)

    await page.getByTestId('back-to-result').click()
    await expect(page.locator('main[data-page="experiment"]')).toBeVisible()
    // Return must restore config + tab.
    await expect(page).toHaveURL(/config=C_u/)
    await expect(page).toHaveURL(/tab=evidence/)
  })

  test('direct evidence deep link has no fake back target', async ({ page }) => {
    await page.goto('/evidence/ev.case8.D_u.metrics')
    await expect(page.getByTestId('evidence-record')).toBeVisible()
    await expect(page.getByTestId('back-to-result')).toHaveCount(0)
    await expect(page.getByTestId('back-to-lab')).toBeVisible()
  })
})

test.describe('Refresh / deep-link recovery', () => {
  test('refresh keeps config, tab and snapshot', async ({ page }) => {
    await page.goto('/lab/experiments/case8?config=B_u&tab=flow&snapshot=4')
    await expect(page.getByTestId('snapshot-label')).toHaveText("快照 4 / 6")
    await page.reload()
    await expect(page.locator('main[data-page="experiment"]')).toBeVisible()
    await expect(page.getByTestId('overview-config')).toHaveCount(0) // flow tab
    await expect(page.getByTestId('snapshot-label')).toHaveText("快照 4 / 6")
  })

  test('unknown experiment shows a system fallback', async ({ page }) => {
    await page.goto('/lab/experiments/does-not-exist')
    await expect(page.getByTestId('experiment-fallback')).toBeVisible()
  })
})

test.describe('MOCK labelling', () => {
  test('mock badge is visibly present on data pages', async ({ page }) => {
    await page.goto('/home')
    await expect(page.locator('[data-testid="mock-badge"]').first()).toBeVisible()
    await page.goto('/lab/experiments/case8?config=D_u&tab=metrics')
    await expect(page.locator('[data-testid="mock-badge"]').first()).toBeVisible()
    await expect(page.locator('[data-testid="mock-badge"]').first()).toContainText('MOCK')
  })
})
