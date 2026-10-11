<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { useCaseRegistry } from '../data/v2/useCaseRegistry'
import { loadRuns } from '../data/v2/runs'
import AppIcon from '../components/AppIcon.vue'
import RunSummaryList from '../components/RunSummaryList.vue'

const registry = useCaseRegistry()
const router = useRouter()
const experimentPrompt = ref('')
function beginExperiment() {
  const prompt = experimentPrompt.value.trim()
  router.push({ path: '/experiments/new', query: prompt ? { prompt } : {} })
}
const recent = useQuery({ queryKey: ['v2', 'runs', 'recent'], queryFn: () => loadRuns(0, undefined, 5), refetchInterval: 5000, retry: false })
const templates = computed(() => {
  if (registry.isError.value) return []
  const items = registry.data.value?.cases.find(c => c.case_id === 'case8')?.templates ?? []
  const fast = items.find(t => t.profile === 'fast')
  const paper = items.find(t => t.template_id === 'case8.paper.D_u') ?? items.find(t => t.profile === 'paper')
  return [
    ...(fast ? [{ template: fast, label: 'Case 8 快速配置', caption: '较小网格，快速走通求解与分析流程。' }] : []),
    ...(paper ? [{ template: paper, label: 'Case 8 论文标准配置', caption: '沿用登记论文协议，核对配置后启动新运行。' }] : []),
  ]
})
const abilities = [
  { icon: 'activity', name: '真实 CFD 求解', text: '基于已登记 Solver 执行计算，观察真实进度。' },
  { icon: 'chart', name: '熵耗散路径分析', text: '读取逐步熵预算与原生 face 空间分配。' },
  { icon: 'layers', name: '流场可视化', text: '查看密度、压力、速度与 Mach 的真实快照。' },
  { icon: 'spark', name: 'AI 科研辅助', text: '围绕科学结果与当前视图解释数据、回答问题。' },
  { icon: 'dashboard', name: '参数比较', text: '核查可比条件，执行 A/B 对比与系数扫描。' },
  { icon: 'file', name: '实验报告', text: '保存包含配置、图表和来源的离线 HTML 报告。' },
]
</script>
<template>
  <main data-page="home" class="home">
    <header class="home__hero">
      <p class="home__wordmark"><AppIcon name="activity" />ShockPath</p>
      <h1>探索流动之境</h1>
      <p class="home__intro">从一个想法，到一次数值实验。</p>
      <form class="home__composer" @submit.prevent="beginExperiment">
        <label for="experiment-prompt" class="sr-only">描述你的实验</label>
        <textarea id="experiment-prompt" v-model="experimentPrompt" maxlength="4000" rows="2" placeholder="描述你想探索的实验，或直接从模板开始…" />
        <div class="home__composer-tools">
          <div class="home__composer-modes"><RouterLink to="/experiments/new" class="home__mode"><AppIcon name="flask" />模板创建</RouterLink><RouterLink :to="{ path: '/experiments/new', query: { mode: 'form' } }" class="home__mode home__mode--blue"><AppIcon name="settings" />专业参数</RouterLink></div>
          <span data-testid="new-experiment-entry"><button type="submit" class="home__send" aria-label="开始新计算" title="开始新计算"><AppIcon name="up" /></button></span>
        </div>
      </form>
      <p class="home__composer-hint">实验描述将带入配置页，核对参数后再启动求解。</p>
      <div class="home__shortcuts">
        <RouterLink to="/workspace" class="sp-button"><AppIcon name="activity" />运行任务</RouterLink>
        <RouterLink to="/lab" class="sp-button" data-testid="home-to-lab"><AppIcon name="layers" />浏览算例库</RouterLink>
        <RouterLink to="/help" class="sp-button" data-testid="home-to-help"><AppIcon name="book" />科研入门</RouterLink>
      </div>
    </header>
    <section class="sp-section" aria-labelledby="quick-create-heading">
      <div class="sp-section-heading"><h2 id="quick-create-heading">从模板开始</h2><span class="sp-muted">选择一个起点，自由探索</span></div>
      <div v-if="registry.isError.value" class="sp-state sp-state--error" role="alert">模板服务暂不可用。<button class="sp-button" @click="registry.refetch()">重试模板</button></div>
      <p v-else-if="registry.isPending.value" class="sp-state" role="status">正在加载真实算例模板…</p>
      <div v-else-if="templates.length" class="sp-grid">
        <article v-for="item in templates" :key="item.template.template_id" class="sp-panel home__template">
          <AppIcon :name="item.template.profile === 'fast' ? 'activity' : 'book'" />
          <h3>{{ item.label }}</h3><p class="sp-muted">{{ item.caption }}</p>
          <p>{{ item.template.config.grid.nx }} × {{ item.template.config.grid.ny }} · CFL={{ item.template.config.time.cfl }} · T={{ item.template.config.time.final_time }}</p>
          <RouterLink :to="{ path: '/experiments/new', query: { template: item.template.template_id } }" class="sp-button" :data-testid="`quick-${item.template.profile}`">使用此模板<AppIcon name="arrow" /></RouterLink>
        </article>
      </div>
      <p v-else class="sp-state">后端尚未登记可用模板，请在新建计算页查看能力状态。</p>
    </section>
    <section class="sp-section" aria-labelledby="recent-heading">
      <div class="sp-section-heading"><h2 id="recent-heading">近期运行</h2><RouterLink to="/workspace">查看全部任务 →</RouterLink></div>
      <div v-if="recent.isError.value" class="sp-state sp-state--error" role="alert" data-testid="recent-runs-error"><p>无法获取运行记录，请检查后端服务。{{ recent.error.value?.message }}</p><button class="sp-button" @click="recent.refetch()">重试运行记录</button></div>
      <p v-else-if="recent.isPending.value" class="sp-state" role="status">正在加载近期运行…</p>
      <RunSummaryList v-else-if="recent.data.value?.runs.length" :runs="recent.data.value.runs" />
      <div v-else class="sp-state sp-state--empty" data-testid="empty-runs"><p>还没有运行记录。选择模板，创建你的第一个数值实验。</p><RouterLink to="/experiments/new" class="sp-button sp-button--primary">创建第一个实验</RouterLink></div>
    </section>
    <section class="sp-section" aria-labelledby="abilities-heading">
      <div class="sp-section-heading"><h2 id="abilities-heading">系统能力</h2></div>
      <div class="home__abilities"><article v-for="item in abilities" :key="item.name" class="sp-panel"><AppIcon :name="item.icon" /><h3>{{ item.name }}</h3><p class="sp-muted">{{ item.text }}</p></article></div>
    </section>
    <footer class="home__footer">ShockPath · 交互式 CFD 求解与智能数值分析</footer>
  </main>
</template>
<style scoped>
#app main.home { max-width: 1100px; padding-top: 0; }
.home__hero { padding: 70px 0 54px; text-align: center; }
.home__wordmark { display: inline-flex; align-items: center; gap: 10px; margin: 0 0 24px; font-size: 29px; font-weight: 650; letter-spacing: -.8px; color: var(--sp-primary); }
.home__wordmark .sp-icon { width: 36px; height: 36px; }
.home__hero h1 { font-size: clamp(30px, 3.4vw, 44px); letter-spacing: 5px; margin: 0 0 14px; font-weight: 500; color: #273650; }
.home__intro { color: var(--sp-muted); font-size: 15px; margin: 0 0 36px; }
.home__composer { max-width: 790px; margin-inline: auto; text-align: left; background: #f6f7fb; border: 1px solid #eef0f5; border-radius: 26px; padding: 20px 18px 16px 24px; transition: border-color .15s, box-shadow .15s; }
.home__composer:focus-within { border-color: #a8b6ff; box-shadow: 0 0 0 3px #4d6bfe0b; }
.home__composer textarea { width: 100%; resize: none; min-height: 78px; border: 0; outline: none; background: transparent; color: var(--sp-text); font-size: 16px; line-height: 1.8; padding: 0; }
.home__composer textarea::placeholder { color: #697386; }
.home__composer-tools, .home__composer-modes { display: flex; align-items: center; gap: 10px; }
.home__composer-tools { justify-content: space-between; }
.home__mode { display: inline-flex; align-items: center; gap: 7px; min-height: 36px; padding: 6px 12px; border: 1px solid #dde0e8; border-radius: 999px; color: #555e70; text-decoration: none; font-size: 12px; background: transparent; }
.home__mode .sp-icon { width: 16px; height: 16px; }.home__mode:hover { background: #e8edf8; }.home__mode--blue { color: var(--sp-primary); border-color: #c6d1ff; background: #eaf0ff; }
.home__send { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; border: 0; padding: 10px; border-radius: 50%; background: var(--sp-primary); color: #fff; cursor: pointer; }.home__send:hover { background: var(--sp-primary-hover); }.home__send .sp-icon { width: 23px; height: 23px; }
.home__composer-hint { color: var(--sp-muted); font-size: 11px; margin: 12px 0 25px; }
.home__shortcuts { display: flex; justify-content: center; flex-wrap: wrap; gap: 12px; }.home__shortcuts .sp-button { font-size: 13px; color: #5c6373; padding-inline: 18px; }
.home__template .sp-icon, .home__abilities .sp-icon { color: var(--sp-primary); width: 24px; height: 24px; }
.home__template h3 { margin: 12px 0 8px; }.home__template p { font-size: 13px; }.home__template .sp-button { margin-top: 8px; }
.home__template { background: #fafbff; border-color: #edf0f7; }.home__template h3 { font-weight: 500; }
.home__abilities { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }.home__abilities .sp-panel { border: 0; padding: 20px 8px; }
.home__abilities h3 { margin: 12px 0 8px; }.home__abilities p { margin: 0; }
.home__footer { text-align: center; padding-top: 48px; color: #a1a6b1; font-size: 11px; }
@media (max-width: 768px) { .home__abilities { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 600px) { .home__hero { padding: 45px 0 28px; }.home__hero h1 { letter-spacing: 3px; font-size: 30px; }.home__wordmark { font-size: 25px; margin-bottom: 22px; }.home__intro { font-size: 13px; margin-bottom: 28px; }.home__composer { padding: 18px 14px; border-radius: 22px; }.home__composer textarea { font-size: 14px; min-height: 86px; }.home__composer-modes { gap: 6px; }.home__mode { font-size: 11px; padding: 6px 10px; }.home__shortcuts { gap: 8px; }.home__shortcuts .sp-button { font-size: 12px; padding: 9px 12px; }.home__abilities { grid-template-columns: 1fr; } }
</style>
