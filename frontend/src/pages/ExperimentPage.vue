<script setup lang="ts">
import { activeProvider } from '../data'
/**
 * P06 — Case8 Experiment Detail.
 *
 * Capability-driven tabs (IA 11.2): Overview / Flow / Entropy / Allocation /
 * Metrics / Evidence. Allocation is a config-dependent capability: it is present
 * for the experiment family and DISABLED for A/B/C (only D_u has a recorded
 * cumulative native-face map). A disabled tab keeps its place and shows a
 * visible reason — it is never silently removed.
 *
 * State ownership (README): URL state -> Router, transient -> Pinia, loaded
 * results -> the data service. Config and tab live in the URL query so a refresh
 * or a shared deep link restores them.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { dataService, createRequestGuard, type Loaded } from '../data'
import type { ExperimentOverview } from '../data/domain'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import MockBadge from '../components/MockBadge.vue'
import ExploreReturn from '../components/ExploreReturn.vue'
import OverviewTab from '../views/case8/OverviewTab.vue'
import FlowTab from '../views/case8/FlowTab.vue'
import EntropyTab from '../views/case8/EntropyTab.vue'
import AllocationTab from '../views/case8/AllocationTab.vue'
import MetricsTab from '../views/case8/MetricsTab.vue'
import EvidenceTab from '../views/case8/EvidenceTab.vue'
import SpectralTab from '../views/case8/SpectralTab.vue'

const props = defineProps<{ experiment_id: string }>()
const route = useRoute()
const router = useRouter()

const overview = ref<Loaded<ExperimentOverview> | null>(null)
const overviewGuard = createRequestGuard()

const VALID_CONFIGS = ['A_u', 'B_u', 'C_u', 'D_u'] as const
const VALID_TABS = ['overview', 'flow', 'entropy', 'allocation', 'metrics', 'spectral', 'evidence'] as const
type Tab = (typeof VALID_TABS)[number]

function readQueryString(key: string): string | null {
  const v = route.query[key]
  return typeof v === 'string' ? v : null
}

const configId = ref<string>(normalizeConfig(readQueryString('config')))
const tab = ref<Tab>(normalizeTab(readQueryString('tab')))
const snapshotIndex = ref<number>(normalizeSnapshot(readQueryString('snapshot')))
const fieldId = ref<string>(readQueryString('field') === 'pressure' || readQueryString('field') === 'front' ? (readQueryString('field') as string) : 'density')
const scalarStep = ref<number | null>(readQueryString('step') ? Number(readQueryString('step')) : null)

function normalizeConfig(value: string | null): string {
  // Invalid / unsupported config falls back to the documented default (D_u).
  return value && (VALID_CONFIGS as readonly string[]).includes(value) ? value : 'D_u'
}
function normalizeTab(value: string | null): Tab {
  return value && (VALID_TABS as readonly string[]).includes(value) ? (value as Tab) : 'overview'
}
function normalizeSnapshot(value: string | null): number {
  const n = value ? Number(value) : 1
  // Recorded indices are 1..6; anything else (including 0) is not selectable.
  return Number.isInteger(n) && n >= 1 && n <= 6 ? n : 1
}

const invalidSnapshot = computed(() => {
  const value = readQueryString('snapshot')
  return value !== null && (!Number.isInteger(Number(value)) || Number(value) < 1 || Number(value) > 6)
})
const invalidConfig = computed(() => readQueryString('config') !== null && !(VALID_CONFIGS as readonly string[]).includes(readQueryString('config')!))
const unsupportedTab = computed(() => readQueryString('tab') !== null && !(VALID_TABS as readonly string[]).includes(readQueryString('tab')!))
watch([snapshotIndex, fieldId, scalarStep], () => syncQuery({}))

const isCase8 = computed(() => props.experiment_id === 'case8')

/** Allocation is family-present but config-disabled except for D_u. */
const allocationDisabled = computed(() => configId.value !== 'D_u')

/** Pushing a new query is the single writer of URL state. */
function syncQuery(patch: Record<string, string | number | null>, push = false) {
  const query: Record<string, string> = {}
  for (const key of ['source_scene', 'explore_return', 'allocation_family', 'allocation_gate', 'spectral_q', 'spectral_mode', 'spectral_rank', 'spectral_run']) {
    const value = readQueryString(key)
    if (value !== null) query[key] = value
  }
  const current = { config: configId.value, tab: tab.value, snapshot: String(snapshotIndex.value), field: fieldId.value }
  const merged = { ...current, ...patch } as Record<string, string | number | null>
  if (merged.config) query.config = String(merged.config)
  if (merged.tab) query.tab = String(merged.tab)
  query.snapshot = String(merged.snapshot)
  query.field = String(merged.field)
  if (tab.value === 'entropy' && scalarStep.value !== null) query.step = String(scalarStep.value)
  router[push ? 'push' : 'replace']({ name: 'experiment', params: { experiment_id: props.experiment_id }, query })
}

function selectConfig(value: string) {
  if (!(VALID_CONFIGS as readonly string[]).includes(value)) return
  configId.value = value
  scalarStep.value = null
  // Keep the requested location and explain unavailable configuration assets.
  syncQuery({}, true)
}

function selectTab(value: Tab) {
  if (value === 'allocation' && allocationDisabled.value) return // disabled, not hidden
  tab.value = value
  syncQuery({}, true)
}

onMounted(async () => {
  overview.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await overviewGuard.run((signal) => dataService.getExperimentOverview(props.experiment_id, signal))
  if (result) overview.value = result
})

// Keep the URL in step with back/forward navigation.
watch(
  () => route.query,
  () => {
    configId.value = normalizeConfig(readQueryString('config'))
    tab.value = normalizeTab(readQueryString('tab'))
    snapshotIndex.value = normalizeSnapshot(readQueryString('snapshot'))
    const f = readQueryString('field')
    if (f === 'density' || f === 'pressure' || f === 'front') fieldId.value = f
    scalarStep.value = readQueryString('step') ? Number(readQueryString('step')) : null
  },
)
</script>

<template>
  <main data-page="experiment" class="exp">
    <ExploreReturn />
    <nav class="exp__crumb" aria-label="Breadcrumb">
      <RouterLink :to="{ name: 'home' }">Home</RouterLink> →
      <RouterLink :to="{ name: 'lab' }">Lab</RouterLink> →
      <span>Case8</span> →
      <span class="exp__crumb-current">{{ configId }}</span>
    </nav>
    <RouterLink :to="{ name: 'cross-flow', query: { case8_config: configId, cylinder_config: 'D_u' } }">Case8 ↔ Cylinder · Cross-flow Compare</RouterLink>

    <section v-if="invalidConfig" data-state="invalid-selector">UNSUPPORTED config: {{ readQueryString('config') }}. Choose a recorded Case8 configuration; no default scientific result is substituted.</section>
    <section v-else-if="unsupportedTab" data-testid="unsupported-tab" role="alert">UNSUPPORTED view: {{ readQueryString('tab') }}. Requested location retained.</section>
    <section v-else-if="invalidSnapshot" data-state="invalid-selector">Invalid snapshot selector: recorded indices are 1…6; index 0 is rejected.</section>
    <LoadStateBlock v-else :loaded="overview" target="experiment overview">
      <template v-if="overview?.state === 'READY' || overview?.state === 'PARTIAL'">
        <header class="exp__header">
          <div>
            <h1>Case8 — {{ configId }}</h1>
            <p class="exp__subtitle">Recorded replay · six spatial snapshots + 1912 accepted-step scalar history</p>
          </div>
          <MockBadge v-if="activeProvider.kind === 'MOCK'" origin="MOCK" :verification="activeProvider.kind === 'MOCK' ? 'NOT_APPLICABLE' : undefined" />
        </header>

        <!-- Config selector: A/B/C/D are equally selectable -->
        <div class="exp__configs" role="group" aria-label="Case8 config">
          <span class="exp__configs-label">Config:</span>
          <button
            v-for="cfg in VALID_CONFIGS"
            :key="cfg"
            class="exp__config-btn"
            :class="{ 'exp__config-btn--active': cfg === configId }"
            :data-testid="`config-${cfg}`"
            :aria-pressed="cfg === configId"
            @click="selectConfig(cfg)"
          >{{ cfg }}</button>
        </div>

        <!-- Capability-driven tabs -->
        <nav class="exp__tabs" role="tablist" aria-label="Case8 tabs">
          <button
            v-for="t in VALID_TABS.filter(t => t !== 'spectral')"
            :key="t"
            role="tab"
            class="exp__tab"
            :class="{ 'exp__tab--active': t === tab, 'exp__tab--disabled': t === 'allocation' && allocationDisabled }"
            :data-testid="`tab-${t}`"
            :disabled="t === 'allocation' && allocationDisabled"
            :aria-selected="t === tab"
            @click="selectTab(t)"
          >{{ t.charAt(0).toUpperCase() + t.slice(1) }}</button>
        </nav>

        <p v-if="tab === 'overview'" data-testid="case8-independent-workspace-note">
          Case8 has no recorded spectral capability. Spectrum and Modal Validation use independent
          recorded experiments; the legacy Spectral Lab shortcut keeps their separate identity.
        </p>
        <button data-testid="tab-spectral" :aria-pressed="tab === 'spectral'" @click="selectTab('spectral')">
          Independent workspace: Spectrum / Modal Validation
        </button>

        <p v-if="allocationDisabled" class="exp__tab-reason" data-testid="allocation-disabled-reason">
          Allocation is not available for {{ configId }}: only D_u has a recorded terminal cumulative
          native-face map. Other configs do not have a cumulative spatial map saved — this is a known
          capability limit for this config, not a synthetic zero field.
        </p>
        <p v-else-if="tab === 'allocation'" class="exp__tab-note" data-testid="allocation-note">
          D_u FACE_FIELD is the recorded terminal cumulative native-face diagnostic (DIAGNOSTIC_RERUN).
          The Gate CELL_FIELD views (Acoustic / Pressure / Ungated) are frozen production cell maps.
          These are different scientific objects and are rendered separately.
        </p>
        <p v-else-if="tab === 'spectral'" class="exp__tab-note" data-testid="spectral-note">
          Independent Spectral Lab (not Case8 data): <strong>Selective modal response</strong> — the Re(λ) growth signature of the most
          unstable Fourier mode across four exact q_at configurations. This reports recorded spectral
          facts; it is not a spatial field.
        </p>

        <section class="exp__content" role="tabpanel" :aria-label="tab">
          <OverviewTab v-if="tab === 'overview' && overview.data" :overview="overview.data" :config-id="configId" />
          <FlowTab
            v-else-if="tab === 'flow'"
            :config-id="configId"
            v-model="snapshotIndex"
            v-model:field-id="fieldId"
          />
          <EntropyTab v-else-if="tab === 'entropy'" :config-id="configId" v-model="scalarStep" />
          <AllocationTab v-else-if="tab === 'allocation' && !allocationDisabled" :config-id="configId" />
          <MetricsTab v-else-if="tab === 'metrics'" :config-id="configId" />
          <SpectralTab v-else-if="tab === 'spectral'" />
          <EvidenceTab v-else-if="tab === 'evidence'" :config-id="configId" />
        </section>
      </template>
    </LoadStateBlock>

    <!-- Unknown experiment: a system-level fallback, not a business page -->
    <section v-if="overview?.state === 'MISSING'" data-testid="experiment-fallback">
      <h1>Unknown experiment</h1>
      <p>{{ overview.reason }}</p>
      <RouterLink :to="{ name: 'lab' }">← Back to Lab</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.exp { max-width: 62rem; margin: 0 auto; padding: 1.5rem; }
.exp__crumb { font-size: 0.82rem; color: #666; }
.exp__crumb a { color: #1a4f8a; text-decoration: none; }
.exp__crumb-current { font-weight: 600; color: #333; }
.exp__header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
.exp__header h1 { margin: 0.2rem 0; font-size: 1.5rem; }
.exp__subtitle { font-size: 0.85rem; color: #666; margin: 0; }
.exp__configs { display: flex; align-items: center; gap: 0.4rem; margin: 1rem 0; }
.exp__configs-label { font-size: 0.85rem; color: #555; }
.exp__config-btn { padding: 0.3rem 0.9rem; border: 1px solid #bbb; background: #fff; border-radius: 3px; cursor: pointer; font-size: 0.9rem; }
.exp__config-btn--active { background: #1a4f8a; color: #fff; border-color: #1a4f8a; font-weight: 600; }
.exp__tabs { display: flex; gap: 0.2rem; border-bottom: 2px solid #e0e0e0; }
.exp__tab { padding: 0.5rem 1rem; border: none; background: none; cursor: pointer; font-size: 0.9rem; color: #555; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.exp__tab--active { color: #1a4f8a; font-weight: 700; border-bottom-color: #1a4f8a; }
.exp__tab--disabled { color: #aaa; cursor: not-allowed; text-decoration: line-through; }
.exp__tab-reason { font-size: 0.82rem; color: #8a4b00; background: #fffaf0; border-left: 3px solid #d08700; padding: 0.45rem 0.7rem; margin-top: 0.8rem; }
.exp__tab-note { font-size: 0.82rem; color: #555; background: #f7f7f7; padding: 0.45rem 0.7rem; margin-top: 0.8rem; }
.exp__content { margin-top: 1rem; }
</style>
