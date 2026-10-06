<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ScientificRunView from '../views/runs/ScientificRunView.vue'
import { cancelRun, loadRun, loadRunHistory, statusLabels, terminal, type RunRecord } from '../data/v2/runs'
const route = useRoute()
const run = ref<RunRecord | null>(null)
const history = ref<Record<string, number>[]>([])
const error = ref('')
const connection = ref('正在连接事件服务')
const cancelling = ref(false)
let events: EventSource | undefined
let timer: ReturnType<typeof setInterval> | undefined
let generation = 0
const progress = computed(() => run.value ? Math.min(100, 100 * run.value.physical_time / run.value.requested_final_time) : 0)
const failureLabels: Record<string, string> = {
  WORKER_INTERRUPTED: '服务中断，计算未续算。可用同一配置创建新运行。', WORKER_TIMEOUT: '计算超过运行时长上限。',
  RUN_OUTPUT_LIMIT: '输出超过容量上限。', WORKER_EXIT: '求解进程异常退出。', WORKER_FAILED: '求解或结果校验失败。',
}
function stop() { events?.close(); events = undefined; clearInterval(timer); timer = undefined }
async function refresh(id: string, current: number) {
  try {
    const record = await loadRun(id)
    if (current !== generation) return
    if (!run.value || record.last_event_id >= run.value.last_event_id) run.value = record
    error.value = ''
    const first = await loadRunHistory(id)
    const recent = first.total > 5 ? await loadRunHistory(id, first.total - 5) : first
    if (current !== generation) return
    history.value = recent.rows
    if (terminal(record.status)) {
      stop(); connection.value = '运行记录已保存'
    }
  } catch (e) { if (current === generation) error.value = e instanceof Error ? e.message : '连接失败，请重试。' }
}
function start() {
  stop(); const current = ++generation
  const id = String(route.params.runId)
  run.value = null; history.value = []; error.value = ''; cancelling.value = false
  refresh(id, current)
  timer = setInterval(() => refresh(id, current), 4000)
  events = new EventSource('/api/v2/runs/' + encodeURIComponent(id) + '/events')
  events.onopen = () => { if (current === generation) connection.value = '实时事件已连接' }
  events.onerror = () => { if (current === generation) connection.value = '事件连接中断，正在通过状态查询刷新' }
  events.addEventListener('run', event => {
    if (current !== generation) return
    const record = JSON.parse((event as MessageEvent).data) as RunRecord
    if (record.run_id === id && (!run.value || record.last_event_id >= run.value.last_event_id)) {
      run.value = record
      if (terminal(record.status)) refresh(id, current)
    }
  })
}
async function cancel() {
  if (!run.value || cancelling.value) return
  const current = generation
  const id = run.value.run_id
  cancelling.value = true
  try { const record = await cancelRun(id); if (current === generation) run.value = record }
  catch (e) { if (current === generation) error.value = e instanceof Error ? e.message : '取消失败，请重试。' }
  finally { if (current === generation) cancelling.value = false }
}
watch(() => route.params.runId, start, { immediate: true })
onUnmounted(() => { generation++; stop() })
</script>

<template>
  <main class="workspace" data-page="run-workspace">
    <RouterLink to="/workspace">← 实验工作台</RouterLink><h1>Case 8 运行</h1>
    <p v-if="error" role="alert" data-testid="run-error">{{ error }} <button @click="start">重新连接</button></p>
    <p v-if="!run && !error" role="status">正在加载运行记录…</p>
    <template v-if="run">
      <header class="panel"><strong data-testid="run-status">{{ statusLabels[run.status] }}</strong><p class="identity">{{ run.run_id }}</p>
        <p>{{ connection }}</p><p v-if="run.status === 'QUEUED'">等待前面的任务结束后开始求解。</p>
        <p v-if="run.cancel_requested && !terminal(run.status)" role="status">已请求取消，正在停止实际计算…</p>
        <button v-if="!terminal(run.status)" :disabled="cancelling || run.cancel_requested" @click="cancel">取消运行</button>
        <p v-if="run.status === 'FAILED'">{{ failureLabels[run.failure ?? ''] ?? '运行失败，结果不可用。' }}</p>
        <p v-if="run.status === 'CANCELLED'">运行已取消。已计算的局部输出不会作为完成结果展示。</p>
        <p v-if="run.status === 'POSTPROCESSING'">求解已结束，正在校验并保存结果。</p>
        <div v-if="run.planned_steps"><progress :value="progress" max="100" aria-label="求解进度"></progress>
          <p data-testid="real-progress">{{ run.completed_steps }} / {{ run.planned_steps }} 步 · t={{ run.physical_time.toPrecision(6) }} / {{ run.requested_final_time }} · {{ progress.toFixed(1) }}%</p></div>
      </header>
      <section class="panel"><h2>本次配置</h2>
        <p>{{ run.experiment.normalized_config.grid.nx }} × {{ run.experiment.normalized_config.grid.ny }} · CFL={{ run.experiment.normalized_config.time.cfl }} · T={{ run.requested_final_time }}</p>
        <p>q_aa={{ run.experiment.normalized_config.method.q_aa }} · q_at={{ run.experiment.normalized_config.method.q_at }} · Mach=6 · 一阶 · SSP-RK3</p>
        <p class="hash">配置 SHA-256：{{ run.experiment.config_hash }}</p>
        <p>来源：本次新建的 V2 计算。论文配置匹配与科学复现结论分别核查。</p>
        <p v-if="run.finished_at">结束时间：{{ new Date(run.finished_at).toLocaleString() }}</p>
      </section>
      <section class="panel"><h2>真实进度日志</h2><pre data-testid="run-log">{{ run.log_tail.join('\n') || '等待求解器输出…' }}</pre></section>
      <section v-if="history.length" class="panel"><h2>最近的熵累计记录</h2>
        <div class="table-wrap"><table><thead><tr><th>时间（model time）</th><th>E_bg</th><th>E_aa</th><th>E_at</th></tr></thead>
          <tbody><tr v-for="(row, index) in history" :key="index"><td>{{ row.time_end?.toPrecision(5) }}</td>
            <td>{{ row.E_bg?.toPrecision(5) }}</td><td>{{ row.E_aa?.toPrecision(5) }}</td><td>{{ row.E_at?.toPrecision(5) }}</td></tr></tbody></table></div>
        <p class="hint">来自本次运行的逐步诊断，包含 SSP-RK3 时间权重；仅展示最近 5 条记录。</p>
      </section>
      <ScientificRunView v-if="run.status === 'COMPLETED'" :run-id="run.run_id" />
      <section v-if="run.status === 'COMPLETED'" class="panel"><h2>实验报告</h2>
        <p>将本次配置、真实科学结果、已验证解读与来源保存为可离线打开的 HTML。</p>
        <RouterLink :to="`/runs/${run.run_id}/report`" data-testid="run-report-link">生成 / 查看实验报告 →</RouterLink>
      </section>
    </template>
  </main>
</template>

<style scoped>
.workspace { max-width: 1100px; margin: auto; padding: 2.5rem 1.5rem; color: #24384c; }a { color: #214f75; }
.panel { padding: 1.5rem; border: 1px solid #dce4eb; border-radius: 8px; margin: 1rem 0; min-width: 0; }h2 { font-size: 1.1rem; }p { line-height: 1.7; }
strong { font-size: 1.2rem; color: #214f75; }.identity,.hash { overflow-wrap: anywhere; font-size: .8rem; }.hint { color: #617184; font-size: .85rem; }
button { font: inherit; border: 1px solid #bdccda; border-radius: 5px; background: white; color: #254b6c; padding: .55rem .9rem; }button:disabled { opacity: .5; }
progress { width: 100%; accent-color: #214f75; }pre { overflow: auto; background: #f4f7fa; padding: 1rem; font-size: .8rem; }.table-wrap { overflow-x: auto; }table { width: 100%; text-align: left; border-collapse: collapse; }th,td { padding: .5rem; border-bottom: 1px solid #dce4eb; font-size: .85rem; }
@media(max-width:780px) { .workspace { padding: 1.5rem 1rem; }.panel { padding: 1rem; } }
</style>
