<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { generateReport, loadReport, saveReport } from '../data/v2/reports'
const route = useRoute()
const report = ref<Awaited<ReturnType<typeof loadReport>> | null>(null)
const error = ref('')
const busy = ref(false)
const saving = ref(false)
let generation = 0
async function load() {
  const current = ++generation
  report.value = null; error.value = ''; busy.value = true
  try { const result = await loadReport(String(route.params.runId)); if (current === generation) report.value = result }
  catch (e) { if (current === generation) error.value = e instanceof Error ? e.message : '报告加载失败。' }
  finally { if (current === generation) busy.value = false }
}
async function generate() {
  const current = generation
  busy.value = true; error.value = ''
  try { const result = await generateReport(String(route.params.runId)); if (current === generation) report.value = result }
  catch (e) { if (current === generation) error.value = e instanceof Error ? e.message : '报告生成失败。' }
  finally { if (current === generation) busy.value = false }
}
async function save() {
  const current = generation
  saving.value = true; error.value = ''
  try { await saveReport(String(route.params.runId)) }
  catch (e) { if (current === generation) error.value = e instanceof Error ? e.message : '报告保存失败。' }
  finally { if (current === generation) saving.value = false }
}
watch(() => route.params.runId, load, { immediate: true })
</script>

<template>
  <main class="report-page" data-page="run-report">
    <RouterLink :to="`/runs/${route.params.runId}`">← 本次运行结果</RouterLink>
    <h1>实验报告</h1>
    <p>固定 12 节结构，包含真实配置、数字、流场图、熵预算和来源。保存 HTML 后可离线打开。</p>
    <p v-if="error" role="alert" data-testid="report-error">{{ error }} <button :disabled="busy" @click="load">重新加载</button></p>
    <p v-if="busy" role="status">正在核查并生成报告…</p>
    <template v-if="report">
      <section class="panel">
        <p v-if="report.status === 'NOT_GENERATED'">本次运行尚未生成报告。</p>
        <p v-else-if="report.status === 'STALE'">结果、解读或报告版本已变化，请更新报告。</p>
        <p v-else data-testid="report-ready">报告已保存 · {{ report.report_version }} · {{ report.size_bytes }} bytes</p>
        <p data-testid="report-ai">{{ report.ai_status === 'AVAILABLE' ? `已纳入经过证据校验的 AI 解读 · ${report.ai_model} · ${report.ai_prompt_version}` : `AI 解读不可用：${report.ai_reason}。确定性报告仍可生成。` }}</p>
        <button :disabled="busy" @click="generate">{{ report.status === 'NOT_GENERATED' ? '生成实验报告' : '更新报告' }}</button>
        <button v-if="report.status === 'READY'" :disabled="busy || saving" @click="save">保存 HTML</button>
        <p class="hash">result_hash：{{ report.result_hash }}</p>
        <p v-if="report.html_sha256" class="hash">HTML SHA-256：{{ report.html_sha256 }}</p>
        <RouterLink :to="`/runs/${route.params.runId}/evidence`">核查本次运行证据</RouterLink>
      </section>
      <iframe v-if="report.status === 'READY' && report.html_url" :key="report.report_id ?? ''" :src="report.html_url" title="ShockPath 数值实验报告预览" sandbox="" data-testid="report-preview"></iframe>
    </template>
  </main>
</template>

<style scoped>
.report-page{max-width:1100px;margin:auto;padding:2.5rem 1.5rem;color:#24384c;min-width:0}p{line-height:1.7;overflow-wrap:anywhere}a{color:#214f75}.panel{padding:1.5rem;border:1px solid #dce4eb;border-radius:8px;margin:1rem 0}.hash{font-size:.8rem;overflow-wrap:anywhere}button{font:inherit;border:1px solid #bdccda;border-radius:5px;background:white;color:#254b6c;padding:.55rem .9rem;margin:0 .5rem .5rem 0}button:disabled{opacity:.5}iframe{width:100%;height:80vh;border:1px solid #dce4eb;border-radius:8px;background:#fff;box-sizing:border-box}@media(max-width:780px){.report-page{padding:1.5rem 1rem}.panel{padding:1rem}}
</style>
