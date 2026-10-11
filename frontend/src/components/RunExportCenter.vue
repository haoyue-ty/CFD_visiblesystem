<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { Database, Box, FileText, Download, LoaderCircle } from '@lucide/vue'
import { downloadExport, generateExport, loadExports, type ExportKind, type ExportStatus, type ReportFormat } from '../data/v2/exports'
import { ExperimentApiError } from '../data/v2/experiments'
import type { RunStatus } from '../data/v2/runs'

const props = defineProps<{ runId: string; runStatus: RunStatus }>()
const cards = [
  { kind: 'raw' as const, label: '原始数据包', icon: Database, detail: '原始状态、完整诊断与科学来源' },
  { kind: 'visualization' as const, label: '流场文件', icon: Box, detail: '真实时间序列，可在 ParaView 中打开' },
  { kind: 'report' as const, label: '实验报告', icon: FileText, detail: '实验配置、流场、熵预算与关键指标' },
]
const summary = ref<ExportStatus>()
const serviceError = ref(''), loading = ref(false)
const reportFormat = ref<ReportFormat>('zip')
const busy = ref<Partial<Record<ExportKind, 'GENERATING' | 'DOWNLOADING'>>>({})
const feedback = ref<Partial<Record<ExportKind, string>>>({})
const failures = ref<Partial<Record<ExportKind, string>>>({})
let session = 0, timer: ReturnType<typeof setTimeout> | undefined
let controller = new AbortController()
const completed = computed(() => props.runStatus === 'COMPLETED')
const reason = computed(() => !completed.value ? '本次运行尚未成功完成，完成并通过科学校验后可导出。' : summary.value?.reason)
const pdfReason = computed(() => summary.value?.capabilities.report?.unavailable_formats.PDF)

function schedule(current: number) {
  clearTimeout(timer)
  if (current !== session) return
  if (Object.values(busy.value).length || Object.values(summary.value?.exports ?? {}).some(e => e.status === 'GENERATING')) {
    timer = setTimeout(() => refresh(current), 1500)
  }
}
async function refresh(current = session) {
  if (!completed.value) return
  try {
    const value = await loadExports(props.runId, controller.signal)
    if (current !== session) return
    summary.value = value; serviceError.value = ''
    if (pdfReason.value && reportFormat.value === 'pdf') reportFormat.value = 'html'
  } catch (error) {
    if (current === session && !controller.signal.aborted) serviceError.value = error instanceof Error ? error.message : '导出服务不可用。'
  } finally {
    if (current === session) { loading.value = false; schedule(current) }
  }
}
function disabled(kind: ExportKind) {
  return !completed.value || loading.value || !!serviceError.value || !summary.value?.available || !!busy.value[kind] || summary.value.exports[kind]?.status === 'GENERATING'
}
function formats(kind: ExportKind) {
  const values = summary.value?.capabilities[kind]?.formats ?? []
  return values.length ? values.map(f => f === 'VTI' ? 'VTK (VTI)' : f).join(' / ') : '完成后可用'
}
function status(kind: ExportKind) {
  if (!completed.value) return '暂不可用'
  if (busy.value[kind] === 'DOWNLOADING') return '正在下载…'
  if (busy.value[kind] === 'GENERATING') return '正在生成…'
  if (failures.value[kind]) return '下载 / 导出失败 · 点击重试'
  if (feedback.value[kind]) return feedback.value[kind]
  const entry = summary.value?.exports[kind]
  return ({ NOT_GENERATED: '点击生成并下载', GENERATING: '正在生成…', READY: '已就绪 · 点击下载', FAILED: '导出失败 · 点击重试' })[entry?.status ?? 'NOT_GENERATED']
}
async function start(kind: ExportKind, chosenFormat?: ReportFormat) {
  if (disabled(kind)) return
  const current = session, id = props.runId, signal = controller.signal
  const format = kind === 'report' ? chosenFormat ?? reportFormat.value : 'zip'
  delete failures.value[kind]; delete feedback.value[kind]
  busy.value[kind] = 'GENERATING'; schedule(current)
  try {
    const entry = await generateExport(id, kind, format, signal)
    if (current !== session) return
    if (summary.value) summary.value.exports[kind] = entry
    busy.value[kind] = 'DOWNLOADING'
    await downloadExport(id, kind, format, signal)
    if (current === session) feedback.value[kind] = '已就绪 · 下载已开始'
  } catch (error) {
    if (current === session && !signal.aborted) {
      if (error instanceof ExperimentApiError && ['EXPORT_BUSY', 'EXPORT_SERVICE_BUSY'].includes(error.code ?? '')) {
        feedback.value[kind] = '导出服务繁忙，请稍后重试'
      } else failures.value[kind] = error instanceof Error ? error.message : '导出失败，请重试。'
    }
  } finally {
    if (current === session) { delete busy.value[kind]; await refresh(current) }
  }
}
watch(() => [props.runId, props.runStatus], () => {
  controller.abort(); controller = new AbortController(); clearTimeout(timer)
  const current = ++session
  summary.value = undefined; serviceError.value = ''; feedback.value = {}; failures.value = {}; busy.value = {}
  loading.value = completed.value
  refresh(current)
}, { immediate: true })
onUnmounted(() => { ++session; controller.abort(); clearTimeout(timer) })
</script>

<template>
  <section id="run-exports" class="export-center" aria-labelledby="export-heading" data-testid="run-export-center">
    <div class="export-heading"><div><h2 id="export-heading">实验结果 · 导出中心</h2><p>文件由本次 CFD 计算的真实结果生成。</p></div><span class="export-origin">本次运行</span></div>
    <p v-if="reason" class="availability" role="status">{{ reason }}</p>
    <p v-if="loading" role="status">正在核查导出能力…</p>
    <p v-if="serviceError" class="error" role="alert" data-testid="export-service-error">导出服务不可用：{{ serviceError }} <button @click="loading = true; refresh()">重新连接</button></p>
    <div class="export-grid">
      <article v-for="card in cards" :key="card.kind" class="export-card" :class="{ ready: summary?.exports[card.kind]?.status === 'READY', failed: !!failures[card.kind] }" :data-testid="`export-card-${card.kind}`">
        <button class="export-action" :disabled="disabled(card.kind)" :aria-label="`下载${card.label}`" :aria-busy="!!busy[card.kind]" @click="start(card.kind)">
          <component :is="card.icon" class="export-icon" :size="32" :stroke-width="1.6" aria-hidden="true" />
          <strong>{{ card.label }}</strong><span class="formats" :data-testid="`export-formats-${card.kind}`">{{ formats(card.kind) }}</span>
          <span class="detail">{{ card.detail }}</span>
          <span class="action-status" role="status" :data-testid="`export-status-${card.kind}`"><LoaderCircle v-if="busy[card.kind] || summary?.exports[card.kind]?.status === 'GENERATING'" class="spinner" :size="15" aria-hidden="true" /><Download v-else :size="15" aria-hidden="true" />{{ status(card.kind) }}</span>
        </button>
        <label v-if="card.kind === 'report'" class="format-choice">报告格式
          <select v-model="reportFormat" aria-label="报告下载格式" :disabled="disabled('report')">
            <option value="zip">完整报告 ZIP</option><option value="html">HTML</option>
            <option v-if="summary?.capabilities.report?.formats.includes('PDF')" value="pdf">PDF · A4</option>
          </select>
        </label>
        <p v-if="failures[card.kind] || summary?.exports[card.kind]?.reason" class="error card-error" role="alert">{{ failures[card.kind] || summary?.exports[card.kind]?.reason }}</p>
        <p v-if="card.kind === 'report' && pdfReason" class="pdf-unavailable" data-testid="export-pdf-unavailable">PDF 不可用：{{ pdfReason }}</p>
        <button v-if="card.kind === 'report' && summary?.capabilities.report?.retryable_formats.includes('PDF')" class="pdf-retry" :disabled="disabled('report')" @click="start('report', 'pdf')">重试 PDF</button>
      </article>
    </div>
  </section>
</template>

<style scoped>
.export-center{margin:1.5rem 0;padding:1.5rem;border:1px solid var(--sp-border,var(--sp-border));border-radius: var(--sp-radius);background:#fff;color:var(--sp-text);min-width:0}
.export-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;margin-bottom:1.25rem}.export-heading h2{margin:0;font-size:1.1rem;font-weight:650}.export-heading p{margin:.5rem 0 0;color:var(--sp-muted);font-size:.85rem;line-height:1.6}.export-origin{font-size:.75rem;color:#52687a;border:1px solid var(--sp-border);border-radius: 12px;padding:.3rem .55rem;white-space:nowrap}
.export-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.export-card{border:1px solid var(--sp-border);border-radius: 12px;background:#fafbfd;overflow:hidden;min-width:0;display:flex;flex-direction:column}.export-action{appearance:none;border:0;background:transparent;color:inherit;font:inherit;width:100%;padding:1.7rem 1rem 1.2rem;display:flex;align-items:center;flex-direction:column;gap:.65rem;cursor:pointer;flex:1;transition:background-color .15s,color .15s}.export-action:hover:not(:disabled){background:#eef5fd;color:#1768b8}.export-action:focus-visible,select:focus-visible{outline:2px solid #2477cc;outline-offset:-3px}.export-action:disabled{cursor:not-allowed;color:#788897}.export-icon{color:#37617f;margin-bottom:.45rem}.export-action strong{font-size:1rem;font-weight:650}.formats{font-size:.8rem;letter-spacing:.02em;color:#52687a}.detail{font-size:.76rem;line-height:1.6;text-align:center;color:var(--sp-muted)}.action-status{display:flex;align-items:center;gap:.45rem;font-size:.78rem;color:#1768b8;margin-top:.55rem}.export-action:disabled .action-status{color:#788897}.format-choice{display:flex;justify-content:center;align-items:center;gap:.5rem;font-size:.75rem;padding:0 .8rem 1rem;color:#52687a}select{max-width:100%;font:inherit;border:1px solid #c9d6e3;border-radius: 12px;padding:.35rem;background:white;color:var(--sp-text)}.error{font-size:.8rem;color:#a52e3b;line-height:1.65;overflow-wrap:anywhere}.card-error,.pdf-unavailable{padding:0 1rem;margin:0 0 1rem}.pdf-unavailable,.availability{font-size:.78rem;color:var(--sp-muted);line-height:1.65}.error button{font:inherit;color:#1768b8;background:white;border:1px solid #c9d6e3;border-radius: 12px;padding:.3rem .6rem}.spinner{animation:export-spin 1s linear infinite}@keyframes export-spin{to{transform:rotate(360deg)}}
@media(max-width:620px){.export-center{padding:1rem}.export-grid{gap:.5rem}.export-action{padding:1.2rem .4rem 1rem;gap:.5rem}.export-action strong{font-size:.85rem}.detail{display:none}.formats,.action-status{font-size:.68rem}.format-choice{flex-direction:column;padding:0 .3rem .7rem}.export-origin{display:none}.card-error,.pdf-unavailable{padding:0 .4rem;font-size:.7rem}}
.pdf-retry{align-self:center;border:1px solid #c9d6e3;background:white;color:#1768b8;font:inherit;font-size:.75rem;border-radius: 12px;padding:.35rem .75rem;margin:0 0 1rem;cursor:pointer}.pdf-retry:disabled{opacity:.5;cursor:not-allowed}
@media(prefers-reduced-motion:reduce){.spinner{animation:none}.export-action{transition:none}}
</style>
