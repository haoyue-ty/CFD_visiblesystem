<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { loadRuns, statusLabels, type RunRecord, type RunStatus } from '../data/v2/runs'
import WorkspaceNavigation from '../components/WorkspaceNavigation.vue'
import RunSummaryList from '../components/RunSummaryList.vue'
const runs = ref<RunRecord[]>([])
const total = ref(0)
const offset = ref(0)
const filter = ref<RunStatus | ''>('')
const error = ref('')
const loading = ref(true)
let timer: ReturnType<typeof setInterval> | undefined
let generation = 0
let pending = false
async function refresh() {
  if (pending && !loading.value) return
  pending = true
  const current = ++generation
  try {
    const result = await loadRuns(offset.value, filter.value || undefined)
    if (current !== generation) return
    runs.value = result.runs; total.value = result.total; error.value = ''
  } catch (e) { if (current === generation) error.value = e instanceof Error ? e.message : '加载失败，请重试。' }
  finally { if (current === generation) { loading.value = false; pending = false } }
}
watch([filter, offset], ([newFilter], [oldFilter]) => {
  if (newFilter !== oldFilter && offset.value !== 0) { offset.value = 0; return }
  loading.value = true; runs.value = []; refresh()
})
onMounted(() => { refresh(); timer = setInterval(refresh, 5000) })
onUnmounted(() => { generation++; clearInterval(timer) })
</script>

<template>
  <main class="workspace" data-page="run-list">
    <WorkspaceNavigation />
    <header><p class="eyebrow">SHOCKPATH · 运行任务</p><h1>运行任务</h1>
      <p>查看新建实验的真实运行记录。任务按提交顺序串行求解，刷新后可继续查看。</p>
      <RouterLink to="/experiments/new" class="sp-button sp-button--primary">新建计算</RouterLink></header>
    <div class="toolbar"><label>运行状态 <select v-model="filter" aria-label="运行状态"><option value="">全部</option>
      <option v-for="(label, key) in statusLabels" :key="key" :value="key">{{ label }}</option></select></label>
      <button @click="refresh">刷新列表</button><span v-if="!error && !loading">共 {{ total }} 次运行</span></div>
    <p v-if="error" role="alert" class="sp-state sp-state--error">{{ error }}</p><p v-else-if="loading" role="status" class="sp-state">正在加载运行记录…</p>
    <div v-else-if="!runs.length" class="sp-state sp-state--empty" data-testid="empty-runs"><p>{{ filter ? '还没有符合当前筛选条件的运行。' : '还没有运行记录。创建并确认配置后即可提交。' }}</p><RouterLink to="/experiments/new" class="sp-button">创建第一个实验</RouterLink></div>
    <RunSummaryList v-else :runs="runs" />
    <div class="toolbar"><button :disabled="offset === 0" @click="offset = Math.max(0, offset - 20)">上一页</button>
      <button :disabled="offset + 20 >= total" @click="offset += 20">下一页</button></div>
    <p class="hint">数据来源：本次 V2 计算。<RouterLink to="/lab">历史科研数据回放可从算例库访问</RouterLink>。</p>
  </main>
</template>

<style scoped>
.workspace { max-width: 1100px; margin: auto; padding: 2.5rem 1.5rem; color: var(--sp-text); }
.eyebrow { font-size: .75rem; letter-spacing: .12em; color: var(--sp-muted); }p { line-height: 1.7; }
button,select,.primary { font: inherit; padding: .55rem .9rem; border: 1px solid var(--sp-border); border-radius: 12px; background: white; color: var(--sp-text); }
.primary { display: inline-block; background: var(--sp-primary); color: white; text-decoration: none; }button:disabled { opacity: .5; }
.toolbar { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin: 1.5rem 0; }
.runs { padding: 0; list-style: none; }.runs li { padding: 1.2rem; border: 1px solid var(--sp-border); border-radius: 12px; margin: .8rem 0; overflow-wrap: anywhere; }
strong { float: right; }a { color: var(--sp-primary); }.hint,small { color: var(--sp-muted); font-size: .8rem; }
@media(max-width:780px) { .workspace { padding: 1.5rem 1rem; }strong { float: none; margin-left: 1rem; } }
</style>
