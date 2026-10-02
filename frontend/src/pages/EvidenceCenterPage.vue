<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createRequestGuard, type Loaded } from '../data'
import { evidenceService, factText, knownValue, verificationLabels, type EvidenceIndex, type EvidenceQuery } from '../data/evidence'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import EvidenceStatus from '../views/evidence/EvidenceStatus.vue'
const route = useRoute(), router = useRouter(), guard = createRequestGuard()
const index = ref<Loaded<EvidenceIndex> | null>(null)
const sections = ['CURRENT', 'GAPS', 'HISTORY'] as const
const section = computed(() => sections.find(s => s === route.query.section) ?? 'CURRENT')
const experiments = ['case8', 'gate', 'spectrum', 'modal-validation', 'cylinder', 'entropy-closure', 'mechanism']
const statuses = ['FROZEN_VERIFIED', 'VERIFIED_NOT_FROZEN', 'DERIVED_VERIFIED', 'AVAILABLE_UNVERIFIED', 'PARTIAL', 'MISSING', 'LEGACY', 'SUPERSEDED', 'NOT_APPLICABLE'] as const
const experiment = computed(() => experiments.includes(String(route.query.experiment)) ? String(route.query.experiment) : '')
const status = computed(() => statuses.find(s => s === route.query.status))
const drift = computed(() => ['TRUE', 'FALSE', 'UNKNOWN'].includes(String(route.query.drift)) ? String(route.query.drift) : '')
const offset = computed(() => { const n = Number(route.query.offset ?? 0); return Number.isSafeInteger(n) && n >= 0 ? n : 0 })
const limit = 20
// Display labels for the accepted, registered gaps; no data is manufactured.
const gapTitles: Record<string, string> = {
  'ev.missing.cylinder-cumulative2d': 'Cylinder cumulative 2D',
  'ev.inventory.missing_near1d_raw_epsilon_scan': 'Near-1D five-epsilon authoritative raw',
  'ev.inventory.missing_persisted_jacobian_fourier_blocks': 'Spectrum serialized matrices',
}
const gapScope: Record<string, { affects: string; independent: string }> = {
  'ev.missing.cylinder-cumulative2d': { affects: 'Full-trajectory cumulative 2D Pi_at is unavailable.', independent: 'Selected J2C formal v2 cumulative angular sectors and fixed-band scalars remain separate recorded objects.' },
  'ev.inventory.missing_near1d_raw_epsilon_scan': { affects: 'Authoritative numerical verification across five epsilon amplitudes is unavailable.', independent: 'Theoretical schematic explanations and independently registered spectral results retain their own scope; manuscript-transcribed values do not verify the missing scan.' },
  'ev.inventory.missing_persisted_jacobian_fourier_blocks': { affects: 'Inspection of serialized full Jacobian/Fourier matrices is unavailable.', independent: 'Recorded spectra, eigenpairs, base state, verification and construction-code evidence exist separately.' },
}
const query = computed<EvidenceQuery>(() => ({ section: section.value, experiment_id: experiment.value || undefined, status: status.value, offset: offset.value, limit }))
const visible = computed(() => (index.value?.data?.items ?? []).filter(item => !drift.value || (knownValue(item.source_drift) === null ? 'UNKNOWN' : knownValue(item.source_drift) ? 'TRUE' : 'FALSE') === drift.value))
async function load() {
  index.value = null
  const result = await guard.run(signal => evidenceService.index(query.value, signal))
  if (result) index.value = result
}
watch(query, load, { immediate: true })
onBeforeUnmount(() => guard.cancel())
function set(key: string, value: string) { void router.push({ query: { ...route.query, [key]: value || undefined, offset: key === 'drift' ? route.query.offset : undefined } }) }
function page(next: number) { void router.push({ query: { ...route.query, offset: String(next) } }) }
</script>
<template>
  <main class="center" data-page="evidence-center">
    <h1>Evidence Center</h1>
    <p>Inspect result identity, method, source, freeze and scientific limits.</p>
    <nav aria-label="Evidence sections" class="sections">
      <button v-for="s in sections" :key="s" :aria-current="section === s ? 'page' : undefined" :data-testid="`section-${s}`" @click="set('section', s)">{{ s }}</button>
    </nav>
    <section :data-testid="`evidence-${section}`" :class="{ history: section === 'HISTORY' }">
      <h2>{{ section }}</h2>
      <p v-if="section === 'CURRENT'">Current accepted evidence selection. Verification and drift are independent facts.</p>
      <p v-else-if="section === 'GAPS'">Known scientific gaps. Missing data remains missing; this center does not generate or fill scientific sources.</p>
      <p v-else role="note"><strong>HISTORICAL RECORDS — legacy, superseded and nonselected sources. These are not current formal results.</strong></p>
      <div class="filters">
        <label>Experiment <select :value="experiment" data-testid="evidence-experiment-filter" @change="set('experiment', ($event.target as HTMLSelectElement).value)"><option value="">All experiments</option><option v-for="id in experiments" :key="id" :value="id">{{ id }}</option></select></label>
        <label>Verification <select :value="status ?? ''" data-testid="evidence-status-filter" @change="set('status', ($event.target as HTMLSelectElement).value)"><option value="">All verification states</option><option v-for="s in statuses" :key="s" :value="s">{{ verificationLabels[s] }} · Source: {{ s }}</option></select></label>
        <label>Source drift (this page) <select :value="drift" data-testid="evidence-drift-filter" @change="set('drift', ($event.target as HTMLSelectElement).value)"><option value="">All drift states</option><option>TRUE</option><option>FALSE</option><option>UNKNOWN</option></select></label>
      </div>
      <p class="note">Experiment, verification and section filter on EVI01 before pagination. The frozen API has no drift query: source drift filters the current server page only. Next / Previous inspect other pages; no complete-registry load.</p>
      <LoadStateBlock :loaded="index" target="evidence index">
        <template v-if="index?.data">
          <p data-testid="evidence-page-range">Server records {{ index.data.page.returned_count ? offset + 1 : 0 }}–{{ offset + index.data.page.returned_count }} of {{ index.data.page.total_count }} · {{ visible.length }} displayed</p>
          <p v-if="!visible.length" data-testid="evidence-empty">No evidence matches on this server page.</p>
          <article v-for="item in visible" :key="item.evidence_id" class="card" data-testid="evidence-card">
            <h3>{{ gapTitles[item.evidence_id] ?? item.title }}</h3>
            <p v-if="gapTitles[item.evidence_id]">{{ item.title }}</p>
            <p><strong>Experiment:</strong> {{ factText(item.experiment_id) }} · <strong>Result count:</strong> {{ item.result_ids.length }}</p>
            <p>Registered result/config identities: {{ item.result_ids.join(', ') || 'No numerical result / config binding in index' }}</p>
            <strong v-if="section === 'HISTORY'">HISTORY — outside current formal selection</strong>
            <EvidenceStatus :verification="item.verification" :drift="item.source_drift" />
            <p><strong>Main limitation:</strong> {{ item.limitations[0]?.description ?? 'No limitation recorded in index; inspect full scope.' }}</p>
            <template v-if="section === 'GAPS'">
              <p><strong>Why missing / limited:</strong> {{ item.limitations.map(l => l.description).join('; ') || item.verification.basis.join('; ') }}</p>
              <p><strong>Affects:</strong> {{ gapScope[item.evidence_id]?.affects ?? (item.limitations.flatMap(l => l.affected_refs).join(', ') || item.result_ids.join(', ') || 'This registered missing source; broader impact is not established.') }}</p>
              <p><strong>Does not affect:</strong> {{ gapScope[item.evidence_id]?.independent ?? 'This gap alone does not invalidate separately verified records with independent dependencies. Exact unaffected results are not enumerated by this record.' }}</p>
            </template>
            <RouterLink :to="{ name: 'evidence', params: { evidence_id: item.evidence_id }, query: { selection: section, back: JSON.stringify({ name: 'evidence-center', query: route.query }) } }">View details →</RouterLink>
          </article>
          <nav aria-label="Evidence pagination" class="pagination">
            <button data-testid="evidence-previous" :disabled="offset === 0" @click="page(Math.max(0, offset - limit))">Previous</button>
            <button data-testid="evidence-next" :disabled="!index.data.page.has_more" @click="page(offset + limit)">Next</button>
          </nav>
        </template>
      </LoadStateBlock>
      <button v-if="index?.state === 'ERROR'" @click="load">Retry evidence index</button>
    </section>
    <p>Evidence records can remain inspectable even when source-data drift blocks a scientific result. Inspectability does not mean Numerical Result Available.</p>
  </main>
</template>
<style scoped>
.center { max-width: 70rem; margin: auto; padding: 1.5rem; } .sections, .filters, .pagination { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
.sections button { padding: .65rem 1rem; } [aria-current="page"] { font-weight: bold; border: 2px solid #1a4f8a; }
.card { border: 1px solid #ccc; padding: 1rem; margin: .75rem 0; overflow-wrap: anywhere; } .card h3 { margin-top: 0; }
.history { border-left: .4rem solid #775936; padding-left: 1rem; background: #f8f5ef; } .note { font-size: .85rem; color: #555; }
</style>
