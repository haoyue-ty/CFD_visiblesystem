<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { loadRuns, statusLabels, type RunRecord, type RunStatus } from '../data/v2/runs'
const runs = ref<RunRecord[]>([])
const total = ref(0)
const offset = ref(0)
const filter = ref<RunStatus | ''>('')
const error = ref('')
const loading = ref(true)
let timer: ReturnType<typeof setInterval> | undefined
let generation = 0
async function refresh() {
  const current = ++generation
  try {
    const result = await loadRuns(offset.value, filter.value || undefined)
    if (current !== generation) return
    runs.value = result.runs; total.value = result.total; error.value = ''
  } catch (e) { if (current === generation) error.value = e instanceof Error ? e.message : '加载失败，请重试。' }
  finally { if (current === generation) loading.value = false }
}
watch(filter, () => { offset.value = 0; refresh() })
watch(offset, refresh)
onMounted(() => { refresh(); timer = setInterval(refresh, 5000) })
onUnmounted(() => { generation++; clearInterval(timer) })
</script>

<template>
  <main class="workspace" data-page="run-list">
    <header><p class="eyebrow">SHOCKPATH · 实验工作台</p><h1>我的运行</h1>
      <p>查看新建实验的真实运行记录。任务按提交顺序串行求解，刷新后可继续查看。</p>
      <RouterLink to="/experiments/new" class="primary">新建实验</RouterLink></header>
    <div class="toolbar"><RouterLink to="/workspace/compare">运行 A/B 对比</RouterLink><RouterLink to="/workspace/sweeps">系数扫描</RouterLink></div>
    <div class="toolbar"><label>运行状态 <select v-model="filter" aria-label="运行状态"><option value="">全部</option>
      <option v-for="(label, key) in statusLabels" :key="key" :value="key">{{ label }}</option></select></label>
      <button @click="refresh">刷新列表</button><span>共 {{ total }} 次运行</span></div>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="loading" role="status">正在加载…</p>
    <p v-else-if="!runs.length && !error" data-testid="empty-runs">还没有符合条件的运行。创建并确认配置后即可提交。</p>
    <ul class="runs"><li v-for="run in runs" :key="run.run_id" data-testid="run-list-item">
      <RouterLink :to="'/runs/' + run.run_id">Case 8 · {{ run.experiment.normalized_config.grid.nx }} × {{ run.experiment.normalized_config.grid.ny }}</RouterLink>
      <strong>{{ statusLabels[run.status] }}</strong>
      <p>q_aa={{ run.experiment.normalized_config.method.q_aa }} · q_at={{ run.experiment.normalized_config.method.q_at }} · T={{ run.requested_final_time }}</p>
      <small>{{ new Date(run.created_at).toLocaleString() }} · {{ run.run_id }}</small>
    </li></ul>
    <div class="toolbar"><button :disabled="offset === 0" @click="offset = Math.max(0, offset - 20)">上一页</button>
      <button :disabled="offset + 20 >= total" @click="offset += 20">下一页</button></div>
    <p class="hint">数据来源：本次 V2 计算。历史 V1 回放仍可从数字实验室访问。</p>
  </main>
</template>

<style scoped>
.workspace { max-width: 1100px; margin: auto; padding: 2.5rem 1.5rem; color: #24384c; }
.eyebrow { font-size: .75rem; letter-spacing: .12em; color: #476e93; }p { line-height: 1.7; }
button,select,.primary { font: inherit; padding: .55rem .9rem; border: 1px solid #bdccda; border-radius: 5px; background: white; color: #254b6c; }
.primary { display: inline-block; background: #214f75; color: white; text-decoration: none; }button:disabled { opacity: .5; }
.toolbar { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin: 1.5rem 0; }
.runs { padding: 0; list-style: none; }.runs li { padding: 1.2rem; border: 1px solid #dce4eb; border-radius: 8px; margin: .8rem 0; overflow-wrap: anywhere; }
strong { float: right; }a { color: #214f75; }.hint,small { color: #617184; font-size: .8rem; }
@media(max-width:780px) { .workspace { padding: 1.5rem 1rem; }strong { float: none; margin-left: 1rem; } }
</style>
