import { test, expect, type Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

async function open(page: Page, path = '/lab/mechanism') {
  await page.goto(path)
  await expect(page.getByTestId('mechanism-architecture')).toBeVisible()
  await expect(page.getByTestId('schematic-badge')).toHaveText('SCHEMATIC')
  await expect(page.getByTestId('mock-badge')).toHaveCount(0)
}

test('Lab route opens/reloads CONTENT03 real API with every registered node and edge', async ({ page }) => {
  await page.goto('/lab')
  const responsePromise = page.waitForResponse(r => r.url().endsWith('/api/v1/mechanism'))
  await page.getByTestId('lab-open-mechanism').click()
  const response = await responsePromise
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.availability).toBe('AVAILABLE')
  expect(body.data.data_origin).toBe('SCHEMATIC')
  expect(body.data.nodes).toHaveLength(11)
  expect(body.data.edges).toHaveLength(13)
  await expect(page.getByTestId('mechanism-architecture')).toBeVisible()
  for (const node of body.data.nodes) await expect(page.getByTestId(`node-${node.id}`)).toBeVisible()
  for (const edge of body.data.edges) await expect(page.locator(`[data-from="${edge.from_node}"][data-to="${edge.to_node}"]`)).toHaveCount(1)
  for (const node of body.data.nodes) {
    await page.getByTestId(`node-${node.id}`).click()
    await expect(page.getByTestId('selected-node')).toContainText(node.explanation)
  }
  await page.reload()
  await expect(page.getByTestId('schematic-badge')).toHaveText('SCHEMATIC')
  const output = fileURLToPath(new URL('../../.cache/phase10-window2/', import.meta.url))
  mkdirSync(output, { recursive: true })
  await page.setViewportSize({ width: 1500, height: 1000 })
  await page.screenshot({ path: `${output}mechanism-workspace.png`, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: `${output}mechanism-narrow.png`, fullPage: true })
  await page.getByTestId('mechanism-return').click()
  await expect(page).toHaveURL(/\/lab$/)
})

for (const state of ['STRICT_1D', 'WEAKLY_2D']) {
  for (const qat of ['OFF', 'ENABLED']) {
    test(`${state} / q_at ${qat}: receiving content and output remain separate from trigger`, async ({ page }) => {
      await open(page)
      const requests: string[] = []
      page.on('request', r => { if (r.url().includes('/api/')) requests.push(r.url()) })
      await page.getByTestId('mechanism-state').selectOption(state)
      await page.getByTestId('mechanism-qat').selectOption(qat)
      await expect(page.getByTestId('receiving-state')).toHaveText(state === 'STRICT_1D' ? 'zero' : 'nonzero')
      await expect(page.getByTestId('output-state')).toHaveText(qat === 'OFF' ? 'Pathway disabled' : state === 'STRICT_1D' ? 'Inactive / zero' : 'Active — conditional on acoustic trigger')
      await expect(page.getByTestId('gate-state')).toContainText('Trigger retained — may be nonzero')
      await expect(page.getByTestId('node-acoustic-gate')).toContainText('Acoustic trigger may remain nonzero')
      await expect(page.getByTestId('node-tangential-output')).toContainText(qat === 'OFF' ? 'Pathway disabled' : state === 'STRICT_1D' ? 'Inactive / zero' : 'Active')
      await expect(page.getByTestId('mechanism-view')).not.toContainText(/gate off|gate = 0|trigger = 0/i)
      expect(requests).toEqual([])
      await page.reload()
      await expect(page.getByTestId('mechanism-state')).toHaveValue(state)
      await expect(page.getByTestId('mechanism-qat')).toHaveValue(qat)
    })
  }
}

test('trigger/output have distinct visual and semantic roles; keyboard and delta_t wording', async ({ page }) => {
  await open(page)
  const trigger = page.getByTestId('node-acoustic-gate')
  const output = page.getByTestId('node-tangential-output')
  await expect(trigger).toHaveAttribute('data-role', 'TRIGGER')
  await expect(output).toHaveAttribute('data-role', 'OUTPUT')
  expect(await trigger.locator('rect').evaluate(el => getComputedStyle(el).strokeDasharray)).not.toBe('none')
  expect(await output.locator('rect').evaluate(el => getComputedStyle(el).strokeDasharray)).toBe('none')
  await output.focus()
  await page.keyboard.press('Enter')
  await expect(output).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByTestId('selected-node')).toContainText('δ_t does not enter gate, but tangential receiving content affects output amplitude.')
  await trigger.click()
  await expect(page.getByTestId('selected-node')).toContainText('J uses acoustic / normal information')
  await expect(page.locator('[data-from="tangential-content"][data-to="acoustic-gate"]')).toHaveCount(0)
  await expect(page.locator('[data-from="tangential-content"][data-to="tangential-output"]')).toHaveCount(1)
})

test('Near1D theory only; no sliders, numeric points or numerical chart', async ({ page }) => {
  await open(page)
  await expect(page.getByTestId('near1d-gap')).toHaveText('No authoritative five-epsilon raw numerical scan is registered.')
  await expect(page.getByTestId('mechanism-limitations')).toContainText('O(epsilon)')
  await expect(page.getByTestId('mechanism-limitations')).toContainText('O(epsilon^2)')
  await expect(page.locator('input, [role="slider"], canvas')).toHaveCount(0)
  await expect(page.locator('select')).toHaveCount(2)
  await expect(page.getByTestId('mechanism-state').locator('option')).toHaveCount(2)
  await expect(page.getByTestId('mechanism-qat').locator('option')).toHaveCount(2)
  await expect(page.getByTestId('mechanism-limitations').locator('svg, img, table')).toHaveCount(0)
})

test('node evidence quick/detail uses EVI02 and restores full mechanism state', async ({ page }) => {
  await open(page, '/lab/mechanism?source_scene=3&state=WEAKLY_2D&q_at=OFF&node=tangential-output')
  await expect(page.getByTestId('mechanism-evidence')).toContainText('Theory:')
  await expect(page.getByTestId('mechanism-evidence')).toContainText('Implementation:')
  await expect(page.getByTestId('mechanism-evidence')).toContainText('Numerical result:')
  const responsePromise = page.waitForResponse(r => r.url().includes('/api/v1/evidence/'))
  await page.getByTestId('evidence-link').first().click()
  expect((await responsePromise).status()).toBe(200)
  await expect(page.getByTestId('evidence-quick-view')).toContainText('Method hash:')
  await expect(page.getByTestId('evidence-quick-view')).not.toContainText('Method hash: UNKNOWN')
  await page.getByTestId('quick-full-record').click()
  await expect(page.getByTestId('evidence-record')).toBeVisible()
  await expect(page.getByTestId('mechanism-evidence-context')).toContainText('they do not certify the schematic as CFD numerical verification')
  await page.getByTestId('back-to-result').click()
  await expect(page.getByTestId('mechanism-state')).toHaveValue('WEAKLY_2D')
  await expect(page.getByTestId('mechanism-qat')).toHaveValue('OFF')
  await expect(page.getByTestId('selected-node')).toContainText('Tangential output')
  await expect(page.getByTestId('mechanism-return')).toContainText('Explore S3')
})

for (const scene of [2, 3]) {
  test(`Explore S${scene} shares MechanismView, returns to source_scene and browser Back works`, async ({ page }) => {
    const responsePromise = page.waitForResponse(r => r.url().includes(`/api/v1/explore/scenes/${scene}`))
    await open(page, `/explore?scene=${scene}&state=WEAKLY_2D&q_at=OFF&node=tangential-output`)
    expect((await responsePromise).status()).toBe(200)
    await expect(page.getByTestId('scene-title')).toContainText(`S${scene}`)
    await expect(page.getByTestId('mechanism-view')).toHaveCount(1)
    await expect(page.getByTestId('mechanism-state')).toHaveCount(scene === 3 ? 1 : 0)
    await page.getByTestId('explore-open-mechanism').click()
    await expect(page).toHaveURL(new RegExp(`source_scene=${scene}`))
    await expect(page.getByTestId('mechanism-view')).toHaveCount(1)
    await expect(page.getByTestId('mechanism-state')).toHaveValue('WEAKLY_2D')
    await page.goBack()
    await expect(page.getByTestId('scene-title')).toContainText(`S${scene}`)
    await page.getByTestId('explore-open-mechanism').click()
    await page.getByTestId('mechanism-qat').selectOption('ENABLED')
    await page.getByTestId('mechanism-return').click()
    await expect(page.getByTestId('scene-title')).toContainText(`S${scene}`)
    await expect(page.getByTestId('output-state')).toContainText('Active')
    await page.reload()
    await expect(page.getByTestId('scene-title')).toContainText(`S${scene}`)
  })
}

test('browser Back restores discrete state and node selection', async ({ page }) => {
  await open(page)
  await page.getByTestId('mechanism-state').selectOption('WEAKLY_2D')
  await page.getByTestId('mechanism-qat').selectOption('OFF')
  await page.getByTestId('node-tangential-output').click()
  await page.goBack()
  await expect(page.getByTestId('selected-node')).toContainText('Acoustic gate J')
  await page.goBack()
  await expect(page.getByTestId('mechanism-qat')).toHaveValue('ENABLED')
  await page.goBack()
  await expect(page.getByTestId('mechanism-state')).toHaveValue('STRICT_1D')
})

for (const outage of ['network', 'http', 'envelope', 'origin']) {
  test(`CONTENT03 ${outage} failure shows error, no mock fallback; retry recovers`, async ({ page }) => {
    const matcher = '**/api/v1/mechanism'
    await page.route(matcher, async route => {
      if (outage === 'network') return route.abort('failed')
      if (outage === 'http') return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ availability: 'ERROR', error: { message: 'Unavailable' } }) })
      const actual = await route.fetch()
      const body = await actual.json()
      if (outage === 'envelope') body.availability = 'ERROR'
      if (outage === 'origin') body.data.data_origin = 'MOCK'
      await route.fulfill({ response: actual, json: body })
    })
    await page.goto('/lab/mechanism')
    await expect(page.getByRole('alert')).toContainText('Error loading mechanism content')
    await expect(page.getByTestId('mechanism-architecture')).toHaveCount(0)
    await expect(page.getByTestId('mechanism-state')).toHaveCount(0)
    await expect(page.getByTestId('mock-badge')).toHaveCount(0)
    await expect(page.getByTestId('provider-kind')).toHaveText('REAL API')
    await page.unroute(matcher)
    await page.getByRole('button', { name: 'Retry real API' }).click()
    await expect(page.getByTestId('mechanism-architecture')).toBeVisible()
  })
}

test('evidence outage leaves schematic visible and shows no fabricated record', async ({ page }) => {
  await open(page)
  await page.route('**/api/v1/evidence/**', r => r.abort('failed'))
  await page.getByTestId('evidence-link').first().click()
  await expect(page.getByRole('alert')).toContainText('Error loading evidence quick view')
  await expect(page.getByTestId('mechanism-architecture')).toBeVisible()
  await expect(page.getByTestId('evidence-quick-view')).not.toContainText('Method hash:')
})

test('Explore metadata outage and invalid scene cannot fabricate S2/S3', async ({ page }) => {
  await page.route('**/api/v1/explore/scenes/3', r => r.abort('failed'))
  await page.goto('/explore?scene=3')
  await expect(page.getByRole('alert')).toContainText('Error loading Explore scene')
  await expect(page.getByTestId('mechanism-view')).toHaveCount(0)
  await page.goto('/explore?scene=8')
  await expect(page.getByRole('alert')).toContainText('Error loading Explore scene')
  await expect(page.getByTestId('mechanism-view')).toHaveCount(0)
})
