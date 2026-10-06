// P6 real three-entry CFD/DeepSeek/report acceptance, using the project's browser harness.
import { chromium, expect } from '../../frontend/node_modules/@playwright/test/index.mjs'
import { spawn, spawnSync } from 'node:child_process'
import { createWriteStream, writeFileSync, readFileSync, readdirSync, existsSync, mkdirSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../..', import.meta.url))
const out = path.join(root, 'docs/v2')
const base = 'http://127.0.0.1:4437'
const api = 'http://127.0.0.1:5127'
const offlineApi = 'http://127.0.0.1:5128'
const offlineBase = 'http://127.0.0.1:4438'
let activeApi = api
const log = createWriteStream(path.join(out, 'p6_live_server.log'))
const servers = []
let browser
const report = { status:'RUNNING', started_at:new Date().toISOString(), scenarios:[], checks:{} }
const persist = () => writeFileSync(path.join(out,'p6_live_acceptance.json'), JSON.stringify(report,null,2)+'\n')
const hash = data => createHash('sha256').update(data).digest('hex')
const dataOf = html => JSON.parse(html.match(/<script type="application\/json" id="report-data">([\s\S]*?)<\/script>/)[1])
const providerCalls = () => {
  const dir = path.join(root,'runtime/ai/calls')
  return existsSync(dir) ? readdirSync(dir).filter(p=>p.endsWith('.json')).length : 0
}
function launch(cmd,args,cwd,env) {
  const child=spawn(cmd,args,{cwd,env:{...process.env,...env},windowsHide:true})
  child.stdout.pipe(log,{end:false});child.stderr.pipe(log,{end:false});servers.push(child)
}
async function ready(url) {
  for(let i=0;i<200;i++) {
    try { if((await fetch(url)).ok)return } catch {}
    await new Promise(resolve=>setTimeout(resolve,100))
  }
  throw Error('Server readiness timeout')
}
async function json(request,method,url,expected=200) {
  const response=await request[method](activeApi+url,{timeout:120000})
  const payload=await response.json()
  expect(response.status(),JSON.stringify(payload)).toBe(expected)
  return payload.data
}
try {
  persist()
  launch('pwsh',['-NoProfile','-File',path.join(root,'scripts/serve_backend.ps1')],root,
    {API_PORT:'5127',DEEPSEEK_TIMEOUT_SECONDS:'60'})
  await ready(api+'/api/v2/cases')
  const cases=await (await fetch(api+'/api/v2/cases')).json()
  expect(cases.data.natural_language_available).toBeTruthy()
  launch(path.join(root,'.venv/Scripts/python.exe'),['-B','-m','scripts.serve_backend'],root,
    {API_PORT:'5128',DEEPSEEK_API_KEY:''})
  await ready(offlineApi+'/api/v2/cases')
  expect((await (await fetch(offlineApi+'/api/v2/cases')).json()).data.natural_language_available).toBe(false)
  launch('pwsh',['-NoProfile','-Command','& npm.cmd run preview -- --port 4437 --strictPort'],path.join(root,'frontend'),{API_PROXY_TARGET:api})
  await ready(base)
  launch('pwsh',['-NoProfile','-Command','& npm.cmd run preview -- --port 4438 --strictPort'],path.join(root,'frontend'),{API_PROXY_TARGET:offlineApi})
  await ready(offlineBase)
  browser=await chromium.launch()
  const context=await browser.newContext({baseURL:base,viewport:{width:1365,height:900},acceptDownloads:true})
  const page=await context.newPage()
  const pageErrors=[]
  page.on('pageerror',e=>pageErrors.push(e.message))
  for(const mode of ['template','form','natural_language']) {
    activeApi=mode==='template' ? offlineApi : api
    // Template executes end-to-end against an actually keyless backend.
    // Other modes delay automatic AI solely to verify a cache-free report.
    if(mode!=='template')await page.route('**/api/v2/ai/runs/*/interpret',route=>route.abort())
    await page.goto((mode==='template' ? offlineBase : base)+'/experiments/new')
    await expect(page.getByTestId('execution-ready')).toBeVisible()
    if(mode==='natural_language') {
      await page.getByRole('button',{name:'自然语言',exact:true}).click()
      await page.getByLabel('实验要求',{exact:true}).fill('请使用 Case 8 fast D_u 普通模板，网格 64×16，CFL=0.05，T=0.04，q_aa=3.96，q_at=0.396；其他参数保持模板值。')
      await page.getByRole('button',{name:'生成配置草稿',exact:true}).click()
      await expect(page.getByTestId('natural-language-draft')).toBeVisible({timeout:120000})
    } else {
      if(mode==='form')await page.getByRole('button',{name:'专业参数',exact:true}).click()
      await page.getByLabel('起始模板',{exact:true}).selectOption('case8.fast.D_u')
      await page.getByRole('button',{name:'验证配置',exact:true}).click()
    }
    await expect(page.getByTestId('config-hash')).toBeVisible({timeout:20000})
    const configHash=await page.getByTestId('config-hash').textContent()
    await expect(page.getByRole('button',{name:'启动求解',exact:true})).toBeDisabled()
    await page.getByRole('checkbox').check()
    await page.getByRole('button',{name:'确认配置',exact:true}).click()
    await expect(page.getByTestId('config-confirmed')).toBeVisible()
    await page.getByRole('button',{name:'启动求解',exact:true}).click()
    await expect(page).toHaveURL(/\/runs\/[0-9a-f-]+$/,{timeout:20000})
    const runId=new URL(page.url()).pathname.split('/').at(-1)
    await expect(page.getByTestId('run-status')).toHaveText('已完成',{timeout:600000})
    if(mode==='template')await expect(page.getByTestId('ai-interpret-error')).toContainText('密钥',{timeout:30000})
    const result=await json(page.request,'get',`/api/v2/runs/${runId}/result`)
    expect(result.identity.config_hash).toBe(configHash)
    expect(result.identity.frozen).toBe(false)
    const runRoot=path.join(root,'runtime/runs',runId)
    const provenanceBefore=hash(readFileSync(path.join(runRoot,'provenance.json')))
    const callsBefore=providerCalls()
    const offline=await json(page.request,'post',`/api/v2/reports/${runId}`)
    expect(offline.ai_status).toBe('UNAVAILABLE')
    const offlineHtml=await (await page.request.get(`${activeApi}/api/v2/reports/${runId}/html`)).text()
    expect(offlineHtml.match(/<section id=/g)).toHaveLength(12)
    expect(offlineHtml.match(/<svg /g)).toHaveLength(4)
    expect(providerCalls()).toBe(callsBefore)
    await page.unroute('**/api/v2/ai/runs/*/interpret')
    activeApi=api
    await page.goto(base+'/runs/'+runId)
    await expect(page.getByTestId('ai-cache-status')).toBeVisible({timeout:120000})
    // The actual assistant uses the current final density snapshot.
    await page.getByLabel('科研问题',{exact:true}).fill('请解释当前密度统计与熵通道预算的含义，并说明本次结论的局限。')
    let chatResponse=page.waitForResponse(response=>response.url().endsWith('/api/v2/ai/chat'),{timeout:120000})
    await page.getByRole('button',{name:'提问',exact:true}).click()
    let chat=await chatResponse
    let chatRetries=0
    if(chat.status()===502 || chat.status()===503) {
      await expect(page.getByTestId('ai-chat-error')).toBeVisible()
      chatResponse=page.waitForResponse(response=>response.url().endsWith('/api/v2/ai/chat'),{timeout:120000})
      await page.getByRole('button',{name:'重试问答',exact:true}).click()
      chat=await chatResponse;chatRetries++
    }
    const answer=await chat.json()
    expect(chat.status(),JSON.stringify(answer)).toBe(200)
    expect(answer.data.result_hash).toBe(result.result_hash)
    expect(answer.data.current_view.run_id).toBe(runId)
    await expect(page.getByText(/^回答绑定 t=/)).toBeVisible({timeout:20000})
    await page.getByTestId('run-report-link').click()
    await expect(page.getByText('结果、解读或报告版本已变化，请更新报告。')).toBeVisible({timeout:30000})
    await page.getByRole('button',{name:'更新报告',exact:true}).click()
    await expect(page.getByTestId('report-ready')).toBeVisible({timeout:30000})
    await expect(page.getByTestId('report-ai')).toContainText('已纳入')
    const receipt=await json(page.request,'get',`/api/v2/reports/${runId}`)
    expect(receipt.ai_status).toBe('AVAILABLE')
    const frame=page.frameLocator('[data-testid="report-preview"]')
    await expect(frame.locator('h1')).toHaveText('ShockPath 数值实验报告')
    await expect(frame.locator('section')).toHaveCount(12)
    const downloadPromise=page.waitForEvent('download')
    await page.getByRole('button',{name:'保存 HTML',exact:true}).click()
    const download=await downloadPromise
    mkdirSync(path.join(root,'output/reports'),{recursive:true})
    const saved=path.join(root,'output/reports',`p6-${mode}.html`)
    await download.saveAs(saved)
    const bytes=readFileSync(saved)
    expect(hash(bytes)).toBe(receipt.html_sha256)
    const data=dataOf(bytes.toString('utf8'))
    expect(data.submission.input_mode).toBe(mode)
    expect(data.config).toEqual(result.config)
    expect(data.runtime).toEqual(result.runtime)
    expect(data.metrics).toEqual(result.metrics)
    expect(data.entropy).toEqual(result.entropy)
    expect(data.ai.result_hash).toBe(result.result_hash)
    expect(data.ai_context.result_hash).toBe(result.result_hash)
    expect(data.charts.every(f=>f.snapshot_id===result.snapshots.at(-1).snapshot_id)).toBeTruthy()
    const afterGeneration=providerCalls()
    await json(page.request,'post',`/api/v2/reports/${runId}`)
    expect(providerCalls()).toBe(afterGeneration)
    expect(hash(readFileSync(path.join(runRoot,'provenance.json')))).toBe(provenanceBefore)
    // Reopen the actual downloaded artifact, with every HTTP request blocked.
    const local=await context.newPage()
    const remote=[]
    await local.route(/^https?:\/\//,route=>{remote.push(route.request().url());return route.abort()})
    await local.goto(pathToFileURL(saved).href)
    await expect(local.locator('section')).toHaveCount(12)
    await expect(local.locator('svg')).toHaveCount(4)
    expect(remote).toEqual([])
    await local.setViewportSize({width:390,height:844})
    expect(await local.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
    await local.screenshot({path:path.join(root,'output/playwright',`p6-${mode}-offline-mobile.png`),fullPage:true})
    await local.close()
    if(mode==='template') {
      await page.screenshot({path:path.join(root,'output/playwright/p6-report-desktop.png'),fullPage:true})
      await page.setViewportSize({width:390,height:844})
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
      await page.screenshot({path:path.join(root,'output/playwright/p6-report-mobile.png'),fullPage:true})
      await page.setViewportSize({width:1365,height:900})
    }
    report.scenarios.push({status:'PASS',mode,run_id:runId,config_hash:configHash,result_hash:result.result_hash,
      accepted_steps:result.runtime.accepted_steps,final_time:result.runtime.final_time,
      deterministic_report_without_ai:true,real_interpretation_and_chat:true,chat_retries:chatRetries,
      keyless_backend_cfd_and_report:mode==='template',
      assistant:answer.data,receipt,
      offline_resource_requests:remote,provenance_unchanged:true,report_refresh_provider_calls:0,
      saved_html:path.relative(root,saved).replaceAll('\\','/')})
    persist();process.stdout.write(JSON.stringify({mode,run_id:runId,status:'PASS'})+'\n')
  }
  expect(new Set(report.scenarios.map(s=>s.run_id)).size).toBe(3)
  expect(new Set(report.scenarios.map(s=>s.config_hash)).size).toBe(1)
  await page.goto(base+'/runs/00000000-0000-4000-8000-000000000000/report')
  await expect(page.getByTestId('report-error')).toContainText('运行记录不存在')
  expect(pageErrors).toEqual([])
  report.checks={same_normalized_config:true,independent_runs:3,unknown_run:404,page_errors:pageErrors,offline_mobile_no_overflow:true}
  report.status='PASS';report.finished_at=new Date().toISOString();persist()
} catch(error) {
  report.status='FAIL';report.error=String(error);persist();throw error
} finally {
  await browser?.close()
  for(const child of servers.reverse()) {
    if(child.exitCode===null)spawnSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'})
  }
  log.end()
}
