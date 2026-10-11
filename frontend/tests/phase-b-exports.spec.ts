import { test, expect, type Page } from '@playwright/test'
import { mkdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const runId = process.env.E2E_EXPORT_RUN_ID ?? '08f92162-b308-47ac-9a61-4aa1af08c048'
const artifacts = fileURLToPath(new URL('../../output/playwright/phase-b/', import.meta.url))
mkdirSync(artifacts, { recursive: true })
const center = (page: Page) => page.getByTestId('run-export-center')
test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: 'ignoreErrors' }) })
async function open(page: Page) {
  await page.goto(`/runs/${runId}`)
  await expect(page.getByTestId('run-status')).toHaveText('已完成')
  await expect(center(page).getByRole('button', { name: '下载原始数据包', exact: true })).toBeEnabled()
  await center(page).scrollIntoViewIfNeeded()
}
async function save(page: Page, label: string, filename: string) {
  const pending = page.waitForEvent('download')
  await center(page).getByRole('button', { name: label, exact: true }).click()
  const download = await pending
  expect(download.suggestedFilename()).toBe(filename)
  await download.saveAs(artifacts + filename)
  expect(await download.failure()).toBeNull()
  expect(readFileSync(artifacts + filename).byteLength).toBeGreaterThan(1024)
  return download
}

test('three equal cards download verified real ZIPs and reuse existing exports', async ({ page, request }) => {
  const before = (await (await request.get(`/api/v2/runs/${runId}/exports`)).json()).data
  await open(page)
  await expect(center(page).getByRole('heading', { name: '实验结果 · 导出中心' })).toBeVisible()
  await expect(center(page).locator('.export-card')).toHaveCount(3)
  const cards = await center(page).locator('.export-card').all()
  const boxes = await Promise.all(cards.map(card => card.boundingBox()))
  expect(Math.max(...boxes.map(b => b!.width)) - Math.min(...boxes.map(b => b!.width))).toBeLessThan(1)
  expect(new Set(boxes.map(b => Math.round(b!.y))).size).toBe(1)
  await save(page, '下载原始数据包', `ShockPath_${runId}_raw_data.zip`)
  await save(page, '下载流场文件', `ShockPath_${runId}_flow_field.zip`)
  await save(page, '下载实验报告', `ShockPath_${runId}_experiment_report.zip`)
  await expect(page.getByTestId('export-status-report')).toContainText('下载已开始')
  const after = (await (await request.get(`/api/v2/runs/${runId}/exports`)).json()).data
  for (const kind of ['raw', 'visualization', 'report']) {
    expect(after.exports[kind].status).toBe('READY')
    if (before.exports[kind].status === 'READY') expect(after.exports[kind].generated_at).toBe(before.exports[kind].generated_at)
  }
  await center(page).screenshot({ path: artifacts + 'export-center-1440.png' })
  await page.screenshot({ path: artifacts + 'run-workspace-1440.png', fullPage: true })
})

test('report offers actual HTML and A4 PDF downloads', async ({ page }) => {
  await open(page)
  await page.getByLabel('报告下载格式').selectOption('html')
  await save(page, '下载实验报告', `ShockPath_${runId}_report.html`)
  expect(readFileSync(artifacts + `ShockPath_${runId}_report.html`, 'utf8')).toContain(runId)
  await page.getByLabel('报告下载格式').selectOption('pdf')
  await save(page, '下载实验报告', `ShockPath_${runId}_report.pdf`)
  expect(readFileSync(artifacts + `ShockPath_${runId}_report.pdf`).subarray(0, 5).toString()).toBe('%PDF-')
})

test('failed and cancelled real Runs explain unavailable export', async ({ page, request }) => {
  for (const state of ['FAILED', 'CANCELLED']) {
    const response = await request.get(`/api/v2/runs?status=${state}&limit=1`)
    const record = (await response.json()).data.runs[0]
    expect(record).toBeDefined()
    await page.goto(`/runs/${record.run_id}`)
    await expect(center(page)).toContainText('本次运行尚未成功完成')
    for (const label of ['下载原始数据包', '下载流场文件', '下载实验报告']) await expect(center(page).getByRole('button', { name: label, exact: true })).toBeDisabled()
  }
})

test('service failure disables cards and reconnect recovers real availability', async ({ page }) => {
  const url = `**/api/v2/runs/${runId}/exports`
  await page.route(url, route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { message: '测试：服务暂不可用', code: 'EXPORT_SERVICE_BUSY' } }) }))
  await page.goto(`/runs/${runId}`)
  await expect(page.getByTestId('export-service-error')).toContainText('导出服务不可用')
  await expect(center(page).getByRole('button', { name: '下载原始数据包', exact: true })).toBeDisabled()
  await page.unroute(url)
  await center(page).getByRole('button', { name: '重新连接' }).click()
  await expect(center(page).getByRole('button', { name: '下载原始数据包', exact: true })).toBeEnabled()
})

test('generation and download failures stay in the export card and are retryable', async ({ page }) => {
  await open(page)
  const url = `**/api/v2/runs/${runId}/exports/raw?format=zip`
  await page.route(url, route => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: { message: '测试：导出生成失败', code: 'EXPORT_GENERATION_FAILED' } }) }))
  await center(page).getByRole('button', { name: '下载原始数据包', exact: true }).click()
  await expect(page.getByTestId('export-card-raw')).toContainText('导出生成失败')
  await page.unroute(url)
  const downloadUrl = `**/api/v2/runs/${runId}/exports/raw/download?format=zip`
  await page.route(downloadUrl, route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { message: '测试：下载连接失败' } }) }))
  await center(page).getByRole('button', { name: '下载原始数据包', exact: true }).click()
  await expect(page.getByTestId('export-card-raw')).toContainText('文件下载失败')
  await expect(page.getByTestId('final-density')).toBeVisible()
  await page.unroute(downloadUrl)
  await save(page, '下载原始数据包', `ShockPath_${runId}_raw_data.zip`)
  await expect(page.getByTestId('export-card-raw').getByRole('alert')).toHaveCount(0)
})

test('generation feedback prevents duplicate clicks', async ({ page }) => {
  await open(page)
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route(`**/api/v2/runs/${runId}/exports/raw?format=zip`, async route => { await gate; await route.continue() })
  const button = center(page).getByRole('button', { name: '下载原始数据包', exact: true })
  await button.click()
  await expect(page.getByTestId('export-status-raw')).toContainText('正在生成')
  await expect(button).toBeDisabled()
  const pending = page.waitForEvent('download'); release()
  const download = await pending; expect(await download.failure()).toBeNull()
  await expect(button).toBeEnabled()
})

test('PDF unavailable is explicit while actual HTML still downloads', async ({ page }) => {
  await page.route(`**/api/v2/runs/${runId}/exports`, async route => {
    const response = await route.fetch(), json = await response.json()
    json.data.capabilities.report.formats = ['HTML']
    json.data.capabilities.report.unavailable_formats = { PDF: '测试：缺少 Chromium 依赖；HTML 仍可下载。' }
    await route.fulfill({ response, json })
  })
  await open(page)
  await expect(page.getByTestId('export-pdf-unavailable')).toContainText('PDF 不可用')
  await expect(page.getByLabel('报告下载格式').locator('option[value="pdf"]')).toHaveCount(0)
  await page.getByLabel('报告下载格式').selectOption('html')
  await save(page, '下载实验报告', `ShockPath_${runId}_report.html`)
})

test('mobile retains three columns without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await open(page)
  const boxes = await Promise.all((await center(page).locator('.export-card').all()).map(card => card.boundingBox()))
  expect(new Set(boxes.map(b => Math.round(b!.y))).size).toBe(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await center(page).screenshot({ path: artifacts + 'export-center-390.png' })
})
