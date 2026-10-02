import { zh } from '../src/presentation/zh-CN'
import { test, expect, type Page } from '@playwright/test'
import { mkdirSync, readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const ready = ['entropy-terminal', 'mechanism-architecture', 'mechanism-architecture', 'gate-Ungated', 'guided-modal-table', 'sector-table', 'evidence-record']
async function open(page: Page, scene: number, extra = '') {
  await page.goto(`/explore?scene=${scene}${extra}`)
  await expect(page.getByTestId('scene-progress')).toHaveText(`第 ${scene} 幕 / 共 7 幕`)
  await expect(page.getByTestId(ready[scene - 1]!)).toBeVisible()
  if (scene === 1) expect(await page.getByTestId('entropy-chart').evaluate(el => el.clientWidth)).toBeGreaterThan(300)
  if (scene === 4) await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(3)
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
}

test('Home and Lab enter implemented Explore; CONTENT01 returns exactly seven presets', async ({ page, request }) => {
  const response = await request.get('/api/v1/explore/scenes')
  expect(response.ok()).toBeTruthy()
  const body = await response.json()
  expect(body.data.items.map((s: { scene_id: number }) => s.scene_id)).toEqual([1, 2, 3, 4, 5, 6, 7])
  await page.goto('/home')
  await expect(page.getByTestId('explore-status')).toContainText("已交付")
  await page.getByTestId('home-start-explore').click()
  await expect(page.getByTestId('scene-progress')).toHaveText("第 1 幕 / 共 7 幕")
  await page.goto('/lab')
  await page.getByTestId('lab-open-explore').click()
  await expect(page).toHaveURL(/scene=1/)
})

for (let scene = 1; scene <= 7; scene++) {
  test(`Scene ${scene} direct deep link, reload and production screenshot`, async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await open(page, scene)
    await expect(page.getByTestId('scene-evidence').locator('a')).not.toHaveCount(0)
    await expect(page.locator('[aria-label="场景导航"] a')).toHaveCount(7)
    await page.reload()
    await expect(page.getByTestId(ready[scene - 1]!)).toBeVisible()
    if (scene === 1) expect(await page.getByTestId('entropy-chart').evaluate(el => el.clientWidth)).toBeGreaterThan(300)
    if (scene === 4) {
      await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(3)
      await expect(page.getByTestId('gate-Ungated').getByTestId('matched-qat')).toHaveText('0.03483470441226932')
    }
    if (scene === 6) await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
    const dir = fileURLToPath(new URL('../../.cache/phase10-window3/', import.meta.url))
    mkdirSync(dir, { recursive: true })
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.screenshot({ path: `${dir}scene-${scene}.png`, fullPage: true })
    expect(errors).toEqual([])
  })
}

test('S1 reads B_u / D_u Case8 accepted histories and terminal facts verbatim', async ({ page }) => {
  for (const config of ['B_u', 'D_u']) {
    const pending = page.waitForResponse(r => r.url().includes(`/configs/${config}/entropy-history`) && r.url().includes('limit=2000'))
    await open(page, 1, `&config=${config}`)
    const body = (await (await pending).json()).data
    expect(body.config_id).toBe(config)
    expect(body.series).toHaveLength(3)
    for (const series of body.series) {
      expect(series.points).toHaveLength(1912)
      await expect(page.getByTestId('entropy-terminal')).toContainText(String(series.points.at(-1).value.value))
      expect(series.result.data_origin).toBe('VERIFIED_PRODUCTION')
    }
    await expect(page.getByTestId('explore-entropy-config').locator('option')).toHaveCount(2)
    await expect(page.getByTestId('scalar-step-input')).toHaveCount(0)
  }
})

test('S2 schematic and S3 strict/weak plus off/enabled use shared MechanismView', async ({ page }) => {
  await open(page, 2)
  await expect(page.getByTestId('mechanism-state')).toHaveCount(0)
  await expect(page.getByTestId('node-acoustic-gate')).toHaveAttribute('data-role', 'TRIGGER')
  await open(page, 3)
  await page.getByTestId('node-tangential-output').click()
  await expect(page.getByTestId('selected-node')).toContainText("δ_t 不进入门控")
  await expect(page.getByTestId('output-state')).toContainText("输出为零")
  await page.getByTestId('mechanism-state').selectOption('WEAKLY_2D')
  await expect(page.getByTestId('output-state')).toContainText("允许输出")
  await page.getByTestId('mechanism-qat').selectOption('OFF')
  await expect(page.getByTestId('output-state')).toContainText("路径关闭")
  await expect(page.getByTestId('near1d-gap')).toContainText("权威五组")
})

test('S4 Gate matched q_at, common API scale, fixed window and saved fractions', async ({ page, request }) => {
  const meta = (await (await request.get('/api/v1/allocations/comparison?experiment_id=gate')).json()).data
  await open(page, 4)
  const expected = { Acoustic: '0.4', Pressure: '0.31018332312583474', Ungated: '0.03483470441226932' }
  for (const [gate, q] of Object.entries(expected)) {
    const panel = page.getByTestId(`gate-${gate}`)
    await expect(panel.getByTestId('matched-qat')).toHaveText(q)
    await expect(panel.getByTestId('cell-allocation-canvas')).toBeVisible()
    await expect(panel.getByTestId('gate-window')).toContainText("计数=")
    const summary = (await (await request.get(`/api/v1/allocations/gate.${gate}.allocation/summary`)).json()).data
    await expect(panel.getByTestId('alloc-inside')).toHaveText(String(summary.inside.value.value.value))
    const figure = panel.locator('figure')
    await expect(figure).toHaveAttribute('data-colour-min', String(meta.shared_extent[0].value.value.value))
    await expect(figure).toHaveAttribute('data-colour-max', String(meta.shared_extent[1].value.value.value))
  }
  await expect(page.getByTestId('gate-comparison')).toContainText("预算近似匹配")
})

test('S5 complete real SPEC02 curves retain negative, positive and near-zero directions', async ({ page, request }) => {
  await open(page, 5)
  const rows = page.getByTestId('guided-modal-table').locator('tbody tr')
  await expect(rows).toHaveCount(17)
  for (const q of ['0.000', '0.396']) {
    const data = (await (await request.get(`/api/v1/spectra/spectrum.q-${q}/points`)).json()).data
    for (const point of data.points) await expect(rows.filter({ has: page.locator(`th:text-is("${point.mode_index}")`) })).toContainText(point.real_lambda.value.toFixed(10))
  }
  for (const direction of ['negative shift', 'positive shift', 'near-zero shift']) await expect(page.getByTestId('guided-modal-table')).toContainText(zh(direction))
  await expect(page.locator('tr.emphasized')).toHaveCount(2)
  await expect(page.getByTestId('spectral-scientific-limit')).toContainText("正熵产 ≠ 所有模态统一增强阻尼")
})

test('S6 CMP01 fixed D_u pair keeps independent renderers, policies and missing 2D', async ({ page }) => {
  const response = page.waitForResponse(r => r.url().includes('/api/v1/comparisons/case8-cylinder'))
  await open(page, 6, '&case8_config=A_u&cylinder_config=B_u')
  const data = (await (await response).json()).data
  expect(data.left.config_id).toBe('D_u'); expect(data.right.config_id).toBe('D_u')
  expect(data.ranking_policy).toBe('NO_UNIFIED_RANKING')
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
  await expect(page.getByTestId('front-band')).toContainText("前沿区域标量")
  await expect(page.getByTestId('cumulative-2d-missing')).toContainText("缺失")
  await expect(page.getByTestId('descriptive-only')).toContainText("仅作描述性比较")
  await expect(page.getByTestId('case8-config')).toHaveCount(0)
})

test('S7 real per-result evidence loads one record with identity/config/hash/limits; Detail returns', async ({ page }) => {
  const scienceRequests: string[] = []
  page.on('request', r => { if (r.url().includes('/api/v1/')) scienceRequests.push(r.url()) })
  await open(page, 7)
  for (const heading of ["配置", "方法与来源", "验证状态", "来源资产", "适用边界"]) await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
  expect(scienceRequests.filter(s => s.includes('/evidence/'))).toHaveLength(1)
  expect(scienceRequests.filter(s => /\/arrays\/|entropy-history|\/spectra\/|\/comparisons\//.test(s))).toEqual([])
  await page.locator('a[data-testid="evidence-link"][href*="ev.case8.D_u.entropy"]').first().click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await page.getByTestId('back-to-result').click()
  await expect(page.getByTestId('scene-progress')).toHaveText("第 7 幕 / 共 7 幕")
})

test('Previous / Next, scene navigation and browser Back restore only Scene/page', async ({ page }) => {
  await page.goto('/home'); await page.getByTestId('home-start-explore').click()
  await expect(page.getByTestId('scene-progress')).toHaveText("第 1 幕 / 共 7 幕")
  await page.getByTestId('scene-next').click()
  await expect(page.getByTestId('scene-progress')).toHaveText("第 2 幕 / 共 7 幕")
  await page.getByTestId('scene-next').click()
  await expect(page.getByTestId('scene-progress')).toHaveText("第 3 幕 / 共 7 幕")
  await page.goBack(); await expect(page.getByTestId('scene-progress')).toHaveText("第 2 幕 / 共 7 幕")
  await page.getByTestId('scene-previous').click(); await expect(page.getByTestId('scene-progress')).toHaveText("第 1 幕 / 共 7 幕")
  await page.goBack(); await page.goBack(); await page.goBack()
  await expect(page).toHaveURL(/\/home$/)
})

for (const scene of [1, 4, 5, 6, 7]) {
  test(`S${scene} Open in Lab carries legal configuration/tab/source_scene and explicit return survives reload`, async ({ page }) => {
    await open(page, scene, scene === 1 ? '&config=D_u' : '')
    const href = await page.getByTestId('explore-open-lab').getAttribute('href')
    expect(href).toContain(`source_scene=${scene}`); expect(href).toContain('tab=')
    await page.getByTestId('explore-open-lab').click()
    await expect(page.getByTestId('explore-return')).toBeVisible()
    await page.reload()
    await page.getByTestId('explore-return').click()
    await expect(page.getByTestId('scene-progress')).toHaveText(`第 ${scene} 幕 / 共 7 幕`)
    if (scene === 1) await expect(page.getByTestId('explore-entropy-config')).toHaveValue('D_u')
  })
}

for (const invalid of ['0', '8', '-1', 'abc', '1.5', '']) {
  test(`invalid scene ${JSON.stringify(invalid)} has error and no scientific content`, async ({ page }) => {
    await page.goto(`/explore?scene=${invalid}`)
    await expect(page.getByRole('alert')).toContainText('场景无效')
    await expect(page.locator('.scientific-content')).toHaveCount(0)
  })
}

for (const [scene, pattern, target] of [
  [1, '**/api/v1/experiments/case8/configs/*/entropy-history*', 'entropy history'],
  [2, '**/api/v1/mechanism', 'mechanism content'],
  [4, '**/api/v1/allocations/comparison*', 'Gate comparison'],
  [5, '**/api/v1/spectra/*/points', 'recorded spectrum curve'],
  [6, '**/api/v1/comparisons/case8-cylinder*', 'real API cross-flow comparison'],
  [7, '**/api/v1/evidence/*', 'evidence record'],
] as const) {
  test(`S${scene} scientific API failure is explicit with no mock fallback`, async ({ page }) => {
    await page.route(pattern, r => r.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ availability: 'ERROR', error: { message: 'Unavailable for outage check' } }) }))
    await page.goto(`/explore?scene=${scene}`)
    await expect(page.getByRole('alert').first()).toContainText(`数据加载失败： ${zh(target)}`)
    await expect(page.getByTestId('provider-kind')).toHaveText("真实数据 API")
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
  })
}

test('CONTENT01 outage prevents science; production bundle excludes synthetic providers', async ({ page }) => {
  await page.route('**/api/v1/explore/scenes', r => r.abort())
  await page.goto('/explore?scene=1')
  await expect(page.getByRole('alert')).toContainText("引导探索导航")
  await expect(page.getByTestId('case8-entropy')).toHaveCount(0)
  const dist = fileURLToPath(new URL('../dist/assets/', import.meta.url))
  const js = readdirSync(dist).filter(f => f.endsWith('.js')).map(f => readFileSync(`${dist}${f}`, 'utf8')).join('\n')
  for (const marker of ['createMockProvider', 'MOCK_LAYOUT_ONLY', 'MOCK_SYNTHETIC_DATA', 'lim.mock.synthetic', 'mock.case8', 'mock.gate', 'mock.spectrum', 'mock.evidence', 'mockProvider', 'Synthetic Case8']) expect(js).not.toContain(marker)
})


test('Lab edits preserve the original Explore return context', async ({ page }) => {
  await open(page, 1, '&config=D_u')
  await page.getByTestId('explore-open-lab').click()
  await page.getByTestId('config-B_u').click()
  await page.getByTestId('tab-flow').click()
  await page.reload()
  await page.getByTestId('explore-return').click()
  await expect(page.getByTestId('scene-progress')).toHaveText("第 1 幕 / 共 7 幕")
  await expect(page.getByTestId('explore-entropy-config')).toHaveValue('D_u')
})

test('rapid Scene changes and selected S7 evidence cannot display stale data', async ({ page }) => {
  await open(page, 2)
  await page.getByTestId('scene-nav-1').click()
  await page.getByTestId('scene-nav-7').click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await expect(page.getByTestId('case8-entropy')).toHaveCount(0)
  await page.getByTestId('explore-evidence-select').selectOption('ev.gate.Acoustic.allocation')
  await expect(page.getByTestId('evidence-config')).toHaveText('Acoustic')
  await expect(page.getByTestId('evidence-experiment')).toHaveText('gate')
  await page.reload()
  await expect(page.getByTestId('explore-evidence-select')).toHaveValue('ev.gate.Acoustic.allocation')
})
