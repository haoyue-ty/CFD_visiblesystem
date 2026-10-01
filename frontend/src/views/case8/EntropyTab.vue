<script setup lang="ts">
/**
 * Case8 Entropy tab.
 *
 * Renders E_bg / E_aa / E_at. Selecting a scalar point selects a REAL accepted
 * step; the tab then queries the nearest recorded snapshot and displays:
 *   - the selected scalar time (fine granularity, 1..1912 steps)
 *   - the displayed snapshot time (coarse granularity, 1..6 snapshots)
 * Both are shown together. They are never conflated and no rounded time is
 * passed off as the actual time.
 */
import { onMounted, ref, watch } from 'vue'
import { dataService, createRequestGuard, type Loaded } from '../../data'
import type { EntropyHistoryView, SnapshotAlignmentView } from '../../data/domain'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import MockBadge from '../../components/MockBadge.vue'
import EntropyChart from '../../scientific/EntropyChart.vue'

const props = defineProps<{ configId: string; modelValue?: number | null }>()
const emit = defineEmits<{ (e: 'update:modelValue', step: number): void }>()

const history = ref<Loaded<EntropyHistoryView> | null>(null)
const alignment = ref<Loaded<SnapshotAlignmentView> | null>(null)
const selectedStep = ref<number | null>(props.modelValue ?? null)
const manualStep = ref<number | null>(props.modelValue ?? null)

const historyGuard = createRequestGuard()
const alignGuard = createRequestGuard()

async function loadHistory() {
  history.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await historyGuard.run((signal) => dataService.getEntropyHistory(props.configId, signal))
  if (result) history.value = result
}

async function loadAlignment(step: number) {
  alignment.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await alignGuard.run((signal) =>
    dataService.getSnapshotAlignment(props.configId, step, 'NEAREST_RECORDED', undefined, signal),
  )
  if (result) alignment.value = result
}

function onSelectStep(step: number) {
  selectedStep.value = step
  manualStep.value = step
  emit('update:modelValue', step)
  loadAlignment(step)
}

/** Apply a manually entered accepted step, clamped to the recorded range. */
function applyManualStep() {
  const total = history.value?.data?.total_point_count
  const value = manualStep.value
  if (typeof value !== 'number' || !Number.isInteger(value)) return
  if (total && (value < 1 || value > total)) return
  const step = value
  selectedStep.value = step
  manualStep.value = step
  emit('update:modelValue', step)
  loadAlignment(step)
}

onMounted(async () => {
  await loadHistory()
  if (selectedStep.value !== null) await loadAlignment(selectedStep.value)
})

watch(() => props.configId, async () => {
  // Configuration change: drop the old alignment (it belonged to another config).
  alignGuard.cancel()
  alignment.value = null
  selectedStep.value = null
  manualStep.value = null
  await loadHistory()
})
watch(selectedStep, (step) => {
  if (step !== null) loadAlignment(step)
})
</script>

<template>
  <section class="ent" data-testid="case8-entropy">
    <LoadStateBlock :loaded="history" target="entropy history">
      <div v-if="history?.data" class="ent__body">
        <EntropyChart :history="history.data" @select-scalar-step="onSelectStep" />
        <MockBadge :origin="history.data.series[0]?.data_origin || 'MOCK'" :verification="history.data.series[0]?.verification.status" />

        <div class="ent__series-legend">
          <span data-field="aggregation">{{ history.data.series[0]?.aggregation }}</span>
          <p><strong>E_bg</strong> background production · <strong>E_aa</strong> acoustic pathway · <strong>E_at</strong> q_at channel cumulative production</p>
          <p class="ent__caption">
            <span data-field="total-point-count">{{ history.data.total_point_count }}</span> accepted scalar steps recorded. Step increment and
            cumulative aggregation are shown as separate semantics.
          </p>
        </div>
      </div>
    </LoadStateBlock>

    <section class="ent__alignment" aria-label="Scalar / snapshot alignment">
      <h3>Scalar selection &amp; snapshot alignment</h3>

      <!-- Manual step selection: selects a REAL accepted step by number, and is
           the accessible equivalent of clicking the chart. -->
      <div v-if="history?.data" class="ent__picker">
        <label for="scalar-step-input">Select accepted step (1…{{ history.data.total_point_count }}):</label>
        <input
          id="scalar-step-input"
          data-testid="scalar-step-input"
          type="number"
          :min="1"
          :max="history.data.total_point_count"
          v-model.number="manualStep"
          @keyup.enter="applyManualStep"
        />
        <button data-testid="scalar-step-apply" @click="applyManualStep">Apply</button>
      </div>

      <p v-if="selectedStep === null" class="ent__hint" data-testid="alignment-empty">
        No scalar point selected yet. Click the chart, or pick an accepted step above.
      </p>
      <LoadStateBlock v-else :loaded="alignment" target="snapshot alignment">
        <div v-if="alignment?.data" class="ent__dual" data-testid="dual-time-notice">
          <div class="ent__dual-col">
            <h4>Selected scalar time</h4>
            <p class="ent__dual-big" data-testid="selected-scalar-time">{{ alignment.data.selected_scalar_time }}</p>
            <p class="ent__dual-sub">completed step {{ alignment.data.selected_scalar_step }} · fine granularity (1…{{ history?.data?.total_point_count }})</p>
          </div>
          <div class="ent__dual-col">
            <h4>Displayed snapshot time</h4>
            <p class="ent__dual-big" data-testid="displayed-snapshot-time">{{ alignment.data.displayed_snapshot_time }}</p>
            <p class="ent__dual-sub">
              nearest recorded snapshot {{ alignment.data.displayed_snapshot_index }} · coarse granularity (1…6)
            </p>
          </div>
          <div class="ent__dual-col">
            <h4>Signed delta</h4>
            <p class="ent__dual-big">{{ alignment.data.signed_time_delta }}</p>
            <p class="ent__dual-sub">displayed time − selected time</p>
          </div>
        </div>
        <p class="ent__warn" data-testid="granularity-warning">
          The two times use different granularities and are <strong>not</strong> the same instant.
          No interpolated field is generated for the selected scalar step.
        </p>
      </LoadStateBlock>
    </section>
  </section>
</template>

<style scoped>
.ent__body { display: grid; gap: 0.4rem; justify-items: start; }
.ent__series-legend { font-size: 0.85rem; color: #444; }
.ent__caption { font-size: 0.78rem; color: #777; }
.ent__alignment { margin-top: 1.5rem; border-top: 1px solid #e6e6e6; padding-top: 1rem; }
.ent__alignment h3 { font-size: 1rem; }
.ent__hint { font-size: 0.85rem; color: #777; }
.ent__picker { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; margin-bottom: 0.6rem; }
.ent__picker input { width: 7rem; padding: 0.2rem 0.4rem; border: 1px solid #bbb; border-radius: 3px; }
.ent__picker button { padding: 0.25rem 0.7rem; border: 1px solid #1a4f8a; background: #1a4f8a; color: #fff; border-radius: 3px; cursor: pointer; }
.ent__dual { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 1rem; }
.ent__dual-col h4 { margin: 0; font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.04em; }
.ent__dual-big { margin: 0.2rem 0; font-size: 1.15rem; font-weight: 700; color: #1a3a5c; }
.ent__dual-sub { font-size: 0.76rem; color: #777; margin: 0; }
.ent__warn { font-size: 0.8rem; color: #8a4b00; background: #fffaf0; border-left: 3px solid #d08700; padding: 0.4rem 0.6rem; margin-top: 0.7rem; }
</style>
