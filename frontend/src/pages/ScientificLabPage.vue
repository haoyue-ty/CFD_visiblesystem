<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../services/api'
import type { components } from '../types/generated/api'
import { createRequestGuard, type Loaded } from '../data'
import ExploreReturn from '../components/ExploreReturn.vue'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import EvidenceLink from '../scientific/EvidenceLink.vue'
import GateComparisonView from '../views/case8/GateComparisonView.vue'
import SpectralTab from '../views/case8/SpectralTab.vue'
const props = defineProps<{ experiment_id: string }>()
const route = useRoute(), router = useRouter(), guard = createRequestGuard()
type Experiment = components['schemas']['Experiment']
const overview = ref<Loaded<Experiment> | null>(null)
const tabs = computed(() => overview.value?.data?.capabilities.filter(c => c.tab_policy.visible_for_family).map(c => c.tab_policy.tab_id) ?? [])
const tab = computed(() => typeof route.query.tab === 'string' ? route.query.tab : props.experiment_id === 'gate' ? 'allocation' : props.experiment_id === 'modal-validation' ? 'validation' : 'spectrum')
const unsupported = computed(() => !tabs.value.includes(tab.value))
watch(() => props.experiment_id, async id => {
  overview.value = { state: 'LOADING', data: null, reason: null, origin: 'VERIFIED_PRODUCTION' }
  const loaded = await guard.run(async signal => {
    try {
      const response = await api.GET('/api/v1/experiments/{experiment_id}', { params: { path: { experiment_id: id } }, signal })
      if (response.data && response.response.ok && 'data' in response.data) return { state: 'READY' as const, data: response.data.data, reason: null, origin: 'VERIFIED_PRODUCTION' as const }
      return { state: response.error?.availability === 'MISSING' ? 'MISSING' as const : response.error?.availability === 'UNSUPPORTED' ? 'UNSUPPORTED' as const : 'ERROR' as const, data: null, reason: response.error?.error.message ?? 'Experiment metadata unavailable', origin: 'VERIFIED_PRODUCTION' as const }
    } catch (error) {
      if ((error as Error).name === 'AbortError') throw error
      return { state: 'ERROR' as const, data: null, reason: String(error), origin: 'VERIFIED_PRODUCTION' as const }
    }
  })
  if (loaded) overview.value = loaded
}, { immediate: true })
onBeforeUnmount(() => guard.cancel())
</script>
<template>
  <main data-page="scientific-lab" class="science-lab">
    <ExploreReturn /><RouterLink to="/lab">Lab</RouterLink>
    <h1>{{ experiment_id === 'gate' ? 'Gate Allocation' : experiment_id === 'modal-validation' ? 'Modal Validation' : 'Spectral Lab' }}</h1>
    <LoadStateBlock :loaded="overview" target="experiment capability metadata">
      <nav role="tablist" :aria-label="`${experiment_id} tabs`"><button v-for="id in tabs" :key="id" role="tab" :data-testid="`tab-${id}`" :aria-selected="tab === id" @click="router.push({ query: { ...route.query, tab: id } })">{{ id.charAt(0).toUpperCase() + id.slice(1) }}</button></nav>
      <p v-if="unsupported" data-testid="unsupported-tab" role="alert">UNSUPPORTED — {{ tab }} is not a capability of {{ experiment_id }}. Requested location retained.</p>
      <section v-else role="tabpanel" :aria-label="tab">
        <template v-if="tab === 'overview'"><p>{{ overview?.data?.description }}</p><p>Flow and entropy histories are not capabilities of this experiment family. The recorded scientific workspace remains separate from Case8.</p><p v-if="experiment_id === 'spectrum'">Spectrum serialized matrices: MISSING.</p><p v-if="experiment_id === 'modal-validation'">Linear/RK3 amplitude histories: MISSING. Recorded growth rates and CFD projected amplitude are available.</p></template>
        <template v-else-if="tab === 'evidence'"><EvidenceLink v-for="id in overview?.data?.evidence_refs" :key="id" :evidence-id="id" /></template>
        <GateComparisonView v-else-if="experiment_id === 'gate'" />
        <SpectralTab v-else />
      </section>
    </LoadStateBlock>
  </main>
</template>
<style scoped>.science-lab { padding: 1.5rem; max-width: 90rem; margin: auto; } nav { display: flex; gap: .5rem; margin: 1rem 0; } button[aria-selected=true] { font-weight: bold; }</style>
