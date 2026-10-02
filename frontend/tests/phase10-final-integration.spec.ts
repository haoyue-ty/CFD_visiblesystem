import { test, expect } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

test('Entry → Home → seven real Scenes → Evidence Detail → Scene → Lab → original Scene', async ({ page }) => {
  test.setTimeout(180_000)
  const errors: string[] = []
  const fatalConsole: string[] = [], failedNetwork: string[] = [], serverErrors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') fatalConsole.push(message.text()) })
  page.on('requestfailed', request => { if (!request.failure()?.errorText.includes('ERR_ABORTED')) failedNetwork.push(`${request.url()}: ${request.failure()?.errorText}`) })
  page.on('response', response => { if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`) })
  const ready = ['entropy-terminal', 'mechanism-architecture', 'mechanism-architecture', 'gate-Ungated', 'guided-modal-table', 'sector-table', 'evidence-record']
  await page.goto('/')
  await page.getByTestId('enter-system').click()
  await expect(page.locator('main[data-page="home"]')).toBeVisible()
  await page.getByTestId('home-start-explore').click()
  for (let scene = 1; scene <= 7; scene++) {
    await expect(page.getByTestId('scene-progress')).toHaveText(`第 ${scene} 幕 / 共 7 幕`)
    await expect(page.getByTestId(ready[scene - 1]!)).toBeVisible()
    await expect(page.getByTestId('provider-kind')).toHaveText("真实数据 API")
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
    if (scene === 1) await expect(page.getByTestId('scene-conclusion')).toContainText("耗散量的大小本身不足以解释")
    if (scene === 2) await expect(page.getByTestId('node-acoustic-gate')).toHaveAttribute('data-role', 'TRIGGER')
    if (scene === 3) {
      await page.getByTestId('node-tangential-output').click()
      await expect(page.getByTestId('selected-node')).toContainText("δ_t 不进入门控")
      await expect(page.getByTestId('output-state')).toContainText("输出为零")
      await page.getByTestId('mechanism-state').selectOption('WEAKLY_2D')
      await expect(page.getByTestId('output-state')).toContainText("允许输出")
      await expect(page.getByTestId('near1d-gap')).toContainText("权威五组")
    }
    if (scene === 4) await expect(page.getByTestId('cell-allocation-canvas')).toHaveCount(3)
    if (scene === 5) {
      await expect(page.getByTestId('guided-modal-table').locator('tbody tr')).toHaveCount(17)
      await expect(page.getByTestId('spectral-scientific-limit')).toContainText("正熵产 ≠ 所有模态统一增强阻尼")
    }
    if (scene === 6) {
      await expect(page.getByTestId('scene-conclusion')).toContainText("路径预算 ≠ 空间分配 ≠ 宏观响应")
      await expect(page.getByTestId('descriptive-only')).toContainText("仅作描述性比较")
      await expect(page.getByTestId('face-allocation-canvas')).toHaveCount(2)
      await expect(page.getByTestId('cumulative-2d-missing')).toContainText("缺失")
    }
    if (scene < 7) await page.getByTestId('scene-next').click()
  }
  await expect(page.getByRole('heading', { name: "来源资产", exact: true })).toBeVisible()
  await page.locator('a[data-testid="evidence-link"][href*="ev.case8.D_u.entropy"]').first().click()
  await page.getByTestId('quick-full-record').click()
  await expect(page.locator('main[data-page="evidence"]')).toBeVisible()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  const output = fileURLToPath(new URL('../../.cache/phase10-final/', import.meta.url))
  mkdirSync(output, { recursive: true })
  await page.screenshot({ path: `${output}journey-evidence.png`, fullPage: true })
  await page.getByTestId('back-to-result').click()
  await expect(page.getByTestId('scene-progress')).toHaveText("第 7 幕 / 共 7 幕")
  await page.getByTestId('scene-nav-3').click()
  await page.getByTestId('mechanism-state').selectOption('WEAKLY_2D')
  await page.getByTestId('node-tangential-output').click()
  await page.getByTestId('explore-open-lab').click()
  await expect(page).toHaveURL(/\/lab\/mechanism.*source_scene=3/)
  await page.reload()
  await expect(page.getByTestId('mechanism-state')).toHaveValue('WEAKLY_2D')
  await page.getByTestId('mechanism-return').click()
  await expect(page.getByTestId('scene-progress')).toHaveText("第 3 幕 / 共 7 幕")
  await expect(page.getByTestId('mechanism-state')).toHaveValue('WEAKLY_2D')
  await expect(page.getByTestId('selected-node')).toContainText("δ_t 不进入门控")
  expect(errors).toEqual([])
  expect(fatalConsole).toEqual([])
  expect(failedNetwork).toEqual([])
  expect(serverErrors).toEqual([])
})
