// Real-browser acceptance; every submitted run is computed by the P3 daemon.
import { chromium, expect } from '../../frontend/node_modules/@playwright/test/index.mjs'
import { spawn, spawnSync } from 'node:child_process'
import { createWriteStream, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../..', import.meta.url))
const python = path.join(root, '.venv/Scripts/python.exe')
const out = path.join(root, 'docs/v2')
const base = 'http://127.0.0.1:4434'
const api = 'http://127.0.0.1:5124'
const log = createWriteStream(path.join(out, 'p3_browser_server.log'))
const servers = []
const report = { status: 'RUNNING', started_at: new Date().toISOString(), checks: {} }
let browser
function launch(cmd, args, cwd, env) {
  const child = spawn(cmd, args, { cwd, env: { ...process.env, ...env }, windowsHide: true })
  child.stdout.pipe(log, { end: false }); child.stderr.pipe(log, { end: false })
  servers.push(child)
}
function save(name, value) {
  report.checks[name] = { status: 'PASS', ...value }
  writeFileSync(path.join(out, 'p3_browser_acceptance.json'), JSON.stringify(report, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ check: name, status: 'PASS' }) + '\n')
}
async function ready(url) {
  for (let i = 0; i < 150; i++) {
    try { if ((await fetch(url)).ok) return } catch {}
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  throw new Error('Server readiness timeout: ' + url)
}
try {
  launch(python, ['-B', '-m', 'scripts.serve_backend'], root, { API_PORT: '5124', DEEPSEEK_API_KEY: '' })
  await ready(api + '/api/v2/cases')
  launch('pwsh', ['-NoProfile', '-Command', '& npm.cmd run preview -- --port 4434 --strictPort'],
    path.join(root, 'frontend'), { API_PROXY_TARGET: api })
  await ready(base)
  browser = await chromium.launch()
  const context = await browser.newContext({ viewport: { width: 1365, height: 900 } })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(base + '/experiments/new')
  await expect(page.getByTestId('execution-ready')).toBeVisible()
  await expect(page.getByRole('button', { name: '启动求解', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: '验证配置', exact: true }).click()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '确认配置', exact: true }).click()
  await expect(page.getByRole('button', { name: '启动求解', exact: true })).toBeEnabled()
  const submissions = []
  let lost = true
  let firstId
  await page.route('**/api/v2/runs', async route => {
    if (route.request().method() !== 'POST') { await route.continue(); return }
    submissions.push(route.request().postDataJSON())
    if (lost) {
      const accepted = await route.fetch()
      expect(accepted.status()).toBe(202)
      firstId = (await accepted.json()).data.run_id
      lost = false
      await route.abort('failed')
    } else { await route.continue() }
  })
  await page.getByRole('button', { name: '启动求解', exact: true }).click()
  await expect(page.getByTestId('builder-error')).toBeVisible()
  await page.getByRole('button', { name: '启动求解', exact: true }).click()
  await expect(page).toHaveURL(new RegExp('/runs/' + firstId + '$'))
  expect(submissions).toHaveLength(2)
  expect(submissions[0].idempotency_key).toBe(submissions[1].idempotency_key)
  save('builder_and_lost_response_retry', { run_id: firstId, same_idempotency_key: true, accepted_status: 202 })
  const second = await context.newPage()
  await second.goto(base + '/experiments/new')
  await second.getByRole('button', { name: '专业参数', exact: true }).click()
  await second.getByLabel('q_at', { exact: true }).selectOption('0')
  await second.getByRole('button', { name: '验证配置', exact: true }).click()
  await second.getByRole('checkbox').check()
  await second.getByRole('button', { name: '确认配置', exact: true }).click()
  await second.getByRole('button', { name: '启动求解', exact: true }).click()
  await expect(second.getByTestId('run-status')).toHaveText('排队中')
  await second.getByRole('button', { name: '取消运行', exact: true }).click()
  await expect(second.getByTestId('run-status')).toHaveText('已取消')
  const secondId = new URL(second.url()).pathname.split('/').at(-1)
  save('professional_submission_and_queued_cancel', { run_id: secondId, status: 'CANCELLED' })
  await expect(page.getByTestId('real-progress')).toBeVisible({ timeout: 20000 })
  await page.route('**/events*', route => route.abort())
  await page.reload()
  await expect(page.getByText('事件连接中断，正在通过状态查询刷新')).toBeVisible({ timeout: 10000 })
  await expect(page.getByTestId('run-status')).toHaveText('已完成', { timeout: 60000 })
  await expect(page.getByTestId('final-density')).toBeVisible({ timeout: 10000 })
  await expect(page.getByTestId('snapshot-canvas')).toHaveAttribute('width', '64')
  await expect(page.getByTestId('snapshot-canvas')).toHaveAttribute('height', '16')
  await expect(page.getByTestId('run-log')).toContainText('step=478/478')
  await page.screenshot({ path: path.join(out, 'p3_workspace_desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: path.join(out, 'p3_workspace_mobile.png'), fullPage: true })
  await page.reload()
  await expect(page.getByTestId('final-density')).toBeVisible({ timeout: 10000 })
  save('reload_polling_final_density_and_mobile', { run_id: firstId, completed_steps: 478, canvas: [16, 64],
    screenshots: ['p3_workspace_desktop.png', 'p3_workspace_mobile.png'], mobile_no_overflow: true })
  await page.goto(base + '/workspace')
  await expect(page.getByTestId('run-list-item').filter({ hasText: firstId })).toBeVisible()
  await page.getByLabel('运行状态').selectOption('CANCELLED')
  await expect(page.getByTestId('run-list-item').filter({ hasText: secondId })).toBeVisible()
  await page.goto(base + '/runs/00000000-0000-4000-8000-000000000000')
  await expect(page.getByTestId('run-error')).toContainText('运行记录不存在')
  expect(errors).toEqual([])
  save('list_filter_unknown_run_and_console', { unknown_run: 404, page_errors: errors })
  report.status = 'PASS'
  report.finished_at = new Date().toISOString()
  writeFileSync(path.join(out, 'p3_browser_acceptance.json'), JSON.stringify(report, null, 2) + '\n')
} catch (error) {
  report.status = 'FAIL'; report.error = String(error)
  writeFileSync(path.join(out, 'p3_browser_acceptance.json'), JSON.stringify(report, null, 2) + '\n')
  throw error
} finally {
  await browser?.close()
  for (const child of servers.reverse()) {
    if (child.exitCode === null) spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true })
  }
  log.end()
}
