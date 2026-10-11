<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { zh } from '../presentation/zh-CN'
import { activeProvider, dataService, createRequestGuard, type Loaded } from '../data'
import type { ExperimentCatalogEntry, ExperimentOverview } from '../data/domain'
import { useCaseRegistry } from '../data/v2/useCaseRegistry'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import MockBadge from '../components/MockBadge.vue'
import LiveCaseCard from '../components/LiveCaseCard.vue'

const registry = useCaseRegistry()
const executable = computed(() => registry.isError.value ? [] : registry.data.value?.cases.filter(c => c.execution_available && c.templates.length) ?? [])
const experiments = ref<Loaded<ExperimentCatalogEntry[]> | null>(null)
const case8 = ref<Loaded<ExperimentOverview> | null>(null)
const catalogGuard = createRequestGuard(), caseGuard = createRequestGuard()
onMounted(async () => {
  const [catalog, overview] = await Promise.all([
    catalogGuard.run(signal => dataService.listExperiments(signal)),
    caseGuard.run(signal => dataService.getExperimentOverview('case8', signal)),
  ])
  if (catalog) experiments.value = catalog
  if (overview) case8.value = overview
})
onUnmounted(() => { catalogGuard.cancel(); caseGuard.cancel() })
</script>
<template>
  <main data-page="lab" class="lab">
    <header><p class="sp-eyebrow">SHOCKPATH · 算例库</p><h1>算例库</h1><p class="sp-intro">选择可执行算例开始新计算，或打开已有科研记录进行回放与分析。实时计算与历史数据分别标明。</p></header>
    <section class="sp-section" aria-labelledby="live-heading" data-testid="live-case-library">
      <div class="sp-section-heading"><h2 id="live-heading">实时求解算例</h2><RouterLink to="/experiments/new">新建计算 →</RouterLink></div>
      <div v-if="registry.isError.value" class="sp-state sp-state--error" role="alert">无法核查实时求解能力。<button class="sp-button" @click="registry.refetch()">重试能力检查</button></div>
      <p v-else-if="registry.isPending.value" class="sp-state" role="status">正在核查后端执行能力…</p>
      <LiveCaseCard v-for="liveCase in executable" v-else-if="executable.length" :key="liveCase.case_id" :live-case="liveCase" />
      <p v-else class="sp-state" data-testid="no-live-cases">求解服务未启动或当前没有可执行算例。新建计算页仍可查看已登记的模板、支持参数并验证配置；服务恢复后才能启动真实求解。</p>
    </section>
    <section class="sp-section" aria-labelledby="history-heading" data-testid="history-case-library">
      <div class="sp-section-heading"><h2 id="history-heading">历史科研算例</h2><span class="sp-badge sp-badge--history">历史数据回放</span></div>
      <p class="sp-muted">以下入口读取已有科研数据，切换配置或图表不会启动 Solver。软件交付状态与科学验证状态分别保留。</p>
      <LoadStateBlock :loaded="experiments" :target="zh('experiment catalog')">
        <ul class="lab__list sp-grid" data-testid="lab-experiment-list">
          <li v-for="exp in experiments?.data || []" :key="exp.experiment_id" class="sp-panel lab__item" :data-testid="`lab-experiment-${exp.experiment_id}`">
            <div class="lab__item-head"><h3>{{ zh(exp.name) }}</h3><span class="sp-badge" :data-testid="`lab-delivery-${exp.experiment_id}`">{{ zh(exp.delivery_status) }}</span></div>
            <span class="sp-badge sp-badge--history">历史数据回放</span>
            <p class="lab__summary">{{ zh(exp.summary) }}</p>
            <template v-if="exp.delivery_status === 'IMPLEMENTED' && exp.implementable_route">
              <p class="sp-muted" :data-testid="`${exp.experiment_id}-capability`">{{ zh(exp.availability_note ?? exp.summary) }}</p>
              <RouterLink class="sp-button" :to="{ name: 'experiment', params: { experiment_id: exp.experiment_id } }" :data-testid="`open-${exp.experiment_id}`">查看 {{ zh(exp.name) }} →</RouterLink>
            </template>
            <template v-else><p class="sp-muted" :data-testid="`lab-planned-note-${exp.experiment_id}`">{{ zh('Delivery: PLANNED — no interactive page is registered yet. This is an application delivery state,') }} <strong>{{ zh('not') }}</strong> {{ zh('MISSING scientific data.') }}</p><span class="sp-muted" aria-disabled="true">{{ zh('Not yet available') }}</span></template>
          </li>
          <li class="sp-panel lab__item" data-testid="history-cross-flow"><div class="lab__item-head"><h3>跨流动比较</h3></div><span class="sp-badge sp-badge--history">历史数据回放</span><p>并列查看 Case 8 与 Mach 3 圆柱绕流的已记录路径、分配与响应。保留不同定义和适用范围，不进行统一性能排名。</p><RouterLink to="/cross-flow" class="sp-button">查看跨流动比较 →</RouterLink></li>
        </ul>
      </LoadStateBlock>
      <details class="sp-panel sp-section"><summary>Case 8 历史配置</summary>
        <LoadStateBlock :loaded="case8" :target="zh('Case8 overview')">
          <table data-testid="lab-case8-configs"><thead><tr><th>配置</th><th>q_aa</th><th>q_at</th></tr></thead><tbody><tr v-for="cfg in case8?.data?.configurations || []" :key="cfg.config_id"><td>{{ cfg.config_id }}</td><td>{{ cfg.q_aa }}</td><td>{{ cfg.q_at }}</td></tr></tbody></table>
          <p class="sp-muted">{{ zh('All four configs are equally selectable; D_u is only a convenient starting point, not "best".') }}</p>
        </LoadStateBlock>
      </details>
    </section>
    <nav class="sp-subnav sp-section" aria-label="算例相关教程"><RouterLink to="/help">帮助与科研教程</RouterLink><RouterLink :to="{ name: 'explore', query: { scene: '1' } }" data-testid="lab-open-explore">七幕引导探索</RouterLink><RouterLink to="/lab/mechanism" data-testid="lab-open-mechanism">跨模态耗散机制</RouterLink></nav>
    <MockBadge v-if="activeProvider.kind === 'MOCK'" origin="MOCK" verification="NOT_APPLICABLE" />
  </main>
</template>
<style scoped>
.lab__list { list-style: none; padding: 0; }
.lab__item-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.lab__item-head h3 { margin: 0; }.lab__item p { font-size: 14px; }.lab__item .sp-button { margin-top: 6px; }
summary { cursor: pointer; color: var(--sp-primary); }table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }th,td { padding: 10px; text-align: left; border-bottom: 1px solid var(--sp-border); }
</style>
