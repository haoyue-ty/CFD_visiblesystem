<script setup lang="ts">
import { verificationText } from "../../data/evidence"
/**
 * P07 / Spectral Lab tab — Phase 7B Window 3.
 *
 * WHAT THIS IS
 *   Selective modal response: the growth-rate signature Re(λ) of the most unstable
 *   Fourier mode ell, measured on a common Mach6 base state across four recorded
 *   q_at configurations. It is NOT a spatial field and NOT a snapshot.
 *
 * SCIENTIFIC LIMITS (enforced in the UI, not only in comments)
 *   * The panel says "Selective modal response" and NEVER emits a comparative
 *     verdict. Words such as Stable / Improved / Better must not appear.
 *   * q_at is one of the four EXACT registered configurations — there is no
 *     continuous slider and no interpolation between them.
 *   * Fourier mode index (ell, 0..16) and eigenpair rank (0..31) are DIFFERENT
 *     index spaces and are never interchanged.
 *
 * THREE REGIONS
 *   1. spectral abscissa curve   x = mode k, y = Re(λ)
 *   2. mode detail               eigenmode at a chosen mode index; when the saved
 *                                vector is absent the panel shows "Unavailable"
 *                                and never a blank frame.
 *   3. growth validation         linear vs CFD recorded series.
 *
 * SELECTION ORDERING
 *   The dataset identity must be resolved (SPEC00) before a curve can be read;
 *   q_at is a property of the resolved dataset (SPEC01), so the front end never
 *   constructs a `spectrum.q-*` string from a free-form number.
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { activeProvider, dataService, createRequestGuard, type Loaded } from '../../data'
import type {
  EigenmodeSelector,
  EigenmodeView,
  GrowthValidationView,
  SpectralArrayView,
  SpectrumCurveView,
  SpectrumDatasetView,
  SpectralDatasetRef,
  ValidationRunRef,
} from '../../data'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import MockBadge from '../../components/MockBadge.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'
import SpectralCurveChart from '../../scientific/SpectralCurveChart.vue'
import EigenmodeChart from '../../scientific/EigenmodeChart.vue'
import GrowthValidationChart from '../../scientific/GrowthValidationChart.vue'

const props = defineProps<{ guidedTargets?: string[] }>()
const guided = computed(() => Boolean(props.guidedTargets))
const guidedCurves = ref<Loaded<SpectrumCurveView>[] | null>(null)
const guidedGuard = createRequestGuard()
const route = useRoute()
const router = useRouter()

/** The four registered q_at configurations are discovered from SPEC00, never hard-coded. */
const datasets = ref<Loaded<SpectralDatasetRef[]> | null>(null)
const dataset = ref<Loaded<SpectrumDatasetView> | null>(null)
const curve = ref<Loaded<SpectrumCurveView> | null>(null)
const mode = ref<Loaded<EigenmodeView> | null>(null)
const modeArray = ref<Loaded<SpectralArrayView> | null>(null)
const validation = ref<Loaded<GrowthValidationView> | null>(null)
const runs = ref<Loaded<ValidationRunRef[]> | null>(null)

const datasetsGuard = createRequestGuard()
const curveGuard = createRequestGuard()
const datasetGuard = createRequestGuard()
const modeGuard = createRequestGuard()
const validationGuard = createRequestGuard()

/** Selected dataset id; defaults to the first registered q, else the query value. */
const selectedDatasetId = ref<string>(typeof route.query.spectral_q === 'string' ? route.query.spectral_q : '')

/** Selected Fourier mode index (ell). */
const selectedModeIndex = ref<number>(normalizeMode(route.query.spectral_mode))
/** Eigenpair rank (0..31) — a DIFFERENT index space from the mode index. */
const selectedRank = ref<number>(normalizeRank(route.query.spectral_rank))
const selectedSide = ref<'LEFT' | 'RIGHT'>('RIGHT')
const selectedRunId = ref<string>(typeof route.query.spectral_run === 'string' ? route.query.spectral_run : '')

function normalizeMode(value: unknown): number {
  const n = typeof value === 'string' ? Number(value) : 1
  return Number.isInteger(n) && n >= 0 && n <= 16 ? n : 1
}
function normalizeRank(value: unknown): number {
  const n = typeof value === 'string' ? Number(value) : 0
  return Number.isInteger(n) && n >= 0 && n <= 31 ? n : 0
}

const returnTo = computed(() => ({ name: route.name as string, params: route.params, query: route.query }))

// --- loaders ----------------------------------------------------------------

async function loadDatasets() {
  datasets.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await datasetsGuard.run((signal) => dataService.listSpectra(signal))
  if (!result) return
  datasets.value = result
  if (result.state === 'READY' || result.state === 'PARTIAL') {
    const ids = (result.data ?? []).map(item => item.dataset_id)
    // A query dataset id that is not registered falls back to the first registered one.
    if (!ids.includes(selectedDatasetId.value)) selectedDatasetId.value = ids[0] ?? ''
  }
}

async function loadCurve() {
  if (!selectedDatasetId.value) return
  curve.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  dataset.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const [datasetResult, curveResult] = await Promise.all([
    datasetGuard.run((signal) => dataService.getSpectrumDataset({ datasetId: selectedDatasetId.value }, signal)),
    curveGuard.run((signal) => dataService.getSpectralCurve({ datasetId: selectedDatasetId.value }, signal)),
  ])
  if (datasetResult) dataset.value = datasetResult
  if (curveResult) curve.value = curveResult
}

async function loadMode() {
  if (!selectedDatasetId.value) return
  mode.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  modeArray.value = null
  const selector: EigenmodeSelector = {
    datasetId: selectedDatasetId.value,
    modeIndex: selectedModeIndex.value,
    side: selectedSide.value,
    rank: selectedRank.value,
    representation: 'COMPLEX_VECTOR',
    projection: 'COMPLEX',
    fieldComponent: 'stored_vector',
  }
  const result = await modeGuard.run((signal) => dataService.getEigenmode(selector, signal))
  if (!result) return
  mode.value = result
  if ((result.state === 'READY' || result.state === 'PARTIAL') && result.data) {
    const array = await modeGuard.run((signal) => dataService.loadSpectralArray(result.data!.values_ref, signal))
    if (array) modeArray.value = array
  }
}

async function loadValidation() {
  runs.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const runList = await validationGuard.run((signal) => dataService.listValidationRuns(signal))
  if (runList) runs.value = runList
  const ids = (runList?.data ?? []).map(run => run.run_id)
  if (!ids.includes(selectedRunId.value)) selectedRunId.value = ids[0] ?? ''
  if (!selectedRunId.value) {
    validation.value = { state: 'MISSING', data: null, reason: 'No recorded validation run is registered.', origin: 'MOCK' }
    return
  }
  validation.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await validationGuard.run((signal) => dataService.getGrowthValidation(selectedRunId.value, signal))
  if (result) validation.value = result
}

onBeforeUnmount(() => { [datasetsGuard, curveGuard, datasetGuard, modeGuard, validationGuard, guidedGuard].forEach(g => g.cancel()) })
onMounted(async () => {
  if (guided.value) {
    await guidedGuard.run(async signal => {
      const curves = await Promise.all((props.guidedTargets ?? []).map(datasetId => dataService.getSpectralCurve({ datasetId }, signal)))
      if (!signal.aborted) guidedCurves.value = curves
      return { state: 'READY', data: curves, reason: null, origin: 'FROZEN_PRODUCTION' }
    })
    return
  }
  await loadDatasets()
  await Promise.all([loadCurve(), loadMode(), loadValidation()])
})

watch(selectedDatasetId, () => { if (!guided.value) { void loadCurve(); void loadMode() } })
watch([selectedModeIndex, selectedRank, selectedSide], () => { if (!guided.value) void loadMode() })
watch(selectedRunId, () => { if (!guided.value) void loadValidation() })

function direction(a: number | null, b: number | null) {
  if (a === null || b === null) return 'unavailable'
  if (a.toFixed(10) === b.toFixed(10)) return 'near-zero shift (at displayed precision)'
  return b < a ? 'negative shift' : 'positive shift'
}
const guidedRows = computed(() => {
  const [base, enabled] = guidedCurves.value ?? []
  if (!base?.data || !enabled?.data) return []
  return base.data.points.map(point => {
    const other = enabled.data!.points.find(p => p.mode_index === point.mode_index)
    return { mode: point.mode_index, baseline: point.real_lambda, enabled: other?.real_lambda ?? null, direction: direction(point.real_lambda, other?.real_lambda ?? null) }
  })
})
// --- derived facts ----------------------------------------------------------

/** The recorded q of the resolved dataset — read from the API, never from the id. */
const qAt = computed(() => dataset.value?.data?.q_at ?? curve.value?.data?.q_at ?? null)

/** eigenmodes whose saved vector may legitimately be absent for this dataset. */
const modeUnavailable = computed(() => mode.value?.state === 'MISSING')

function updateQuery() {
  if (guided.value) return
  // URL is the owner of selection state (README): a deep link restores the view.
  const query: Record<string, string> = { ...(route.query as Record<string, string>),
    spectral_q: selectedDatasetId.value, spectral_mode: String(selectedModeIndex.value),
    spectral_rank: String(selectedRank.value), spectral_run: selectedRunId.value }
  void router.replace({ query })
}
watch([selectedDatasetId, selectedModeIndex, selectedRank, selectedRunId], updateQuery)
</script>

<template>
  <section class="sl" data-page="spectral-lab" data-testid="spectral-lab">
    <!-- SCIENTIFIC SCOPE: the page states what it is and what it must not be read as -->
    <header class="sl__scope" data-testid="spectral-scope">
      <h2>Selective modal response</h2>
      <p class="sl__scope-text">
        The growth-rate signature <strong>Re(λ)</strong> of the most unstable Fourier mode, measured on a
        common Mach6 base state. Each <em>q_at</em> below is one exact registered configuration; modes are
        discrete blocks (ell 0…16). This page reports recorded spectral facts only.
      </p>
      <p data-testid="spectral-scientific-limit">Positive entropy production does not imply uniform modal damping.</p>
    </header>

    <section v-if="guided" data-testid="guided-spectral">
      <p>q_at=0 and q_at=.396 · emphasis: mode 4 / mode 8. All recorded ell 0…16 remain visible.</p>
      <p>Negative shift, positive shift and near-zero shift compare recorded Re(λ) values. Near-zero means equal at ten decimal places for display; it is not a formal stability threshold or a recalculated metric.</p>
      <LoadStateBlock v-if="!guidedCurves" :loaded="null" target="recorded spectrum comparison" />
      <div v-for="(loaded, i) in guidedCurves ?? []" :key="i">
        <LoadStateBlock :loaded="loaded" target="recorded spectrum curve">
          <template v-if="loaded.data">
            <MockBadge :origin="loaded.data.result.data_origin" :verification="loaded.data.verification.status" />
            <SpectralCurveChart :curve="loaded.data" />
            <p>{{ loaded.data.provenance.registry_revision }} · {{ loaded.data.provenance.data_revision }} · {{ verificationText(loaded.data.verification) }}</p>
            <EvidenceLink v-for="id in loaded.data.provenance.evidence_refs" :key="id" :evidence-id="id" :return-to="returnTo" />
          </template>
        </LoadStateBlock>
      </div>
      <table v-if="guidedRows.length" data-testid="guided-modal-table">
        <thead><tr><th>ell</th><th>Recorded Re(λ), q_at=0</th><th>Recorded Re(λ), q_at=.396</th><th>Direction at displayed precision</th></tr></thead>
        <tbody><tr v-for="row in guidedRows" :key="row.mode" :data-mode="row.mode" :class="{ emphasized: [4, 8].includes(row.mode) }"><th>{{ row.mode }}</th><td>{{ row.baseline?.toFixed(10) ?? 'UNKNOWN' }}</td><td>{{ row.enabled?.toFixed(10) ?? 'UNKNOWN' }}</td><td>{{ row.direction }}</td></tr></tbody>
      </table>
    </section>
    <template v-else>
    <!-- SELECTION: configuration (dataset) + exact q_at -->
    <LoadStateBlock :loaded="datasets" target="spectral datasets">
      <div class="sl__select" role="group" aria-label="Spectral dataset">
        <span class="sl__select-label">configuration:</span>
        <button
          v-for="item in datasets?.data || []"
          :key="item.dataset_id"
          class="sl__btn"
          :class="{ 'sl__btn--active': item.dataset_id === selectedDatasetId }"
          :data-testid="`spectral-q-${item.q_at}`"
          :aria-pressed="item.dataset_id === selectedDatasetId"
          @click="selectedDatasetId = item.dataset_id"
        >{{ item.configuration_id }}</button>
      </div>
      <p class="sl__qat" data-testid="spectral-qat">
        q_at = <strong>{{ qAt === null ? 'unavailable' : qAt }}</strong>
        <span class="sl__qat-note">(one of four exact recorded configurations — never interpolated)</span>
      </p>
    </LoadStateBlock>

    <!-- REGION 1: spectral abscissa curve -->
    <section class="sl__region" data-testid="spectral-curve-region">
      <h3>1 · Spectral abscissa curve</h3>
      <p class="sl__axis-note">x = mode k · y = Re(λ)</p>
      <LoadStateBlock :loaded="curve" target="spectral curve">
        <template v-if="curve?.data">
          <MockBadge :origin="curve.data.result.data_origin" :verification="curve.data.verification.status" />
          <SpectralCurveChart :curve="curve.data" />
          <p class="sl__prov" data-testid="curve-provenance">
            registry_revision={{ curve.data.provenance.registry_revision }} ·
            data_revision={{ curve.data.provenance.data_revision }} ·
            verification={{ verificationText(curve.data.verification) }}
          </p>
        </template>
      </LoadStateBlock>
    </section>

    <!-- REGION 2: mode detail -->
    <section class="sl__region" data-testid="spectral-mode-region">
      <h3>2 · Mode detail</h3>
      <div class="sl__select" role="group" aria-label="Fourier mode index">
        <span class="sl__select-label">mode index (ell):</span>
        <button
          v-for="k in 17"
          :key="k - 1"
          class="sl__btn sl__btn--mode"
          :class="{ 'sl__btn--active': (k - 1) === selectedModeIndex }"
          :data-testid="`spectral-mode-${k - 1}`"
          :aria-pressed="(k - 1) === selectedModeIndex"
          @click="selectedModeIndex = k - 1"
        >{{ k - 1 }}</button>
      </div>

      <!-- MISSING saved vector: an explicit "Unavailable", never a blank frame -->
      <div v-if="modeUnavailable" class="sl__unavailable" data-testid="spectral-mode-unavailable" role="note">
        <strong>Unavailable.</strong>
        {{ mode?.reason || 'No saved eigenmode vector exists for this selection in the recorded source.' }}
      </div>

      <LoadStateBlock v-else :loaded="mode" target="eigenmode">
        <template v-if="mode?.data">
          <MockBadge :origin="mode.data.result.data_origin" :verification="mode.data.verification.status" />
          <dl class="sl__facts">
            <div><dt>mode index (ell)</dt><dd data-testid="mode-index">{{ mode.data.mode_index }}</dd></div>
            <div><dt>side</dt><dd data-testid="mode-side">{{ mode.data.side }}</dd></div>
            <div><dt>rank (eigenpair)</dt><dd data-testid="mode-rank">{{ mode.data.rank }}</dd></div>
            <div><dt>eigen representation</dt><dd data-testid="mode-representation">{{ mode.data.eigen_representation }}</dd></div>
            <div><dt>projection</dt><dd data-testid="mode-projection">{{ mode.data.projection }}</dd></div>
            <div><dt>field component</dt><dd data-testid="mode-component">{{ mode.data.field_component }}</dd></div>
            <div><dt>shape</dt><dd data-testid="mode-shape">{{ mode.data.shape.join(' × ') }}</dd></div>
            <div><dt>localization</dt><dd data-testid="mode-localization">{{ mode.data.localization_fraction === null ? 'unavailable' : mode.data.localization_fraction }}</dd></div>
          </dl>
          <p class="sl__prov">{{ mode.data.localization_definition }}</p>
          <!-- values load separately through ARRAY01 -->
          <LoadStateBlock :loaded="modeArray" target="eigenmode values">
            <EigenmodeChart v-if="modeArray?.data && mode.data" :mode="mode.data" :array="modeArray.data" />
          </LoadStateBlock>
          <p class="sl__prov" data-testid="mode-provenance">
            registry_revision={{ mode.data.provenance.registry_revision }} ·
            data_revision={{ mode.data.provenance.data_revision }} ·
            verification={{ verificationText(mode.data.verification) }}
          </p>
        </template>
      </LoadStateBlock>
    </section>

    <!-- REGION 3: growth validation -->
    <section class="sl__region" data-testid="spectral-validation-region">
      <h3>3 · Growth validation — linear vs CFD</h3>
      <div v-if="runs?.data?.length" class="sl__select" role="group" aria-label="Validation run">
        <span class="sl__select-label">recorded run:</span>
        <button
          v-for="(run, i) in runs.data"
          :key="run.run_id"
          class="sl__btn sl__btn--run"
          :class="{ 'sl__btn--active': run.run_id === selectedRunId }"
          :data-testid="`spectral-run-${i}`"
          :aria-pressed="run.run_id === selectedRunId"
          @click="selectedRunId = run.run_id"
        >{{ run.label }}</button>
      </div>

      <LoadStateBlock :loaded="validation" target="growth validation" ready-state="READY">
        <template v-if="validation?.data">
          <MockBadge :origin="validation.data.result.data_origin" :verification="validation.data.verification.status" />
          <GrowthValidationChart :validation="validation.data" />
          <p>Recorded growth rates [{{ validation.data.result.unit.label }}]</p>
          <dl class="sl__facts">
            <div><dt>σ linear</dt><dd data-testid="growth-linear">{{ validation.data.growth_rate.linear === null ? 'unavailable' : validation.data.growth_rate.linear.toExponential(6) }}</dd></div>
            <div><dt>σ RK3</dt><dd data-testid="growth-rk3">{{ validation.data.growth_rate.rk3 === null ? 'unavailable' : validation.data.growth_rate.rk3.toExponential(6) }}</dd></div>
            <div><dt>σ CFD</dt><dd data-testid="growth-cfd">{{ validation.data.growth_rate.cfd === null ? 'unavailable' : validation.data.growth_rate.cfd.toExponential(6) }}</dd></div>
            <div><dt>relative discrepancy (CFD−RK3)</dt><dd data-testid="growth-error">{{ validation.data.error.relative_discrepancy === null ? 'unavailable' : validation.data.error.relative_discrepancy.toExponential(6) }}</dd></div>
          </dl>
          <!-- A MISSING prediction history stays visible and explained -->
          <p v-if="validation.data.linear_amplitude.every(v => v === null)" class="sl__gap" data-testid="growth-linear-missing">
            The <strong>linear amplitude history</strong> was not saved for this run. Only the recorded
            linear/RK3/CFD rates and the 33-step CFD history are present — no prediction curve is synthesized.
          </p>
          <p class="sl__prov" data-testid="validation-provenance">
            registry_revision={{ validation.data.provenance.registry_revision }} ·
            data_revision={{ validation.data.provenance.data_revision }} ·
            verification={{ verificationText(validation.data.verification) }} ·
            amplitude={{ validation.data.amplitude_definition }}
          </p>
        </template>
      </LoadStateBlock>
    </section>

    <!-- Evidence -->
    <section class="sl__region" data-testid="spectral-evidence">
      <h3>Evidence</h3>
      <ul class="sl__ev-list">
        <li v-for="ref in [...new Set([...(dataset?.data?.provenance.evidence_refs ?? []), ...(curve?.data?.provenance.evidence_refs ?? []), ...(mode?.data?.provenance.evidence_refs ?? []), ...(validation?.data?.provenance.evidence_refs ?? [])])]" :key="ref" data-testid="spectral-evidence-link">
          <EvidenceLink :evidence-id="ref" context="spectral" :return-to="returnTo" />
          <span class="sl__ev-id">{{ ref }}</span>
        </li>
      </ul>
    </section>    </template>
  </section>
</template>

<style scoped>
table { border-collapse: collapse; width: 100%; font-size: .8rem; } th, td { text-align: left; padding: .4rem; border: 1px solid #ddd; overflow-wrap: anywhere; } .emphasized { background: #eef4fc; font-weight: bold; }
.sl { display: grid; gap: 1.1rem; }
.sl__scope { border-left: 3px solid #1a4f8a; background: #f2f6fb; padding: 0.6rem 0.9rem; }
.sl__scope h2 { margin: 0 0 0.3rem; font-size: 1.15rem; color: #1a4f8a; }
.sl__scope-text { margin: 0; font-size: 0.84rem; color: #444; }
.sl__region { border: 1px solid #e2e2e2; border-radius: 4px; padding: 0.7rem 0.9rem; display: grid; gap: 0.5rem; }
.sl__region h3 { margin: 0; font-size: 0.98rem; }
.sl__axis-note { margin: 0; font-size: 0.8rem; color: #666; }
.sl__select { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; }
.sl__select-label { font-size: 0.82rem; color: #555; }
.sl__btn { padding: 0.28rem 0.7rem; border: 1px solid #bbb; background: #fff; border-radius: 3px; cursor: pointer; font-size: 0.82rem; }
.sl__btn--mode { min-width: 2rem; padding: 0.28rem 0.4rem; }
.sl__btn--active { background: #1a4f8a; color: #fff; border-color: #1a4f8a; font-weight: 600; }
.sl__qat { margin: 0.2rem 0 0; font-size: 0.85rem; }
.sl__qat-note { color: #777; font-size: 0.75rem; margin-left: 0.4rem; }
.sl__facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0.3rem 1rem; margin: 0.2rem 0; font-size: 0.82rem; }
.sl__facts dt { color: #666; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em; }
.sl__facts dd { margin: 0; font-weight: 600; word-break: break-all; }
.sl__prov { font-size: 0.72rem; color: #777; margin: 0; }
.sl__unavailable { color: #8a4b00; background: #fffaf0; border-left: 3px solid #d08700; padding: 0.5rem 0.8rem; font-size: 0.85rem; }
.sl__gap { font-size: 0.8rem; color: #8a4b00; background: #fffaf0; border-left: 3px solid #d08700; padding: 0.45rem 0.7rem; }
.sl__ev-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.2rem; }
.sl__ev-id { font-size: 0.72rem; color: #777; margin-left: 0.5rem; }
</style>
