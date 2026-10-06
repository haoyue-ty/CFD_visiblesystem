import { test, expect, type Page } from '@playwright/test'

const paper = 'case8.paper.D_u'
async function open(page: Page) {
  await page.goto('/experiments/new')
  await expect(page.locator('main[data-page="experiment-builder"]')).toBeVisible()
  await expect(page.getByLabel('起始模板')).toBeVisible()
}
async function validate(page: Page) {
  await page.getByRole('button', { name: '验证配置', exact: true }).click()
  await expect(page.getByTestId('config-hash')).toContainText(/^[0-9a-f]{64}$/)
}

test('template and form share hash, paper changes preserve lineage, confirmation invalidates', async ({ page }) => {
  const runs: string[] = []
  page.on('request', req => { if (req.url().includes('/api/v2/runs')) runs.push(req.url()) })
  await open(page)
  await expect(page.getByTestId('execution-ready')).toContainText('后台运行服务在线')
  await page.getByLabel('起始模板').selectOption(paper)
  await validate(page)
  await expect(page.getByTestId('classification')).toHaveText('论文标准配置的新运行')
  const originalHash = await page.getByTestId('config-hash').innerText()
  await page.getByRole('button', { name: '专业参数', exact: true }).click()
  await validate(page)
  await expect(page.getByTestId('config-hash')).toHaveText(originalHash)
  await page.getByLabel('q_at', { exact: true }).selectOption('0')
  await expect(page.getByTestId('config-hash')).toHaveCount(0)
  await validate(page)
  await expect(page.getByTestId('classification')).toHaveText('论文模板 · 自定义参数')
  await expect(page.getByTestId('protocol-diff')).toContainText('0.396')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '确认配置', exact: true }).click()
  await expect(page.getByTestId('config-confirmed')).toContainText('尚未创建 Run')
  await expect(page.getByRole('button', { name: '启动求解', exact: true })).toBeEnabled()
  await page.getByLabel('网格', { exact: true }).selectOption('64x16')
  await expect(page.getByTestId('config-confirmed')).toHaveCount(0)
  await validate(page)
  await expect(page.getByTestId('config-summary')).toContainText('64 × 16')
  await expect(page.getByTestId('protocol-diff')).toContainText('Nx')
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  expect(runs).toEqual([])
})

test('benchmarked fast and unavailable AI stay explicit; reload and navigation work', async ({ page }) => {
  await page.goto('/home')
  await page.getByTestId('new-experiment-entry').getByRole('link').click()
  await expect(page).toHaveURL(/\/experiments\/new$/)
  await validate(page)
  await expect(page.getByTestId('classification')).toHaveText('普通配置')
  await expect(page.getByTestId('config-summary')).toContainText('已通过本机重复 benchmark')
  await page.getByRole('button', { name: '自然语言', exact: true }).click()
  await page.getByLabel('实验要求').fill('D_u 论文模板')
  await expect(page.getByText('自然语言服务未配置密钥。可以继续使用模板或专业参数。')).toBeVisible()
  await expect(page.getByRole('button', { name: '生成配置草稿' })).toBeDisabled()
  await page.reload()
  await expect(page.getByLabel('起始模板')).toBeVisible()
  await page.getByRole('button', { name: '专业参数', exact: true }).click()
  await validate(page)
  await expect(page.getByTestId('config-hash')).toBeVisible()
})

test('natural language UI uses real validation summary and requires clarification', async ({ page, request }) => {
  const cases = (await (await request.get('/api/v2/cases')).json()).data
  const config = cases.cases[0].templates.find((t: { template_id: string }) => t.template_id === paper).config
  const revision = cases.cases[0].capability_revision
  const validated = (await (await request.post('/api/v2/experiments/validate', { data: {
    config, submission: { input_mode: 'natural_language', template_id: paper, natural_language_text: 'D_u 论文模板',
      parser_version: 'case8.nl.p1.1', capability_revision: revision },
  } })).json()).data
  // Explicit test fixture for the external service; production never has an AI fallback.
  await page.route('**/api/v2/cases', route => route.fulfill({ json: { schema_version: '2.0.0', request_id: 'browser-fixture',
    data: { ...cases, natural_language_available: true }, warnings: [] } }))
  let ambiguous = false
  await page.route('**/api/v2/experiments/parse-natural-language', route => route.fulfill({ json: {
    schema_version: '2.0.0', request_id: 'browser-fixture', warnings: [], data: {
      config, template_id: paper, unresolved_fields: ambiguous ? [{ field: 'physics.epsilon', reason: '请明确扰动含义' }] : [],
      unsupported_fields: ambiguous ? [{ field: 'physics.epsilon', reason: 'epsilon 未支持' }] : [], warnings: ['AI 仅提供草稿'],
      parser_version: 'case8.nl.p1.1', source_text: ambiguous ? 'D_u epsilon=0.0001' : 'D_u 论文模板', capability_revision: revision,
      validated: ambiguous ? null : validated, ready_for_confirmation: !ambiguous,
    },
  } }))
  await open(page)
  await page.getByRole('button', { name: '自然语言', exact: true }).click()
  await page.getByLabel('实验要求').fill('D_u 论文模板')
  await page.getByRole('button', { name: '生成配置草稿' }).click()
  await expect(page.getByTestId('config-hash')).toHaveText(validated.config_hash)
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '确认配置', exact: true }).click()
  await expect(page.getByTestId('config-confirmed')).toBeVisible()
  ambiguous = true
  await page.getByLabel('实验要求').fill('D_u epsilon=0.0001')
  await page.getByRole('button', { name: '生成配置草稿' }).click()
  await expect(page.getByTestId('natural-language-draft')).toContainText('待澄清')
  await expect(page.getByTestId('natural-language-draft')).toContainText('未支持')
  await expect(page.getByTestId('config-hash')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '确认配置', exact: true })).toHaveCount(0)
})

test('backend capability errors are shown and retry can validate', async ({ page }) => {
  await open(page)
  await page.route('**/api/v2/experiments/validate', route => route.fulfill({ status: 409, json: {
    schema_version: '2.0.0', request_id: 'browser-fixture', error: { code: 'CAPABILITY_REVISION_CONFLICT', message: '能力版本已更新，请重新加载。',
      retryable: false, target: { resource_type: 'experiment', identity: null }, details: [] },
  } }))
  await page.getByRole('button', { name: '验证配置', exact: true }).click()
  await expect(page.getByTestId('builder-error')).toContainText('能力版本已更新')
  await expect(page.getByTestId('config-hash')).toHaveCount(0)
  await page.unroute('**/api/v2/experiments/validate')
  await validate(page)
})

test('mobile builder has no horizontal overflow and can confirm configuration', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await open(page)
  await page.getByLabel('起始模板').selectOption(paper)
  await validate(page)
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '确认配置', exact: true }).click()
  await expect(page.getByTestId('config-confirmed')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: '../docs/v2/p1_builder_mobile.png', fullPage: true })
})
