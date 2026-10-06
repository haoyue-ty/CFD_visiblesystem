// Real P7 browser/API acceptance; no mocks or provider credentials.
import { chromium, expect } from '../../frontend/node_modules/@playwright/test/index.mjs'
import { spawn, spawnSync } from 'node:child_process'
import { createWriteStream, readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

const root = fileURLToPath(new URL('../..', import.meta.url))
const out = path.join(root, 'docs/v2'), api = 'http://127.0.0.1:5129', base = 'http://127.0.0.1:4439'
const servers = [], log = createWriteStream(path.join(out, 'p7_live_server.log'))
const receipt = { status: 'RUNNING', started_at: new Date().toISOString(), checks: {} }
const persist = () => writeFileSync(path.join(out,'p7_live_acceptance.json'), JSON.stringify(receipt,null,2)+'\n')
const pause = ms => new Promise(resolve => setTimeout(resolve,ms))
let browser
function launch(cmd,args,cwd,env) {
  const child=spawn(cmd,args,{cwd,env:{...process.env,...env},windowsHide:true})
  child.stdout.pipe(log,{end:false}); child.stderr.pipe(log,{end:false}); servers.push(child)
}
async function ready(url) {
  for (let i=0;i<200;i++) { try { if ((await fetch(url)).ok) return } catch {} await pause(100) }
  throw Error('Server readiness timeout')
}
async function http(url,body,expected=200) {
  const response = await fetch(api+url,body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {})
  const payload=await response.json(); expect(response.status,JSON.stringify(payload)).toBe(expected); return payload.data
}
async function waitSweep(id,expected='COMPLETED') {
  const deadline=Date.now()+360000
  while(Date.now()<deadline) {
    const s=await http('/api/v2/sweeps/'+id)
    if (['COMPLETED','FAILED','CANCELLED'].includes(s.status)) { expect(s.status,JSON.stringify(s)).toBe(expected); return s }
    await pause(500)
  }
  throw Error('Sweep deadline exceeded')
}
function pass(name,data) { receipt.checks[name]={status:'PASS',...data}; persist(); console.log(JSON.stringify({check:name,status:'PASS'})) }
try {
  persist()
  launch(path.join(root,'.venv/Scripts/python.exe'),['-B','-m','scripts.serve_backend'],root,{API_PORT:'5129',DEEPSEEK_API_KEY:''})
  await ready(api+'/api/v2/cases')
  const registry=await http('/api/v2/cases')
  expect(registry.natural_language_available).toBe(false)
  launch('pwsh',['-NoProfile','-Command','& npm.cmd run preview -- --port 4439 --strictPort'],path.join(root,'frontend'),{API_PROXY_TARGET:api})
  await ready(base)
  browser=await chromium.launch()
  const context=await browser.newContext({viewport:{width:1365,height:900}})
  const page=await context.newPage(), errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  const p6=JSON.parse(readFileSync(path.join(out,'p6_live_acceptance.json'),'utf8'))
  const baseRun=p6.scenarios[0].run_id
  await page.goto(base+'/workspace')
  await page.getByRole('link',{name:'系数扫描',exact:true}).click()
  await page.getByLabel('基础 Run ID').fill(baseRun)
  await page.getByLabel('总时间预算',{exact:true}).fill('300')
  await page.getByRole('button',{name:'验证扫描配置'}).click()
  await expect(page.getByRole('heading',{name:'确认 4 项扫描'})).toBeVisible({timeout:30000})
  const before=await http('/api/v2/runs?limit=1')
  await page.getByRole('button',{name:'确认并启动扫描'}).click()
  await page.waitForURL('**/sweeps/*')
  const id=new URL(page.url()).pathname.split('/').at(-1)
  let scan=await http('/api/v2/sweeps/'+id)
  expect(scan.items.filter(i=>i.run).length).toBeLessThanOrEqual(1)
  scan=await waitSweep(id)
  expect(scan.successful_tasks).toBe(4)
  expect(new Set(scan.items.map(i=>i.run.run_id)).size).toBe(4)
  const records=scan.items.map(i=>i.run)
  for(let i=1;i<records.length;i++) expect(Date.parse(records[i].started_at)).toBeGreaterThanOrEqual(Date.parse(records[i-1].finished_at))
  const results=[]
  for(const item of scan.items) {
    const r=await http('/api/v2/runs/'+item.run.run_id+'/result')
    expect(r.config.normalized_config.method.q_aa).toBe(item.q_aa)
    expect(r.config.normalized_config.method.q_at).toBe(item.q_at)
    expect(r.identity.config_hash).toBe(item.config_hash)
    expect(r.snapshots.length).toBe(6)
    if(item.q_at===0) expect(r.entropy.totals.E_at).toBe(0)
    results.push({run_id:item.run.run_id,result_hash:r.result_hash,config_hash:item.config_hash,
      accepted_steps:r.runtime.accepted_steps,solver_seconds:r.runtime.solver_seconds,entropy:r.entropy.totals,metrics:r.metrics})
  }
  await expect(page.getByTestId('sweep-status')).toHaveText('全部完成',{timeout:15000})
  pass('real_four_combination_serial_scan',{sweep_id:id,base_run:baseRun,sweep_hash:scan.sweep_hash,results,records})
  await page.screenshot({path:path.join(out,'p7_scan_desktop.png'),fullPage:true})
  await page.getByRole('link',{name:'对比前两个成功运行'}).click()
  await expect(page.getByTestId('comparison-conditions')).toHaveText('同条件比较',{timeout:30000})
  const pair={run_a:records[0].run_id,run_b:records[1].run_id,field:'density'}
  let comparison=await http('/api/v2/comparisons',pair)
  expect(comparison.same_conditions).toBe(true)
  expect(comparison.common_snapshot_times.length).toBe(6)
  expect(comparison.field_a.time).toBe(comparison.field_b.time)
  expect(comparison.color_min).toBe(Math.min(comparison.field_a.minimum,comparison.field_b.minimum))
  expect(comparison.color_max).toBe(Math.max(comparison.field_a.maximum,comparison.field_b.maximum))
  for(const m of comparison.metrics) if(m.comparable) expect(m.b_minus_a).toBe(m.b-m.a)
  await page.getByLabel('对比变量').selectOption('mach')
  await expect(page.getByLabel('对比变量')).toBeEnabled({timeout:30000})
  await page.getByLabel('共同快照时间').selectOption('0')
  await expect(page.getByTestId('comparison-color')).toHaveText(/· t=0$/,{timeout:30000})
  comparison=await http('/api/v2/comparisons',{...pair,field:'mach',snapshot_time:0})
  expect(comparison.field_a.field_id).toBe('mach')
  expect(comparison.field_a.time).toBe(0)
  pass('same_conditions_time_color_metrics',{run_a:pair.run_a,run_b:pair.run_b,common_snapshot_times:comparison.common_snapshot_times,
    differences:comparison.differences,initial_mach_color:[comparison.color_min,comparison.color_max],metrics:comparison.metrics})
  await page.screenshot({path:path.join(out,'p7_compare_desktop.png'),fullPage:true})
  await page.setViewportSize({width:390,height:844})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({path:path.join(out,'p7_compare_mobile.png'),fullPage:true})
  const p4=JSON.parse(readFileSync(path.join(out,'p4_live_acceptance.json'),'utf8'))
  const other=p4.checks.custom_128x32_qat_zero.run_id
  await page.getByLabel('Run B',{exact:true}).fill(other)
  await page.getByRole('button',{name:'核查并对比'}).click()
  await expect(page.getByTestId('comparison-conditions')).toHaveText('非同条件比较',{timeout:30000})
  const mismatch=await http('/api/v2/comparisons',{...pair,run_b:other})
  expect(mismatch.same_conditions).toBe(false)
  expect(mismatch.differences.some(d=>d.field==='grid.nx' && d.affects_conditions)).toBe(true)
  expect(mismatch.metrics.every(m=>m.b_minus_a===null)).toBe(true)
  pass('non_matching_grid_no_ranking',{run_b:other,differences:mismatch.differences,metrics:mismatch.metrics})
  await http('/api/v2/comparisons',{...pair,snapshot_time:.000001},409)
  const template=registry.cases[0].templates[0]
  const input={config:template.config,submission:{input_mode:'template',template_id:template.template_id,
    capability_revision:registry.cases[0].capability_revision},q_aa_values:[3.96,13.2],q_at_values:[0.,.396],max_tasks:4,time_budget_seconds:300.}
  async function create(body) {
    const p=await http('/api/v2/sweeps/preview',body)
    return http('/api/v2/sweeps',{...body,confirmed_sweep_hash:p.sweep_hash,idempotency_key:randomUUID()},202)
  }
  const cancelling=await create(input)
  const deadline=Date.now()+60000
  let child
  while(Date.now()<deadline) {
    const s=await http('/api/v2/sweeps/'+cancelling.sweep_id)
    child=s.items[0].run
    if(child?.status==='RUNNING' && child.completed_steps > 0) break
    await pause(200)
  }
  expect(child?.completed_steps).toBeGreaterThan(0)
  await page.goto(base+'/sweeps/'+cancelling.sweep_id)
  await page.getByRole('button',{name:'取消扫描',exact:true}).click()
  const cancelled=await waitSweep(cancelling.sweep_id,'CANCELLED')
  expect(cancelled.items[0].status).toBe('CANCELLED')
  expect(cancelled.items.slice(1).every(i=>i.status==='SKIPPED' && i.run===null)).toBe(true)
  pass('cancel_real_active_worker',{record:cancelled,completed_steps_before_cancel:child.completed_steps})
  const timed=await create({...input,time_budget_seconds:1.})
  const exhausted=await waitSweep(timed.sweep_id,'FAILED')
  expect(exhausted.failure).toBe('SWEEP_TIME_BUDGET_EXCEEDED')
  expect(exhausted.items.every(i=>['CANCELLED','SKIPPED'].includes(i.status))).toBe(true)
  pass('real_time_budget',{record:exhausted})
  await page.goto(base+'/workspace/sweeps')
  await expect(page.getByRole('heading',{name:'系数扫描',exact:true})).toBeVisible()
  await page.getByLabel('基础 Run ID').fill(baseRun)
  await page.getByLabel('q_aa 扫描值').fill('5')
  await page.getByRole('button',{name:'验证扫描配置'}).click()
  await expect(page.getByRole('alert')).toContainText('未支持',{timeout:30000})
  await expect(page.getByRole('button',{name:'确认并启动扫描'})).toHaveCount(0)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  expect(errors).toEqual([])
  pass('browser_navigation_mobile_unsupported',{page_errors:errors,mobile_width:390,provider_disabled:true,runs_before:before.total})
  receipt.status='PASS'; receipt.finished_at=new Date().toISOString(); persist()
} catch(error) {
  receipt.status='FAIL'; receipt.error=String(error.stack ?? error); persist(); throw error
} finally {
  if(browser) await browser.close()
  for(const server of servers.reverse()) {
    if(server.exitCode===null) spawnSync('taskkill',['/PID',String(server.pid),'/T','/F'],{windowsHide:true})
  }
  log.end()
}
