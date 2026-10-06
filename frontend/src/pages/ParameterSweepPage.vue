<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loadRuns, loadRun, statusLabels, type RunRecord } from '../data/v2/runs'
import { previewSweep, createSweep, loadSweep, loadSweeps, cancelSweep, type Sweep, type SweepInput, type Preview } from '../data/v2/comparison'
const route = useRoute(), router = useRouter()
const runs = ref<RunRecord[]>([]), base = ref(''), aa = ref('3.96, 13.2'), at = ref('0, 0.396'), tasks = ref(4), seconds = ref(300)
const preview = ref<Preview>(), draft = ref<SweepInput>(), sweep = ref<Sweep>(), sweeps = ref<Sweep[]>([]), error = ref(''), busy = ref(false)
const offset = ref(0), total = ref(0), runOffset = ref(0), runTotal = ref(0)
const terminal = computed(() => sweep.value && ['COMPLETED', 'FAILED', 'CANCELLED'].includes(sweep.value.status))
const labels: Record<string,string> = { QUEUED: '排队中', RUNNING: '扫描中', CANCELLING: '正在取消', COMPLETED: '全部完成', FAILED: '扫描失败', CANCELLED: '已取消' }
const completed = computed(() => sweep.value?.items.filter(i => i.status === 'COMPLETED' && i.run) ?? [])
let timer: ReturnType<typeof setInterval> | undefined
let key = crypto.randomUUID(), active = true, generation = 0
watch([base, aa, at, tasks, seconds], () => { generation++; preview.value = undefined; draft.value = undefined; key = crypto.randomUUID() })
function values(raw: string) {
  const parts = raw.split(/[,，]/).map(v => v.trim())
  if (parts.some(v => !v || !Number.isFinite(Number(v)))) throw new Error('系数须为逗号分隔的有限数值。')
  return parts.map(Number)
}
async function moreRuns() {
  try { const result = await loadRuns(runOffset.value); runs.value.push(...result.runs); runOffset.value += result.runs.length; runTotal.value = result.total }
  catch(e) { error.value = e instanceof Error ? e.message : '加载失败' }
}
async function buildPreview() {
  busy.value = true; error.value = ''; preview.value = undefined; draft.value = undefined
  const current = ++generation
  try {
    const inputValues = { q_aa_values: values(aa.value), q_at_values: values(at.value), max_tasks: tasks.value, time_budget_seconds: seconds.value }
    const record = await loadRun(base.value)
    const input: SweepInput = { config: { ...record.experiment.normalized_config, profile: 'custom' } as SweepInput['config'],
      submission: { input_mode: 'form', template_id: null,
        natural_language_text: null, parser_version: null,
        capability_revision: record.experiment.capability_revision }, ...inputValues }
    const result = await previewSweep(input)
    if (current !== generation || !active) return
    draft.value = input; preview.value = result
  } catch (e) { if (current === generation && active) error.value = e instanceof Error ? e.message : '预览失败' }
  finally { if (active) busy.value = false }
}
async function submit() {
  if (!draft.value || !preview.value) return
  busy.value = true; error.value = ''
  try { const result = await createSweep(draft.value, preview.value.sweep_hash, key); preview.value = undefined; draft.value = undefined; await router.push('/sweeps/'+result.sweep_id); await refresh() }
  catch (e) { error.value = e instanceof Error ? e.message : '提交失败' }
  finally { busy.value = false }
}
async function refresh() {
  try {
    const id = String(route.params.sweepId ?? '')
    if (id) { const result = await loadSweep(id); if (active && id === String(route.params.sweepId)) sweep.value = result }
    const list = await loadSweeps(offset.value)
    if (active) { sweeps.value = list.sweeps; total.value = list.total; error.value = '' }
  } catch (e) { if (active) error.value = e instanceof Error ? e.message : '加载失败' }
}
async function cancel() {
  if (!sweep.value) return
  busy.value = true
  try { sweep.value = await cancelSweep(sweep.value.sweep_id) }
  catch (e) { error.value = e instanceof Error ? e.message : '取消失败' }
  finally { busy.value = false }
}
watch(() => route.params.sweepId, () => { sweep.value = undefined; refresh() })
watch(offset, refresh)
onMounted(async () => { await Promise.all([moreRuns(), refresh()]); timer = setInterval(refresh, 2000) })
onUnmounted(() => { active = false; generation++; clearInterval(timer) })
</script>
<template>
  <main class="p7" data-page="parameter-sweep"><p class="eyebrow">SHOCKPATH · PARAMETER SWEEP</p><h1>系数扫描</h1>
    <p>基于已验证配置，仅改变 q_aa / q_at。当前登记 q_aa=3.96/13.2、q_at=0/0.396，最多四个组合，复用单 worker 串行计算。</p>
    <RouterLink to="/workspace">返回工作台</RouterLink>
    <form @submit.prevent="buildPreview"><label>基础 Run ID <input v-model="base" list="base-runs" required aria-label="基础 Run ID" /></label>
      <datalist id="base-runs"><option v-for="run in runs" :key="run.run_id" :value="run.run_id">{{ run.experiment.normalized_config.grid.nx }}×{{ run.experiment.normalized_config.grid.ny }} T={{ run.requested_final_time }}</option></datalist>
      <label>q_aa 值 <input v-model="aa" required aria-label="q_aa 扫描值" /></label><label>q_at 值 <input v-model="at" required aria-label="q_at 扫描值" /></label>
      <label>总任务预算 <input type="number" v-model.number="tasks" min="1" max="9" step="1" required aria-label="总任务预算" /></label>
      <label>总时间预算 / 秒 <input type="number" v-model.number="seconds" min="1" max="1800" required aria-label="总时间预算" /></label>
      <button :disabled="busy">验证扫描配置</button><button v-if="runOffset < runTotal" type="button" @click="moreRuns">加载更多基础运行</button></form>
    <p>时间预算从提交起计算，包含排队和后处理；耗尽时停止子运行，跳过未提交项。epsilon 与其他 Case 当前未开放。</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <section v-if="preview"><h2>确认 {{ preview.total_tasks }} 项扫描</h2>
      <p v-if="draft">Case 8 · {{ draft.config.grid.nx }}×{{ draft.config.grid.ny }} · T={{ draft.config.time.final_time }} · CFL={{ draft.config.time.cfl }} · {{ draft.config.discretization?.reconstruction }} · {{ draft.config.time.integrator }}</p>
      <p>预算 {{ preview.max_tasks }} 项 / {{ preview.time_budget_seconds }} 秒 · hash {{ preview.sweep_hash }}</p>
      <div class="table"><table><thead><tr><th>q_aa</th><th>q_at</th><th>分类</th><th>配置 hash</th></tr></thead><tbody><tr v-for="e in preview.experiments" :key="e.config_hash">
        <td>{{ e.normalized_config.method.q_aa }}</td><td>{{ e.normalized_config.method.q_at }}</td><td>{{ e.classification }}</td><td>{{ e.config_hash }}</td></tr></tbody></table></div>
      <p v-for="note in preview.warnings" :key="note" class="hint">{{ note }}</p><button :disabled="busy" @click="submit">确认并启动扫描</button></section>
    <section v-if="sweep"><h2 data-testid="sweep-status">{{ labels[sweep.status] }}</h2><p>{{ sweep.sweep_id }}</p>
      <p data-testid="sweep-progress">已处理 {{ sweep.settled_tasks }} / {{ sweep.total_tasks }} · 成功 {{ sweep.successful_tasks }} · 已用 {{ sweep.elapsed_seconds.toFixed(1) }} / {{ sweep.time_budget_seconds }} 秒</p>
      <p v-if="sweep.failure" role="alert">{{ sweep.failure === 'SWEEP_TIME_BUDGET_EXCEEDED' ? '扫描时间预算已耗尽。' : '部分子运行未成功完成，请查看运行详情。' }}</p>
      <button v-if="!terminal" :disabled="busy || sweep.cancel_requested" @click="cancel">取消扫描</button>
      <div class="table"><table><thead><tr><th>序号</th><th>q_aa</th><th>q_at</th><th>状态 / 进度</th><th>运行结果</th></tr></thead><tbody><tr v-for="item in sweep.items" :key="item.index">
        <td>{{ item.index + 1 }}</td><td>{{ item.q_aa }}</td><td>{{ item.q_at }}</td><td>{{ item.status === 'PENDING' ? '待提交' : item.status === 'SKIPPED' ? '已跳过' : statusLabels[item.status] }} <span v-if="item.run">{{ item.run.completed_steps }} / {{ item.run.planned_steps ?? '?' }}</span></td>
        <td><RouterLink v-if="item.run" :to="'/runs/'+item.run.run_id">{{ item.run.run_id }}</RouterLink><span v-else>—</span></td></tr></tbody></table></div>
      <RouterLink v-if="completed.length >= 2" :to="{ path: '/workspace/compare', query: { a: completed[0]?.run?.run_id, b: completed[1]?.run?.run_id } }">对比前两个成功运行</RouterLink>
      <p v-for="note in sweep.warnings" :key="note" class="hint">{{ note }}</p></section>
    <section><h2>扫描记录</h2><ul><li v-for="s in sweeps" :key="s.sweep_id"><RouterLink :to="'/sweeps/'+s.sweep_id">{{ s.sweep_id }}</RouterLink> · {{ labels[s.status] }} · {{ s.successful_tasks }}/{{ s.total_tasks }}</li></ul>
      <div class="toolbar"><button :disabled="offset === 0" @click="offset -= 20">上一页</button><button :disabled="offset + 20 >= total" @click="offset += 20">下一页</button><button @click="refresh">刷新扫描</button></div></section>
  </main>
</template>
<style scoped src="../views/runs/p7.css"></style>
