<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createRequestGuard, type Loaded } from '../data'
import { closureService, known, slotValue, runLabel, PAGE_SIZE, type Science, type HistoryBundle, type Refinement } from '../data/closure'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import EvidenceLink from '../scientific/EvidenceLink.vue'
import ClosureHistory from '../views/closure/ClosureHistory.vue'
import ClosureRefinement from '../views/closure/ClosureRefinement.vue'
const route = useRoute(), router = useRouter()
const tabs = { overview: 'Overview', 'semi-discrete': 'Semi-discrete', 'fully-discrete': 'Fully-discrete', evidence: 'Evidence' }
const tab = computed(() => typeof route.query.tab === 'string' && Object.hasOwn(tabs, route.query.tab) ? route.query.tab as keyof typeof tabs : 'overview')
const unsupportedTab = computed(() => typeof route.query.tab === 'string' && !Object.hasOwn(tabs, route.query.tab))
const registry = ref<Loaded<Science['ClosureRunRegistry']> | null>(null)
const runs = computed(() => registry.value?.data?.runs ?? [])
const run = computed(() => route.query.run === undefined ? runs.value[0] : runs.value.find(r => r.run_id === route.query.run))
const terminal = computed(() => run.value?.terminal_summary.map(s => slotValue(s)).filter(m => m !== null) ?? [])
const zeroChannel = computed(() => !!run.value && known(run.value.config.parameters.find(p => p.name === 'q_at')!.value) === 0
  && terminal.value.some(m => m.metric_id === 'E_at_total' && known(m.value) === 0))
const count = computed(() => tab.value === 'semi-discrete' ? run.value?.stage_point_count ?? 0 : run.value?.step_point_count ?? 0)
const offset = computed(() => {
  const value = Number(route.query.offset ?? 0)
  return Number.isInteger(value) && value >= 0 && value < count.value && value % PAGE_SIZE === 0 ? value : 0
})
function update(patch: Record<string, string>) { router.push({ query: { run: run.value?.run_id, tab: tab.value, offset: String(offset.value), ...patch } }) }
const history = ref<Loaded<HistoryBundle> | null>(null)
const refinement = ref<Loaded<Refinement> | null>(null)
const evidence = ref<Loaded<{ stage: string[]; step: string[] }> | null>(null)
const registryGuard = createRequestGuard(), historyGuard = createRequestGuard(), refinementGuard = createRequestGuard(), evidenceGuard = createRequestGuard()
const loading = () => ({ state: 'LOADING' as const, data: null, reason: null, origin: 'FROZEN_PRODUCTION' as const })
async function loadRegistry() {
  registry.value = loading()
  const result = await registryGuard.run(signal => closureService.runs(signal))
  if (result) registry.value = result
}
loadRegistry()
async function loadRefinement() {
  refinement.value = loading()
  const result = await refinementGuard.run(signal => closureService.refinement(signal))
  if (result) refinement.value = result
}
loadRefinement()
watch([run, tab, offset], async ([current, active, start]) => {
  historyGuard.cancel(); evidenceGuard.cancel(); history.value = null; evidence.value = null
  if (!current) return
  if (active === 'semi-discrete' || active === 'fully-discrete') {
    history.value = loading()
    const result = await historyGuard.run(signal => closureService.history(current, active === 'semi-discrete' ? 'PER_STAGE' : 'PER_STEP', start, signal))
    if (result) history.value = result
  } else if (active === 'evidence') {
    evidence.value = loading()
    const result = await evidenceGuard.run(signal => closureService.evidence(current, signal))
    if (result) evidence.value = result
  }
}, { immediate: true })
onBeforeUnmount(() => { registryGuard.cancel(); historyGuard.cancel(); refinementGuard.cancel(); evidenceGuard.cancel() })
</script>
<template>
  <main data-page="entropy-closure" class="closure">
    <nav><RouterLink to="/lab">Lab</RouterLink> → Entropy Closure</nav>
    <h1>Entropy Closure</h1>
    <p>Frozen periodic Case7 · first-order finite volume · SSP-RK3 · recorded scientific diagnostics</p>
    <aside role="note" data-testid="fully-discrete-limitation">Fully-discrete residual is a numerical diagnostic, not an exact fully-discrete entropy identity.</aside>
    <LoadStateBlock :loaded="registry" target="CLO01 legal run registry">
      <label>Run <select data-testid="closure-run" :value="run?.run_id ?? ''" @change="update({ run: ($event.target as HTMLSelectElement).value, offset: '0' })"><option v-for="r in runs" :key="r.run_id" :value="r.run_id">{{ runLabel(r) }}</option></select></label>
      <p v-if="!run" role="alert" data-testid="invalid-run">Unsupported run selection: choose one of the five recorded CLO01 runs.</p>
      <nav role="tablist" aria-label="Entropy Closure tabs"><button v-for="(label, id) in tabs" :key="id" role="tab" :aria-selected="tab === id" :data-testid="`tab-${id}`" @click="update({ tab: id, offset: '0' })">{{ label }}</button></nav>
      <p v-if="unsupportedTab" role="note" data-testid="unsupported-tab">Requested view is unavailable for Entropy Closure. No saved spatial trajectory; supported scalar views are shown below.</p>
      <template v-if="run">
        <p data-testid="selected-run">{{ runLabel(run) }} · {{ run.stage_point_count }} stage records · {{ run.step_point_count }} accepted steps</p>
        <p v-if="zeroChannel" data-testid="bu-zero-channel">D_at=0 — recorded zero channel. E_at step increments and terminal total are recorded zero.</p>
        <section role="tabpanel" :aria-label="tabs[tab]">
          <template v-if="tab === 'overview'">
            <h2>Recorded closure diagnostics</h2>
            <p data-testid="spatial-trajectory">Spatial trajectory: MISSING / not recorded</p>
            <p>PER_STAGE: 3 RK stages per accepted step. Stage clock is the containing time_n; stage-state physical time is NOT_ESTABLISHED.</p>
            <p>PER_STEP: recorded increments, cumulative temporal residual, and terminal residual remain distinct.</p>
            <p>Method: {{ known(run.config.protocol.method_name) }} · integrator: {{ known(run.config.protocol.integrator) }} · T={{ known(run.config.protocol.final_time) }}</p>
            <p v-for="p in run.config.parameters" :key="p.name">{{ p.name }}={{ known(p.value) }}</p>
          </template>
          <template v-if="tab === 'overview' || tab === 'fully-discrete'">
            <h2>Terminal summary · TERMINAL</h2>
            <p>R_total = terminal R(T). These totals are separate from PER_STEP increments and the recorded R_time_cumulative history.</p>
            <table data-testid="terminal-summary"><thead><tr><th>Metric</th><th>Value</th><th>Unit</th><th>Accumulation</th></tr></thead><tbody><tr v-for="m in terminal" :key="m.metric_id" :data-metric="m.metric_id"><th>{{ m.display_label }}</th><td>{{ known(m.value) ?? 'UNKNOWN' }}</td><td>{{ m.result.unit.label }}</td><td>{{ m.time_scope.accumulation }}</td></tr></tbody></table>
            <EvidenceLink v-for="id in run.evidence_refs" :key="id" :evidence-id="id" />
          </template>
          <template v-if="tab === 'semi-discrete' || tab === 'fully-discrete'">
            <LoadStateBlock :loaded="history" target="recorded closure history"><ClosureHistory v-if="history?.data" :bundle="history.data" :key="`${run.run_id}:${tab}:${offset}`" /></LoadStateBlock>
            <nav v-if="history?.data" aria-label="History pages"><button data-testid="history-previous" :disabled="offset === 0" @click="update({ offset: String(offset - PAGE_SIZE) })">Previous records</button><span>Page {{ offset / PAGE_SIZE + 1 }} / {{ Math.ceil(count / PAGE_SIZE) }}</span><button data-testid="history-next" :disabled="offset + PAGE_SIZE >= count" @click="update({ offset: String(offset + PAGE_SIZE) })">Next records</button><button data-testid="history-last" :disabled="offset + PAGE_SIZE >= count" @click="update({ offset: String(Math.floor((count - 1) / PAGE_SIZE) * PAGE_SIZE) })">Last records</button></nav>
          </template>
          <template v-if="tab === 'overview' || tab === 'fully-discrete'">
            <LoadStateBlock :loaded="refinement" target="CLO05 frozen refinement"><ClosureRefinement v-if="refinement?.data" :summary="refinement.data" :runs="runs" /></LoadStateBlock>
          </template>
          <template v-if="tab === 'evidence'">
            <h2>Evidence · current run: {{ runLabel(run) }}</h2>
            <p>Run <EvidenceLink v-for="id in run.evidence_refs" :key="id" :evidence-id="id" /></p>
            <LoadStateBlock :loaded="evidence" target="current run history evidence"><template v-if="evidence?.data"><p>Semi-discrete <EvidenceLink v-for="id in evidence.data.stage" :key="id" :evidence-id="id" /></p><p>Fully-discrete <EvidenceLink v-for="id in evidence.data.step" :key="id" :evidence-id="id" /></p></template></LoadStateBlock>
            <LoadStateBlock :loaded="refinement" target="refinement evidence"><p v-if="refinement?.data">D_u refinement <EvidenceLink v-for="id in refinement.data.evidence_refs" :key="id" :evidence-id="id" /></p></LoadStateBlock>
            <h3>All five recorded runs</h3><p v-for="r in runs" :key="r.run_id">{{ runLabel(r) }} <EvidenceLink v-for="id in r.evidence_refs" :key="id" :evidence-id="id" /></p>
          </template>
        </section>
      </template>
    </LoadStateBlock>
    <button v-if="registry?.state === 'ERROR' || registry?.state === 'MISSING'" @click="loadRegistry">Retry run registry</button>
  </main>
</template>
<style scoped>.closure { max-width:76rem; margin:auto; padding:1.5rem; } nav { display:flex; gap:.6rem; flex-wrap:wrap; margin:1rem 0; } button,select { padding:.4rem .7rem; } button[aria-selected=true] { font-weight:bold; border:2px solid #1a4f8a; } aside { border-left:3px solid #bd7800; padding:.75rem; background:#fffaf0; margin:1rem 0; } table { border-collapse:collapse; width:100%; } td,th { text-align:left; padding:.4rem; border:1px solid #ddd; }</style>
