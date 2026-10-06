import { test, expect } from '@playwright/test'
const run = '463bf7f2-8143-483a-9db2-81559203771b'
const custom = 'bc8cc641-951f-493c-a484-cd6b6f4eb0c6'
test('真实结果自动解读、缓存刷新和真实区域问答', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
  await page.goto(`/runs/${run}`)
  await expect(page.getByTestId('ai-cache-status')).toContainText('缓存')
  await expect(page.getByTestId('scientific-result').locator('canvas').first()).toBeVisible()
  await expect(page.getByTestId('run-ai').getByRole('link').first()).toHaveAttribute('href', `/runs/${run}/evidence`)
  await page.reload(); await expect(page.getByTestId('ai-cache-status')).toContainText('缓存')
  await page.getByLabel('科学变量').selectOption('mach')
  await page.getByLabel('真实快照').selectOption('1')
  await page.getByText('选择矩形区域', { exact: true }).click()
  for (const [key, value] of Object.entries({ x_min: '.2', x_max: '.7', y_min: '.1', y_max: '.6' })) await page.getByLabel(key, { exact: true }).fill(value)
  await page.getByRole('button', { name: '应用区域', exact: true }).click()
  await expect(page.getByTestId('ai-current-view')).toContainText('mach · step_000096 · 已选择矩形区域')
  // Browser-only fixture for answer rendering, with real deterministic region
  // numbers. Real provider answers are verified by v2_p5_live_ai separately.
  const result = await page.request.get('/api/v2/runs/'+run+'/result'); const hash = (await result.json()).data.result_hash
  const ref = (await page.request.post(`/api/v2/ai/runs/${run}/interpret`)).ok(); expect(ref).toBeTruthy()
  let sent: any
  await page.route('**/api/v2/ai/chat', async route => {
    sent = route.request().postDataJSON()
    const ctx = await page.request.get(`/api/v2/runs/${run}/snapshot/${sent.view.snapshot_id}/view-context?field=${sent.view.field}&x_min=.2&x_max=.7&y_min=.1&y_max=.6`)
    const c = (await ctx.json()).data; const id = c.evidence_id+'#view.mean'
    await route.fulfill({ json: { schema_version:'2.0.0', request_id:'browser-test', warnings:[], data:{
      run_id:run,result_hash:hash,context_hash:'browser-test',prompt_version:'case8.science.p5.5',model:'test-view-projection',created_at:'2026-10-03',cached:false,
      interpretation:null,assistant:{answer:[{kind:'INTERPRETATION',text:'此统计仅描述选中区域。',evidence_refs:[id]}],limitations:['不能证明普适稳定性。']},
      evidence:[{evidence_id:id,label:'mach · mean',value:c.mean,unit:c.unit,availability:'AVAILABLE',reason:null,definition:'真实区域统计'}],limitations:[],current_view:c,
    } } })
  })
  await page.getByLabel('科研问题', { exact: true }).fill('解释当前区域的统计。')
  await page.getByRole('button', { name:'提问', exact:true }).click()
  await expect(page.getByTestId('run-ai')).toContainText('此统计仅描述选中区域。')
  expect(sent.run_id).toBe(run); expect(sent.view).toMatchObject({field:'mach',snapshot_id:'step_000096',x_min:.2,x_max:.7,y_min:.1,y_max:.6})
  await page.screenshot({ path:'../output/playwright/p5-desktop.png', fullPage:true })
  await page.getByLabel('科学变量').selectOption('pressure')
  await expect(page.getByTestId('run-ai')).not.toContainText('此统计仅描述选中区域。')
  expect(errors).toEqual([])
})
test('无密钥和重试不影响流场；手机无横向溢出', async ({ page }) => {
  await page.setViewportSize({width:390,height:844})
  await page.route('**/api/v2/ai/runs/*/interpret', route => route.fulfill({status:503,json:{error:{code:'AI_UNAVAILABLE',message:'AI 服务未配置密钥；已有科学结果仍可使用。'}}}))
  await page.goto(`/runs/${custom}`)
  await expect(page.getByTestId('ai-interpret-error')).toContainText('未配置密钥')
  await page.getByRole('button',{name:'重试 AI 解读',exact:true}).click()
  await expect(page.getByTestId('ai-interpret-error')).toBeVisible()
  await expect(page.getByTestId('scientific-result').locator('canvas').first()).toBeVisible()
  await expect(page.getByTestId('region-statistics')).toContainText('真实 cell center')
  await page.route('**/api/v2/ai/chat', route => route.fulfill({status:503,json:{error:{code:'AI_UNAVAILABLE',message:'AI 服务超时，请重试。'}}}))
  await page.getByLabel('科研问题',{exact:true}).fill('解释当前结果。'); await page.getByRole('button',{name:'提问',exact:true}).click()
  await expect(page.getByTestId('ai-chat-error')).toContainText('超时')
  await expect(page.getByRole('button',{name:'重试问答',exact:true})).toBeEnabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({path:'../output/playwright/p5-mobile.png',fullPage:true})
})
test('旧 Run 缺失累计 face 有真实限制且仍可解读',async({page})=>{
  await page.goto('/runs/ea852646-72ce-40fc-b5f3-99329ff0895b')
  await expect(page.getByTestId('allocation-unavailable')).toBeVisible()
  await expect(page.getByTestId('ai-cache-status')).toContainText('缓存')
  await expect(page.getByTestId('scientific-result').locator('canvas').first()).toBeVisible()
})
