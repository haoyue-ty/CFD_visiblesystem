<script setup lang="ts">
/**
 * Case8 / Gate Allocation tab — Phase 6B Window 4.
 *
 * WHAT THIS TAB IS
 *   Cumulative spatial entropy allocation: where the time-integrated entropy
 *   production sits in space. It is NOT a snapshot and NOT a time history; both
 *   fields are cumulative over the frozen trajectory.
 *
 * TWO DIFFERENT SCIENTIFIC OBJECTS (the central constraint)
 *   The tab can show exactly two representations and never conflates them:
 *
 *     Case8 D_u  FACE_FIELD   native x/y normal faces, shapes [32,129] and
 *                             [32,128], two independent mask counts, spatial
 *                             measure NOT yet applied (dy/dx still required).
 *     Gate *     CELL_FIELD   one [32,128] cell-centre field, one mask, spatial
 *                             measure ALREADY applied (sum(cells)).
 *
 *   They are rendered by two separate components (FaceAllocationView /
 *   CellAllocationView). The FACE view draws each orientation as its own figure
 *   at its own native shape and never averages the two orientations into a cell
 *   field. Because `representation_type` is the discriminant, TypeScript will not
 *   let the template send a cell field through the face renderer or vice versa.
 *
 * PROVENANCE
 *   `representation_type`, `mask`, `definition`, `verification` and `evidence`
 *   are shown as explicit, dedicated blocks — not as decoration. The mock banner
 *   is always visible while the mock provider is active.
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { activeProvider, dataService, createRequestGuard, type Loaded, type AllocationSelector } from '../../data'
import type { AllocationView } from '../../data/domain'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import MockBadge from '../../components/MockBadge.vue'
import FaceAllocationView from '../../scientific/FaceAllocationView.vue'
import CellAllocationView from '../../scientific/CellAllocationView.vue'
import AllocationSummary from '../../scientific/AllocationSummary.vue'
import GateComparisonView from './GateComparisonView.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'

const props = defineProps<{ configId: string }>()
const route = useRoute()
const router = useRouter()

/** The allocation "family" this tab can display. Both are read via one provider. */
type Family = 'case8' | 'gate'
const GATE_CONFIGS = ['Acoustic', 'Pressure', 'Ungated'] as const

/**
 * The Case8 face view is tied to the page config (only D_u has a map); the Gate
 * cell view is an independent family with its own three matched configurations.
 * Keeping two selectors means switching the Gate variant never has to pretend to
 * be a Case8 config change.
 */
const family = ref<Family>(route.query.allocation_family === 'gate' ? 'gate' : 'case8')
const gateConfig = ref<string>(GATE_CONFIGS.find(c => c === route.query.allocation_gate) ?? 'Acoustic')
const returnTo = computed(() => ({ name: 'experiment', params: route.params, query: { ...route.query } }))

const showComparison = ref(route.query.allocation_comparison === 'true')
const allocation = ref<Loaded<AllocationView> | null>(null)
const guard = createRequestGuard()

/** Case8 face allocation only exists for D_u; other configs are a known gap. */
const case8Available = computed(() => props.configId === 'D_u')

const selector = computed<AllocationSelector>(() =>
  family.value === 'case8' ? { experimentId: 'case8', configId: props.configId } : { experimentId: 'gate', configId: gateConfig.value },
)

async function load() {
  allocation.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await guard.run((signal) => dataService.describeAllocation(selector.value, signal))
  if (result) allocation.value = result
}

onMounted(load)
onBeforeUnmount(() => guard.cancel())
watch(selector, load, { deep: true })
// Persist local controls on the result's actual history entry, so browser Back
// restores the same family/gate/comparison as the explicit return link.
watch([family, gateConfig, showComparison], () => {
  if (route.name !== 'experiment' || route.query.tab !== 'allocation') return
  const query = { ...route.query, allocation_family: family.value, allocation_gate: gateConfig.value,
    allocation_comparison: showComparison.value ? 'true' : undefined }
  if (router.resolve({ query }).fullPath !== route.fullPath) void router.replace({ query })
}, { immediate: true })
watch(() => route.query, query => {
  if (route.name !== 'experiment' || query.tab !== 'allocation') return
  family.value = query.allocation_family === 'gate' ? 'gate' : 'case8'
  gateConfig.value = GATE_CONFIGS.find(c => c === query.allocation_gate) ?? 'Acoustic'
  showComparison.value = query.allocation_comparison === 'true'
})
// Selecting a config without a Case8 map while the Case8 family is active must
// fall back to the Gate family rather than showing an unexplained blank.
watch(() => props.configId, () => {
  if (family.value === 'case8' && !case8Available.value) family.value = 'gate'
})
</script>

<template>
  <section class="al" data-testid="case8-allocation">
    <button @click="showComparison = !showComparison">{{ showComparison ? 'Close' : 'Open' }} matched Gate comparison</button>
    <GateComparisonView v-if="showComparison" />
    <p class="al__intro">
      Cumulative spatial allocation of the time-integrated entropy production. Both views are
      trajectory-integrated (not snapshots, not time histories). The two representations below are
      <strong>different scientific objects</strong>: native faces vs integrated cells.
    </p>

    <!-- Family switch: Case8 native faces vs Gate integrated cells -->
    <div class="al__family" role="group" aria-label="Allocation representation family">
      <span class="al__family-label">Representation:</span>
      <button
        class="al__fam-btn"
        :class="{ 'al__fam-btn--active': family === 'case8' }"
        data-testid="alloc-family-face"
        :aria-pressed="family === 'case8'"
        @click="family = 'case8'"
      >Case8 · FACE_FIELD</button>
      <button
        class="al__fam-btn"
        :class="{ 'al__fam-btn--active': family === 'gate' }"
        data-testid="alloc-family-cell"
        :aria-pressed="family === 'gate'"
        @click="family = 'gate'"
      >Gate · CELL_FIELD</button>
    </div>

    <!-- Gate variant selector (only meaningful for the cell family) -->
    <div v-if="family === 'gate'" class="al__gate" role="group" aria-label="Gate config">
      <span class="al__family-label">Gate config:</span>
      <button
        v-for="g in GATE_CONFIGS"
        :key="g"
        class="al__fam-btn"
        :class="{ 'al__fam-btn--active': g === gateConfig }"
        :data-testid="`alloc-gate-${g}`"
        :aria-pressed="g === gateConfig"
        @click="gateConfig = g"
      >{{ g }}</button>
    </div>

    <!-- Case8 config that has no recorded map -->
    <p v-if="family === 'case8' && !case8Available" class="al__gap" data-testid="alloc-case8-gap">
      {{ configId }} has no recorded cumulative native-face map — only D_u does. This is a known
      capability gap for this config, not a synthetic zero field.
    </p>

    <LoadStateBlock :loaded="allocation" target="allocation">
      <div v-if="allocation?.data" class="al__body" :data-representation="allocation.data.representation_type">
        <MockBadge :origin="allocation.data.data_origin" :verification="allocation.data.verification.status" />

        <!-- representation_type: the discriminator, stated in words -->
        <dl class="al__facts">
          <div>
            <dt>representation_type</dt>
            <dd data-testid="alloc-representation-type">{{ allocation.data.representation_type }}</dd>
          </div>
          <div>
            <dt>measure definition</dt>
            <dd data-testid="alloc-measure-definition">{{ allocation.data.measure_definition }}</dd>
          </div>
          <div>
            <dt>semantic id</dt>
            <dd data-testid="alloc-semantic-id">{{ allocation.data.semantic_id }}</dd>
          </div>
          <div>
            <dt>data_origin</dt>
            <dd data-testid="alloc-data-origin">{{ allocation.data.data_origin }}</dd>
          </div>
          <div>
            <dt>experiment / config</dt>
            <dd data-testid="alloc-identity">{{ allocation.data.experiment_id }} / {{ allocation.data.config_id }}</dd>
          </div>
        </dl>

        <!-- definition -->
        <section class="al__block" data-testid="alloc-definition">
          <h3>Definition</h3>
          <p>{{ allocation.data.definition }}</p>
          <p class="al__sub"><strong>Title:</strong> {{ allocation.data.title }}</p>
          <p class="al__sub"><strong>Time rule:</strong> {{ allocation.data.time_rule }}</p>
          <p class="al__sub"><strong>Spatial rule:</strong> {{ allocation.data.spatial_rule }}</p>
          <p class="al__sub"><strong>Coordinate convention:</strong> {{ allocation.data.coordinate_convention }}</p>
        </section>

        <!-- mask (separate identity per representation; never shared) -->
        <section class="al__block" data-testid="alloc-mask">
          <h3>Mask</h3>
          <dl class="al__facts">
            <div>
              <dt>mask_id</dt>
              <dd data-testid="alloc-mask-id">{{ allocation.data.mask.mask_id }}</dd>
            </div>
            <div>
              <dt>mask_type</dt>
              <dd data-testid="alloc-mask-type">{{ allocation.data.mask.mask_type }}</dd>
            </div>
            <div>
              <dt>mask counts</dt>
              <dd data-testid="alloc-mask-counts">{{ allocation.data.mask.counts.join(', ') }}</dd>
            </div>
          </dl>
          <p class="al__sub">{{ allocation.data.mask.definition }}</p>
        </section>

        <!-- verification: its own layer, never merged with provenance or limits -->
        <section class="al__block" data-testid="alloc-verification">
          <h3>Verification</h3>
          <p>status: <strong>{{ allocation.data.verification.status }}</strong></p>
          <ul class="al__list">
            <li v-for="(basis, i) in allocation.data.verification.basis" :key="i">{{ basis }}</li>
          </ul>
          <p v-if="allocation.data.limitations.length" class="al__sub">
            Limitations:
            <span v-for="lim in allocation.data.limitations" :key="lim.id" class="al__lim">{{ lim.code }}</span>
          </p>
        </section>

        <!-- evidence -->
        <section class="al__block" data-testid="alloc-evidence">
          <h3>Evidence</h3>
          <ul class="al__ev-list">
            <li v-for="ref in allocation.data.evidence_refs" :key="ref" data-testid="alloc-evidence-link">
              <EvidenceLink :evidence-id="ref" context="allocation" :return-to="returnTo" />
              <span class="al__ev-id">{{ ref }}</span>
            </li>
          </ul>
        </section>

        <!-- summary -->
        <AllocationSummary :summary="allocation.data.summary" />

        <!-- the map(s): two DIFFERENT renderers, chosen by the discriminated union -->
        <section class="al__map" data-testid="allocation-map">
          <h3>Allocation map</h3>
          <template v-if="allocation.data.representation_type === 'FACE_FIELD'">
            <p class="al__note" data-testid="alloc-face-note">
              Native faces are shown as two separate figures. x-normal and y-normal arrays have
              different shapes and different sample planes; they are never summed into one cell field.
            </p>
            <div class="al__map-grid">
              <FaceAllocationView
                v-for="(arr) in allocation.data.arrays"
                :key="arr.array_id"
                :array="arr"

              />
            </div>
          </template>
          <template v-else>
            <p class="al__note" data-testid="alloc-cell-note">
              A single cell-centre field. Each value already includes the spatial measure, so it is
              not a downsampled face field.
            </p>
            <div class="al__map-grid">
              <CellAllocationView
                v-for="arr in allocation.data.arrays"
                :key="arr.array_id"
                :array="arr"

              />
            </div>
          </template>
        </section>
      </div>
    </LoadStateBlock>
  </section>
</template>

<style scoped>
.al__intro { font-size: 0.85rem; color: #555; }
.al__family, .al__gate { display: flex; align-items: center; gap: 0.4rem; margin: 0.6rem 0; }
.al__family-label { font-size: 0.85rem; color: #555; }
.al__fam-btn { padding: 0.3rem 0.8rem; border: 1px solid #bbb; background: #fff; border-radius: 3px; cursor: pointer; font-size: 0.85rem; }
.al__fam-btn--active { background: #1a4f8a; color: #fff; border-color: #1a4f8a; font-weight: 600; }
.al__gap { font-size: 0.82rem; color: #8a4b00; background: #fffaf0; border-left: 3px solid #d08700; padding: 0.45rem 0.7rem; }
.al__body { display: grid; gap: 0.9rem; justify-items: start; }
.al__facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: 0.3rem 1rem; margin: 0; font-size: 0.82rem; }
.al__facts dt { color: #666; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em; }
.al__facts dd { margin: 0; font-weight: 600; word-break: break-all; }
.al__block { width: 100%; }
.al__block h3 { font-size: 0.95rem; margin: 0 0 0.3rem; }
.al__block p { font-size: 0.82rem; margin: 0.15rem 0; }
.al__sub { font-size: 0.78rem; color: #666; }
.al__list { font-size: 0.78rem; color: #555; margin: 0.2rem 0; padding-left: 1.1rem; }
.al__lim { font-size: 0.7rem; background: #f4f4f4; border: 1px solid #ddd; border-radius: 3px; padding: 0 0.3rem; margin-right: 0.3rem; }
.al__ev-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.2rem; }
.al__ev-id { font-size: 0.72rem; color: #777; margin-left: 0.5rem; }
.al__map { width: 100%; }
.al__map h3 { font-size: 0.95rem; margin: 0 0 0.3rem; }
.al__note { font-size: 0.78rem; color: #555; }
.al__map-grid { display: grid; gap: 0.8rem; }
</style>
