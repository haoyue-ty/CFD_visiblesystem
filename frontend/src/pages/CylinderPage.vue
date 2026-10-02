<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { cylinderService, createRequestGuard, type Loaded } from '../data'
import type { Science, AllocationBundle, HistoryBundle, MetricsBundle, FieldBundle } from '../data/cylinder'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import ExploreReturn from '../components/ExploreReturn.vue'
import EvidenceLink from '../scientific/EvidenceLink.vue'
import SectorAllocation from '../views/cylinder/SectorAllocation.vue'
import ScalarHistory from '../views/cylinder/ScalarHistory.vue'
import CanonicalMetrics from '../views/cylinder/CanonicalMetrics.vue'
import InstantaneousField from '../views/cylinder/InstantaneousField.vue'
import ResourceState from '../views/cylinder/ResourceState.vue'

const route = useRoute(), router = useRouter()
const configs = ['A_u', 'B_u', 'D_u']
const tabs = { overview: 'Overview', flow: 'Flow', entropy: 'Entropy', sectors: 'Sector Allocation', metrics: 'Metrics', evidence: 'Evidence' }
const config = computed(() => typeof route.query.config === 'string' && configs.includes(route.query.config) ? route.query.config : 'D_u')
const tab = computed(() => typeof route.query.tab === 'string' && route.query.tab in tabs ? route.query.tab as keyof typeof tabs : 'overview')
const snapshot = computed(() => Number(route.query.snapshot ?? 1))
const fieldId = computed(() => typeof route.query.field === 'string' ? route.query.field : 'radial_interior_pi_at')
const step = computed({ get: () => { const n = Number(route.query.step ?? 9757); return Number.isInteger(n) && n >= 1 && n <= 9757 ? n : 9757 }, set: value => update({ step: String(value) }) })
function update(patch: Record<string, string>) { router.push({ query: { ...route.query, config: config.value, tab: tab.value, ...patch } }) }

const frames = ref<Loaded<Science['SnapshotIndex']> | null>(null)
const allocation = ref<Loaded<AllocationBundle> | null>(null)
const history = ref<Loaded<HistoryBundle> | null>(null)
const metrics = ref<Loaded<MetricsBundle> | null>(null)
const field = ref<Loaded<FieldBundle> | null>(null)
const frameGuard = createRequestGuard(), allocationGuard = createRequestGuard(), contentGuard = createRequestGuard(), fieldGuard = createRequestGuard()
const loading = () => ({ state: 'LOADING' as const, data: null, reason: null, origin: 'VERIFIED_PRODUCTION' as const })
const selected = computed(() => frames.value?.data?.items.find(s => s.snapshot_index === snapshot.value))
const fieldOptions = computed(() => [...new Set([fieldId.value, 'density', ...(selected.value?.fields.map(f => f.field_id) ?? [])])])
watch(config, async value => {
  frames.value = loading()
  const result = await frameGuard.run(signal => cylinderService.snapshots(value, signal))
  if (result) frames.value = result
}, { immediate: true })
watch(config, async value => {
  allocation.value = loading()
  const result = await allocationGuard.run(signal => cylinderService.allocation(value, signal))
  if (result) allocation.value = result
}, { immediate: true })
watch([config, tab], async ([value, current]) => {
  contentGuard.cancel(); history.value = null; metrics.value = null
  if (current === 'entropy') {
    history.value = loading()
    const result = await contentGuard.run(signal => cylinderService.history(value, signal))
    if (result) history.value = result
  } else if (current === 'metrics') {
    metrics.value = loading()
    const result = await contentGuard.run(signal => cylinderService.metrics(value, signal))
    if (result) metrics.value = result
  }
}, { immediate: true })
watch([config, tab, snapshot, fieldId, selected], async () => {
  fieldGuard.cancel(); field.value = null
  if (tab.value !== 'flow' || !selected.value) return
  if (!selected.value.fields.some(f => f.field_id === fieldId.value)) {
    field.value = { state: 'MISSING', data: null, reason: `No saved instantaneous ${fieldId.value} field in this snapshot.`, origin: 'VERIFIED_PRODUCTION' }
    return
  }
  field.value = loading()
  const result = await fieldGuard.run(signal => cylinderService.field(config.value, snapshot.value, fieldId.value, signal))
  if (result) field.value = result
}, { immediate: true })
onBeforeUnmount(() => { frameGuard.cancel(); allocationGuard.cancel(); contentGuard.cancel(); fieldGuard.cancel() })
</script>
<template>
  <main data-page="cylinder" class="cylinder">
    <ExploreReturn />
    <nav><RouterLink to="/lab">Lab</RouterLink> → Cylinder</nav>
    <h1>Cylinder Experiment Detail — {{ config }}</h1>
    <p>REAL API · saved native instantaneous fields, accepted-step scalar history and trajectory-integrated allocation.</p>
    <div role="group" aria-label="Cylinder config"><button v-for="id in configs" :key="id" :data-testid="`config-${id}`" :aria-pressed="id === config" @click="update({ config: id })">{{ id }}</button></div>
    <nav role="tablist" aria-label="Cylinder tabs"><button v-for="(label, id) in tabs" :key="id" role="tab" :aria-selected="tab === id" :data-testid="`tab-${id}`" @click="update({ tab: id })">{{ label }}</button></nav>
    <RouterLink :to="{ name: 'cross-flow', query: { case8_config: 'D_u', cylinder_config: config } }">Case8 ↔ Cylinder · Cross-flow Compare</RouterLink>
    <aside data-testid="cylinder-capability-gap"><LoadStateBlock :loaded="allocation" target="Cylinder cumulative 2D capability"><ResourceState v-if="allocation?.data" :resource="allocation.data.overview.cumulative_2d" label="Full trajectory cumulative 2D Pi_at" /></LoadStateBlock></aside>
    <section role="tabpanel" :aria-label="tabs[tab]">
      <template v-if="tab === 'overview'">
        <h2>Supported observations</h2>
        <LoadStateBlock :loaded="frames" target="Cylinder snapshots"><p v-if="frames?.data">{{ frames.data.snapshot_count }} recorded snapshots · 9757 accepted-step scalar records per series · 16 angular sectors + fixed cumulative front-band.</p></LoadStateBlock>
        <p>Interior-only cumulative budget excludes wall and far-field boundary flux. Instantaneous Pi face diagnostics are distinct from trajectory-integrated sectors.</p>
        <LoadStateBlock :loaded="allocation" target="Cylinder allocation capability"><template v-if="allocation?.data">
          <p>No cumulative 2D map is supplied by sectors or instantaneous fields.</p>
          <EvidenceLink v-for="id in allocation.data.overview.evidence_refs" :key="id" :evidence-id="id" />
        </template></LoadStateBlock>
      </template>
      <template v-else-if="tab === 'flow'">
        <h2>Recorded instantaneous fields</h2>
        <p>No primitive density movie is saved. Native face sample arrays render directly, without interpolated frames.</p>
        <LoadStateBlock :loaded="frames" target="Cylinder snapshot index"><template v-if="frames?.data">
          <label>Snapshot selector <select data-testid="snapshot-selector" :value="snapshot" @change="update({ snapshot: ($event.target as HTMLSelectElement).value })"><option v-for="s in frames.data.items" :key="s.snapshot_index" :value="s.snapshot_index">Snapshot {{ s.snapshot_index }} · completed step {{ s.step_index }} · t={{ s.physical_time }}</option></select></label>
          <p v-if="!selected" role="alert">Invalid snapshot selector: only recorded indices 1…5 are supported.</p>
          <template v-else>
            <p data-testid="snapshot-meta">snapshot index={{ selected.snapshot_index }} · completed step={{ selected.step_index }} · physical time={{ selected.physical_time }}</p>
            <p data-testid="field-availability">Field availability: {{ selected.fields.map(f => `${f.field_id}: ${f.result.availability}`).join('; ') }} · density: Missing · pressure: Missing</p>
            <label>Field <select data-testid="field-selector" :value="fieldId" @change="update({ field: ($event.target as HTMLSelectElement).value })"><option v-for="id in fieldOptions" :key="id" :value="id">{{ id }}{{ selected.fields.some(f => f.field_id === id) ? '' : ' — Missing' }}</option></select></label>
            <LoadStateBlock :loaded="field" target="instantaneous field"><InstantaneousField v-if="field?.data" :bundle="field.data" /></LoadStateBlock>
            <EvidenceLink v-for="id in selected.result.provenance.evidence_refs" :key="id" :evidence-id="id" />
          </template>
        </template></LoadStateBlock>
      </template>
      <LoadStateBlock v-else-if="tab === 'entropy'" :loaded="history" target="9757-step history"><ScalarHistory v-if="history?.data" :bundle="history.data" v-model:step="step" /></LoadStateBlock>
      <LoadStateBlock v-else-if="tab === 'sectors'" :loaded="allocation" target="sector allocation"><SectorAllocation v-if="allocation?.data" :bundle="allocation.data" /></LoadStateBlock>
      <LoadStateBlock v-else-if="tab === 'metrics'" :loaded="metrics" target="Cylinder local metrics"><CanonicalMetrics v-if="metrics?.data" :collection="metrics.data.collection" :definitions="metrics.data.definitions" /></LoadStateBlock>
      <section v-else-if="tab === 'evidence'"><h2>Evidence</h2><p v-for="suffix in ['protocol', 'snapshots', 'history', 'sectors', 'front-band', 'metrics']" :key="suffix">{{ suffix }}: <EvidenceLink :evidence-id="`ev.cylinder.${config}.${suffix}`" /></p><p>Full trajectory cumulative 2D Pi_at: <EvidenceLink evidence-id="ev.missing.cylinder-cumulative2d" /></p></section>
    </section>
  </main>
</template>
<style scoped>.cylinder { max-width: 68rem; margin: auto; padding: 1.5rem; } nav, [role=group] { margin: .8rem 0; display: flex; flex-wrap: wrap; gap: .5rem; } button { padding: .4rem .8rem; } button[aria-selected=true], button[aria-pressed=true] { font-weight: bold; border: 2px solid #1a4f8a; } section { margin-top: 1rem; } select { max-width: 100%; }</style>
