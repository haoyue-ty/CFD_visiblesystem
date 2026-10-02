<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { cylinderService, dataService, createRequestGuard, type Loaded, type AllocationView } from '../../data'
import type { AllocationBundle, Science, Definitions } from '../../data/cylinder'
import { slotValue } from '../../data/cylinder'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'
import FaceAllocationView from '../../scientific/FaceAllocationView.vue'
import AllocationSummary from '../../scientific/AllocationSummary.vue'
import CanonicalMetrics from '../cylinder/CanonicalMetrics.vue'
import SectorAllocation from '../cylinder/SectorAllocation.vue'
import ResourceState from '../cylinder/ResourceState.vue'
const props = withDefaults(defineProps<{ guided?: boolean }>(), { guided: false })
const route = useRoute(), router = useRouter()
const caseConfigs = ['A_u', 'B_u', 'C_u', 'D_u'], cylinderConfigs = ['A_u', 'B_u', 'D_u']
const leftConfig = computed(() => !props.guided && typeof route.query.case8_config === 'string' && caseConfigs.includes(route.query.case8_config) ? route.query.case8_config : 'D_u')
const rightConfig = computed(() => !props.guided && typeof route.query.cylinder_config === 'string' && cylinderConfigs.includes(route.query.cylinder_config) ? route.query.cylinder_config : 'D_u')
function update(key: string, value: string) { router.push({ query: { ...route.query, case8_config: leftConfig.value, cylinder_config: rightConfig.value, [key]: value } }) }
const composite = ref<Loaded<{ comparison: Science['CrossFlowComparison']; definitions: Definitions }> | null>(null)
const native = ref<Loaded<AllocationView> | null>(null), angular = ref<Loaded<AllocationBundle> | null>(null)
const compositeGuard = createRequestGuard(), nativeGuard = createRequestGuard(), angularGuard = createRequestGuard()
const loading = () => ({ state: 'LOADING' as const, data: null, reason: null, origin: 'VERIFIED_PRODUCTION' as const })
watch([leftConfig, rightConfig], async ([left, right]) => {
  composite.value = loading()
  const result = await compositeGuard.run(signal => cylinderService.comparison(left, right, signal))
  if (result) composite.value = result
}, { immediate: true })
watch(leftConfig, async configId => {
  nativeGuard.cancel(); native.value = null
  if (configId !== 'D_u') return
  native.value = loading()
  const result = await nativeGuard.run(signal => dataService.describeAllocation({ experimentId: 'case8', configId }, signal))
  if (result) native.value = result
}, { immediate: true })
watch(rightConfig, async config => {
  angular.value = loading()
  const result = await angularGuard.run(signal => cylinderService.allocation(config, signal))
  if (result) angular.value = result
}, { immediate: true })
onBeforeUnmount(() => { compositeGuard.cancel(); nativeGuard.cancel(); angularGuard.cancel() })
const ruleLabels = ['Localization', 'HF', 'Width', 'Budget']
</script>
<template>
  <section data-testid="cross-flow-view" class="comparison">
    <h1>P07 · Case8 ↔ Cylinder Cross-flow Compare</h1>
    <aside class="policy" role="note"><strong data-testid="descriptive-only">DESCRIPTIVE ONLY · DESCRIPTIVE_ONLY</strong><br><strong data-testid="no-unified-ranking">NO UNIFIED RANKING · NO_UNIFIED_RANKING</strong><p>Same pathway, different allocation contexts, case-specific macroscopic response.</p></aside>
    <div v-if="!guided" class="selectors">
      <label>Case8 config <select data-testid="case8-config" :value="leftConfig" @change="update('case8_config', ($event.target as HTMLSelectElement).value)"><option v-for="id in caseConfigs" :key="id">{{ id }}</option></select></label>
      <label>Cylinder config <select data-testid="cylinder-config" :value="rightConfig" @change="update('cylinder_config', ($event.target as HTMLSelectElement).value)"><option v-for="id in cylinderConfigs" :key="id">{{ id }}</option></select></label>
    </div>
    <LoadStateBlock :loaded="composite" target="real API cross-flow comparison"><template v-if="composite?.data">
      <section data-testid="comparability-rules"><h2>Comparability Rules</h2><details :open="!guided"><summary>Independent definitions: localization, HF, width and budget</summary><article v-for="(rule, i) in composite.data.comparison.comparability" :key="rule.left_definition_id"><h3>{{ ruleLabels[i] }} → descriptive only</h3><p>{{ rule.status }} · {{ rule.left_definition_id }} ↔ {{ rule.right_definition_id }}</p><p>{{ rule.reason }}</p></article></details></section>
      <div class="sides">
        <section data-testid="case8-side"><h2>Case8 — {{ leftConfig }}</h2>
          <RouterLink :to="{ name: 'experiment', params: { experiment_id: 'case8' }, query: { source_scene: route.query.source_scene ?? (route.name === 'explore' ? '6' : undefined), explore_return: route.query.explore_return ?? (route.name === 'explore' ? JSON.stringify({ name: 'explore', query: route.query }) : undefined), config: leftConfig, tab: 'allocation' } }">Open Case8 detail</RouterLink>
          <h3>FACE_FIELD · Native-face cumulative allocation</h3>
          <ResourceState :resource="composite.data.comparison.left.allocation" label="Case8 native-face cumulative allocation">
            <LoadStateBlock :loaded="native" target="Case8 native-face arrays"><template v-if="native?.data?.representation_type === 'FACE_FIELD'">
              <p>{{ native.data.definition }} · {{ native.data.time_rule }} · {{ native.data.spatial_rule }}</p>
              <p>Mask: {{ native.data.mask.mask_id }} — {{ native.data.mask.definition }} · {{ native.data.data_origin }}</p>
              <div v-for="arr in native.data.arrays" :key="arr.array_id"><FaceAllocationView :array="arr" /><EvidenceLink v-for="id in native.data.evidence_refs" :key="id" :evidence-id="id" /></div>
              <AllocationSummary :summary="native.data.summary" />
              <EvidenceLink v-for="id in native.data.evidence_refs" :key="id" :evidence-id="id" />
            </template></LoadStateBlock>
          </ResourceState>
          <h3>Case8 local metrics / macroscopic response</h3>
          <ResourceState :resource="composite.data.comparison.left.metrics" label="Case8 local metrics"><CanonicalMetrics v-if="slotValue(composite.data.comparison.left.metrics)" :collection="slotValue(composite.data.comparison.left.metrics)!" :definitions="composite.data.definitions" :compact="guided" /></ResourceState>
          <h3>Case8 budget · native scope</h3>
          <ResourceState :resource="composite.data.comparison.left.budget" label="Case8 budget"><CanonicalMetrics v-if="slotValue(composite.data.comparison.left.budget)" :collection="slotValue(composite.data.comparison.left.budget)!" :definitions="composite.data.definitions" :compact="guided" /></ResourceState>
          <p>Case8 evidence: <EvidenceLink v-for="id in composite.data.comparison.left.evidence_refs" :key="id" :evidence-id="id" /></p>
        </section>
        <section data-testid="cylinder-side"><h2>Cylinder — {{ rightConfig }}</h2>
          <RouterLink :to="{ name: 'experiment', params: { experiment_id: 'cylinder' }, query: { source_scene: route.query.source_scene ?? (route.name === 'explore' ? '6' : undefined), explore_return: route.query.explore_return ?? (route.name === 'explore' ? JSON.stringify({ name: 'explore', query: route.query }) : undefined), config: rightConfig, tab: 'sectors' } }">Open Cylinder detail</RouterLink>
          <LoadStateBlock :loaded="angular" target="Cylinder angular sectors and front-band"><SectorAllocation v-if="angular?.data" :bundle="angular.data" /></LoadStateBlock>
          <h3>Cylinder local metrics / macroscopic response</h3>
          <ResourceState :resource="composite.data.comparison.right.metrics" label="Cylinder local metrics"><CanonicalMetrics v-if="slotValue(composite.data.comparison.right.metrics)" :collection="slotValue(composite.data.comparison.right.metrics)!" :definitions="composite.data.definitions" :compact="guided" /></ResourceState>
          <h3>Cylinder budget · interior-only</h3>
          <ResourceState :resource="composite.data.comparison.right.budget" label="Cylinder budget"><CanonicalMetrics v-if="slotValue(composite.data.comparison.right.budget)" :collection="slotValue(composite.data.comparison.right.budget)!" :definitions="composite.data.definitions" :compact="guided" /></ResourceState>
          <p>Cylinder evidence: <EvidenceLink v-for="id in composite.data.comparison.right.evidence_refs" :key="id" :evidence-id="id" /></p>
        </section>
      </div>
      <section data-testid="cross-flow-limitations"><h2>Limitations</h2><p>Macroscopic response retains each case's canonical Metrics, units, detectors and time scopes. No browser-derived ratios or shared score.</p><p v-for="limitation in composite.data.comparison.limitations" :key="limitation.id">{{ limitation.code }} — {{ limitation.description }}</p><EvidenceLink v-for="id in composite.data.comparison.evidence_refs" :key="id" :evidence-id="id" /></section>
    </template></LoadStateBlock>
  </section>
</template>
<style scoped>.comparison { padding: 1.5rem; max-width: 95rem; margin: auto; } .policy { border: 2px solid #8a4b00; padding: 1rem; background: #fffaf0; } .selectors { display: flex; flex-wrap: wrap; gap: 2rem; margin: 1rem 0; } .sides { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 2rem; } .sides > section { min-width: 0; border: 1px solid #ddd; padding: 1rem; } article { border-bottom: 1px solid #ddd; } @media(max-width: 850px) { .sides { grid-template-columns: 1fr; } }</style>
