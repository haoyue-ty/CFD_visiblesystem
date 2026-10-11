import { test, expect, type Page, type APIRequestContext } from '@playwright/test'
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import type { RunRecord } from '../src/data/v2/runs'

const workspace = fileURLToPath(new URL('../..', import.meta.url))
const artifacts = `${workspace}/output/playwright/phase-a`
const cache = `${workspace}/.cache/phase-a`
mkdirSync(artifacts, { recursive: true }); mkdirSync(cache, { recursive: true })
const nav = (page: Page) => page.getByRole('navigation', { name: '系统导航', exact: true })
async function completedRun(request: APIRequestContext): Promise<RunRecord> {
  const response = await request.get('/api/v2/runs?status=COMPLETED&limit=1')
  expect(response.ok()).toBeTruthy()
  const record = (await response.json()).data.runs[0]
  expect(record, 'real completed run required for compatibility checks').toBeDefined()
  return record
}
async function active(page: Page, label: string) {
  await expect(nav(page).locator('[aria-current="page"]')).toHaveCount(1)
  await expect(nav(page).getByRole('link', { name: label, exact: true })).toHaveAttribute('aria-current', 'page')
}

test('entry opens the workspace on demand; five destinations work with visible keyboard focus', async ({ page }) => {
  await page.goto('/?layout=phase-a#recent-heading')
  await expect(page.locator('main[data-page="entry"]')).toBeVisible()
  await expect(nav(page)).toHaveCount(0)
  await page.getByTestId('start-experiment').click()
  await expect(page).toHaveURL(/\/home\?layout=phase-a#recent-heading$/)
  await expect(page.getByTestId('solver-service-status')).toHaveText('求解服务可用')
  const labels = ['首页', '新建计算', '运行任务', '算例库', '帮助']
  await expect(nav(page).getByRole('link')).toHaveText(labels)
  for (const label of labels) {
    await nav(page).getByRole('link', { name: label, exact: true }).click()
    await active(page, label)
    await expect(page.locator('main')).toBeVisible()
  }
  await page.goto('/home')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: '跳到页面内容' })).toBeFocused()
  for (let i = 0; i < 4; i++) await page.keyboard.press('Tab')
  const home = nav(page).getByRole('link', { name: '首页', exact: true })
  await expect(home).toBeFocused()
  expect(await home.evaluate(element => getComputedStyle(element).outlineStyle)).toBe('solid')
  expect(await home.evaluate(element => parseFloat(getComputedStyle(element).outlineWidth))).toBeGreaterThanOrEqual(2)
  const create = nav(page).getByRole('link', { name: '新建计算', exact: true })
  const before = await create.evaluate(element => getComputedStyle(element).backgroundColor)
  await create.hover()
  await expect.poll(() => create.evaluate(element => getComputedStyle(element).backgroundColor)).not.toBe(before)
})

test('home templates preserve backend validation and confirmation before a real Solver run', async ({ page, request }) => {
  test.setTimeout(240_000)
  const errors: string[] = [], submitted: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', req => { if (req.method() === 'POST' && /\/api\/v2\/runs$/.test(req.url())) submitted.push(req.url()) })
  await page.goto('/home')
  await page.getByTestId('quick-paper').click()
  await expect(page.getByLabel('起始模板')).toHaveValue('case8.paper.D_u')
  await expect(page.getByRole('button', { name: '启动求解', exact: true })).toBeDisabled()
  await page.goto('/home')
  await page.getByTestId('quick-fast').click()
  await expect(page.getByLabel('起始模板')).toHaveValue('case8.fast.D_u')
  await expect(page.getByTestId('config-hash')).toHaveCount(0)
  await page.getByRole('button', { name: '验证配置', exact: true }).click()
  await expect(page.getByTestId('config-hash')).toHaveText(/^[0-9a-f]{64}$/)
  const hash = await page.getByTestId('config-hash').innerText()
  await expect(page.getByRole('button', { name: '启动求解', exact: true })).toBeDisabled()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '确认配置', exact: true }).click()
  await expect(page.getByTestId('config-confirmed')).toBeVisible()
  expect(submitted).toEqual([])
  await page.getByRole('button', { name: '启动求解', exact: true }).click()
  await page.waitForURL('**/runs/*')
  const runId = new URL(page.url()).pathname.split('/').at(-1)!
  await active(page, '运行任务')
  await expect(page.getByTestId('run-status')).toHaveText('已完成', { timeout: 180_000 })
  expect(submitted).toHaveLength(1)
  await expect(page.getByTestId('real-progress')).toContainText('100.0%')
  await expect(page.getByTestId('final-density').locator('canvas')).toBeVisible()
  await expect(page.getByTestId('entropy-chart')).toBeVisible()
  await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(4)
  await expect(page.getByTestId('ai-interpret-error')).toContainText(/未配置|不可用/)
  const response = await request.get(`/api/v2/runs/${runId}/result`)
  expect(response.ok()).toBeTruthy()
  const result = (await response.json()).data
  expect(result.identity.config_hash).toBe(hash)
  expect(result.identity.data_origin).toBe('V2_LIVE_COMPUTATION')
  expect(result.config.normalized_config.grid).toMatchObject({ nx: 64, ny: 16 })
  expect(result.snapshots).toHaveLength(6)
  expect(result.runtime.accepted_steps).toBeGreaterThan(0)
  expect(result.entropy.rows.length).toBeGreaterThan(0)
  writeFileSync(`${cache}/live-run.json`, JSON.stringify({ run_id: runId, config_hash: hash, result_hash: result.result_hash, accepted_steps: result.runtime.accepted_steps }, null, 2))
  await page.screenshot({ path: `${artifacts}/completed-run-1440.png`, fullPage: true })
  await page.getByTestId('run-report-link').click()
  await active(page, '运行任务')
  await page.getByRole('button', { name: '生成实验报告', exact: true }).click()
  await expect(page.getByTestId('report-preview')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByTestId('report-ai')).toContainText('确定性报告仍可生成')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '保存 HTML', exact: true }).click()
  const download = await downloadPromise
  const reportPath = `${artifacts}/${download.suggestedFilename()}`
  await download.saveAs(reportPath)
  const html = readFileSync(reportPath, 'utf8')
  expect(html).toContain(hash); expect(html).toContain(result.result_hash)
  await page.getByRole('link', { name: '核查本次运行证据', exact: true }).click()
  await expect(page.getByTestId('run-evidence')).toContainText(result.result_hash)
  await active(page, '运行任务')
  expect(errors).toEqual([])
})

test('all preserved child routes keep a primary parent and survive reload', async ({ page, request }) => {
  test.setTimeout(180_000)
  const run = await completedRun(request)
  const scans = await request.get('/api/v2/sweeps?limit=1')
  const sweep = (await scans.json()).data.sweeps[0]
  expect(sweep, 'real sweep required for compatibility checks').toBeDefined()
  const routes = [
    ['/experiments/new', '新建计算'], ['/workspace', '运行任务'], ['/workspace/compare', '运行任务'], ['/workspace/sweeps', '运行任务'],
    [`/sweeps/${sweep.sweep_id}`, '运行任务'], [`/runs/${run.run_id}`, '运行任务'], [`/runs/${run.run_id}/report`, '运行任务'], [`/runs/${run.run_id}/evidence`, '运行任务'],
    ['/lab', '算例库'], ['/lab/experiments/case8', '算例库'], ['/lab/experiments/cylinder', '算例库'], ['/lab/mechanism', '算例库'],
    ['/cross-flow', '算例库'], ['/lab/compare/case8-cylinder', '算例库'], ['/explore?scene=1', '帮助'], ['/help', '帮助'],
    ['/evidence', '帮助'], ['/evidence/ev.case8.D_u.snapshot.6.density', '帮助'],
  ]
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
  async function ready(path: string, parent: string) {
    await active(page, parent)
    const main = page.locator('main')
    await expect(main).toBeVisible()
    if (path === '/workspace/compare') await expect(page.locator('#completed-runs option').first()).toBeAttached()
    if (path.startsWith('/workspace/sweeps') || path.startsWith('/sweeps/')) await expect(page.locator('#base-runs option').first()).toBeAttached()
    // Export cards keep accessible status messages after loading has finished.
    await expect(main.locator('[role="status"]:not([data-testid^="export-status-"])')).toHaveCount(0)
    if (path === `/runs/${run.run_id}` || path === `/runs/${run.run_id}/report`) {
      const exports = page.getByTestId('run-export-center')
      await expect(exports.locator('.export-card')).toHaveCount(3)
      await expect(exports.locator('[aria-busy="true"]')).toHaveCount(0)
      await expect(exports.getByRole('button', { name: '下载原始数据包', exact: true })).toBeEnabled()
    }
    await expect(main.locator('.ls--error')).toHaveCount(0)
    if (path === `/runs/${run.run_id}`) await expect(page.getByTestId('final-density').locator('canvas')).toBeVisible()
    if (path === `/runs/${run.run_id}/evidence`) await expect(main).toContainText(run.experiment.config_hash)
  }
  for (const [path, parent] of routes) {
    await page.goto(path!); await ready(path!, parent!)
    await page.reload(); await ready(path!, parent!)
  }
  expect(errors).toEqual([])
})

test('case library uses execution availability and keeps all recorded workspaces as replay', async ({ page, request }) => {
  const registry = (await (await request.get('/api/v2/cases')).json()).data
  await page.goto('/lab')
  const runnable = registry.cases.filter((c: { execution_available: boolean }) => c.execution_available)
  await expect(page.getByTestId('live-case-library').locator('article')).toHaveCount(runnable.length)
  await page.getByTestId('live-case-description').locator('summary').click()
  await expect(page.getByTestId('live-case-description')).toContainText('物理模型')
  await page.getByLabel('实时算例模板').selectOption('case8.paper.C_u')
  await page.getByRole('link', { name: '进入新建计算', exact: false }).click()
  await expect(page.getByLabel('起始模板')).toHaveValue('case8.paper.C_u')
  await page.goto('/lab')
  for (const id of ['case8', 'gate', 'entropy-closure', 'spectrum', 'modal-validation', 'cylinder']) {
    await expect(page.getByTestId(`lab-experiment-${id}`)).toContainText('历史数据回放')
    await expect(page.getByTestId(`lab-experiment-${id}`).getByRole('link')).not.toHaveAttribute('href', /experiments\/new/)
  }
  await expect(page.getByTestId('history-cross-flow')).toContainText('历史数据回放')
  const metadataResponse = page.waitForResponse(r => r.url().endsWith('/api/v1/experiments/cylinder'))
  await page.getByTestId('open-cylinder').click()
  expect((await metadataResponse).status()).toBe(200)
  await page.getByTestId('historical-case-info').locator('summary').first().click()
  await expect(page.getByTestId('historical-case-info')).toContainText('该算例尚未开放实时求解')
})

test('task filters use real API status and comparison / scan stay in the workspace', async ({ page }) => {
  await page.goto('/workspace')
  for (const status of ['RUNNING', 'QUEUED', 'COMPLETED', 'FAILED', 'CANCELLED']) {
    const loaded = page.waitForResponse(r => r.url().includes('/api/v2/runs?') && new URL(r.url()).searchParams.get('status') === status)
    await page.getByLabel('运行状态').selectOption(status)
    const response = await loaded, data = (await response.json()).data
    if (data.runs.length) await expect(page.getByTestId('run-list-item')).toHaveCount(data.runs.length)
    else await expect(page.getByTestId('empty-runs')).toBeVisible()
    const visibleStatuses = await page.getByTestId('run-list-item').locator('[data-status]').evaluateAll(elements => elements.map(el => el.getAttribute('data-status')))
    expect(visibleStatuses.every(s => s === status)).toBeTruthy()
  }
  await page.getByRole('navigation', { name: '运行任务分区' }).getByRole('link', { name: '运行对比', exact: true }).click()
  await expect(page.getByRole('heading', { name: '运行对比', exact: true })).toBeVisible(); await active(page, '运行任务')
  await page.getByRole('navigation', { name: '运行任务分区' }).getByRole('link', { name: '参数扫描', exact: true }).click()
  await expect(page.getByRole('heading', { name: '参数扫描', exact: true })).toBeVisible(); await active(page, '运行任务')
})

test('empty history, offline API and stopped manager are explicit without fabricated results', async ({ page, request }) => {
  const empty = await (await request.get('/api/v2/runs?limit=5')).json()
  empty.data = { ...empty.data, runs: [], total: 0 }
  await page.route('**/api/v2/runs?**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(empty) }))
  await page.goto('/home')
  await expect(page.getByTestId('empty-runs')).toContainText('创建你的第一个数值实验')
  await expect(page.getByTestId('run-list-item')).toHaveCount(0)
  await page.unroute('**/api/v2/runs?**')
  await page.route('**/api/**', route => route.abort('connectionrefused'))
  await page.reload()
  await expect(page.getByTestId('solver-service-status')).toHaveText('服务状态未知')
  await expect(page.getByTestId('recent-runs-error')).toBeVisible()
  await expect(page.getByTestId('run-list-item')).toHaveCount(0)
  await page.unroute('**/api/**')
  const unavailable = await (await request.get('/api/v2/cases')).json()
  unavailable.data.cases.forEach((c: { execution_available: boolean; execution_status: string }) => { c.execution_available = false; c.execution_status = 'STANDALONE_VERIFIED' })
  await page.route('**/api/v2/cases', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(unavailable) }))
  await page.goto('/lab')
  await expect(page.getByTestId('solver-service-status')).toHaveText('求解服务未启动')
  await expect(page.getByTestId('no-live-cases')).toBeVisible()
  await expect(page.getByTestId('live-case-library').locator('article')).toHaveCount(0)
  await page.goto('/experiments/new')
  await expect(page.getByTestId('execution-unavailable')).toBeVisible()
  await expect(page.getByRole('button', { name: '启动求解', exact: true })).toBeDisabled()
})

for (const width of [1440, 1024, 768, 390]) {
  test(`five main pages fit ${width}px with a usable sidebar and no overlap`, async ({ page }) => {
    test.setTimeout(90_000)
    await page.setViewportSize({ width, height: 900 })
    for (const [path, id] of [['/home', 'home'], ['/experiments/new', 'experiment-builder'], ['/workspace', 'run-list'], ['/lab', 'lab'], ['/help', 'help']]) {
      await page.goto(path!)
      await expect(page.locator(`main[data-page="${id}"]`)).toBeVisible()
      await expect(page.getByTestId('solver-service-status')).toHaveText('求解服务可用')
      if (path === '/home' || path === '/workspace') await expect(page.getByTestId('run-list-item').first()).toBeVisible()
      if (path === '/lab') await expect(page.getByTestId('lab-experiment-case8')).toBeVisible()
      if (path === '/experiments/new') await expect(page.getByLabel('起始模板')).toHaveValue('case8.fast.D_u')
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      if (width <= 768) await page.getByRole('button', { name: '打开导航', exact: true }).click()
      const bounds = await nav(page).getByRole('link').evaluateAll(elements => elements.map(el => { const rect = el.getBoundingClientRect(); return { x: rect.x, y: rect.y, bottom: rect.bottom, right: rect.right, width: rect.width, height: rect.height } }))
      expect(bounds).toHaveLength(5)
      expect(Math.max(...bounds.map(b => b.width)) - Math.min(...bounds.map(b => b.width))).toBeLessThan(1)
      bounds.forEach((b, i) => { expect(b.x).toBeGreaterThanOrEqual(0); expect(b.right).toBeLessThanOrEqual(width); expect(b.height).toBeGreaterThanOrEqual(44); if (i) expect(b.y).toBeGreaterThanOrEqual(bounds[i - 1]!.bottom) })
      const brand = await page.locator('.appbar__brand').boundingBox(), status = await page.locator('.appbar__env').boundingBox()
      expect(brand!.y + brand!.height).toBeLessThanOrEqual(status!.y)
      if (width <= 768) await page.getByRole('button', { name: '关闭侧栏', exact: true }).click()
      await page.screenshot({ path: `${artifacts}/${id}-${width}.png`, fullPage: true })
    }
  })
}
