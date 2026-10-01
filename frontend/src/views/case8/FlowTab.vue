<script setup lang="ts">
/**
 * Case8 Flow tab.
 *
 * Supports recorded snapshots 1…6 only. Displays "Snapshot n / 6", the actual
 * step and actual physical time, and renders density / pressure / front via
 * Canvas 2D from recorded values only.
 *
 * Snapshot 0 is impossible to select: the selector options are exactly the
 * provider's recorded rows (1-based), and any out-of-range value is refused by
 * the provider as a known-missing recorded index.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { dataService, createRequestGuard, type Loaded } from '../../data'
import type { FieldData, SnapshotMeta } from '../../data/domain'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import MockBadge from '../../components/MockBadge.vue'
import SnapshotViewer from '../../scientific/SnapshotViewer.vue'

const props = defineProps<{ configId: string; modelValue?: number; fieldId?: string }>()
const emit = defineEmits<{
  (e: 'update:modelValue', index: number): void
  (e: 'update:fieldId', fieldId: string): void
}>()

const snapshots = ref<Loaded<SnapshotMeta[]> | null>(null)
const field = ref<Loaded<FieldData> | null>(null)
const snapGuard = createRequestGuard()
const fieldGuard = createRequestGuard()

const activeIndex = ref<number>(props.modelValue ?? 1)
const activeField = ref<string>(props.fieldId ?? 'density')

const FIELD_ORDER = ['density', 'pressure', 'front']

const currentMeta = computed<SnapshotMeta | null>(
  () => snapshots.value?.data?.find((s: SnapshotMeta) => s.snapshot_index === activeIndex.value) ?? null,
)
const recordedIndices = computed<number[]>(() => (snapshots.value?.data ?? []).map((s: SnapshotMeta) => s.snapshot_index))

async function loadSnapshots() {
  snapshots.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await snapGuard.run((signal) => dataService.listSnapshots(props.configId, signal))
  if (result) snapshots.value = result
}

async function loadField() {
  field.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await fieldGuard.run((signal) =>
    dataService.getSnapshotField({ configId: props.configId, snapshotIndex: activeIndex.value, fieldId: activeField.value }, signal),
  )
  if (result) field.value = result
}

function selectSnapshot(index: number) {
  // Guard against any non-recorded index (including 0).
  if (!recordedIndices.value.includes(index)) return
  activeIndex.value = index
  emit('update:modelValue', index)
}

function selectField(fieldId: string) {
  activeField.value = fieldId
  emit('update:fieldId', fieldId)
}

onMounted(async () => {
  await loadSnapshots()
  if (!recordedIndices.value.includes(activeIndex.value)) {
    activeIndex.value = recordedIndices.value[0] ?? 1
  }
  await loadField()
})

// Config change must reload from scratch and never keep the old config's field.
watch(() => props.configId, async () => {
  fieldGuard.cancel()
  field.value = null
  await loadSnapshots()
  if (!recordedIndices.value.includes(activeIndex.value)) activeIndex.value = recordedIndices.value[0] ?? 1
  await loadField()
})
watch(() => props.modelValue, value => { if (value !== undefined) activeIndex.value = value })
watch(() => props.fieldId, value => { if (value) activeField.value = value })
watch(activeIndex, loadField)
watch(activeField, loadField)
</script>

<template>
  <section class="flow" data-testid="case8-flow">
    <LoadStateBlock :loaded="snapshots" target="snapshot index">
      <div class="flow__controls">
        <div class="flow__snapshots" role="group" aria-label="Recorded snapshots">
          <button
            v-for="meta in snapshots?.data || []"
            :key="meta.snapshot_index"
            :data-timeline-step="meta.step_index"
            class="flow__snap-btn"
            :class="{ 'flow__snap-btn--active': meta.snapshot_index === activeIndex }"
            :data-testid="`snapshot-${meta.snapshot_index}`"
            @click="selectSnapshot(meta.snapshot_index)"
          >
            {{ meta.snapshot_index }}
          </button>
        </div>
        <div class="flow__fields" role="group" aria-label="Field">
          <button
            v-for="f in FIELD_ORDER"
            :key="f"
            class="flow__field-btn"
            :class="{ 'flow__field-btn--active': f === activeField }"
            :data-testid="`field-${f}`"
            @click="selectField(f)"
          >{{ f }}</button>
        </div>
      </div>

      <p class="flow__index-label" data-testid="snapshot-label">
        Snapshot {{ activeIndex }} / {{ snapshots?.data?.length ?? 0 }}
      </p>

      <dl v-if="currentMeta" class="flow__time" data-testid="snapshot-time">
        <div><dt>Actual completed step</dt><dd data-testid="snapshot-step">{{ currentMeta.step_index }}</dd></div>
        <div><dt>Actual physical time</dt><dd data-testid="snapshot-physical-time">{{ currentMeta.physical_time }}</dd></div>
      </dl>

      <!-- A disabled selector slot makes it obvious index 0 is not a recorded frame. -->
      <p class="flow__note">
        Recorded indices are strictly 1-based ({{ recordedIndices.join(', ') }}). Index 0 is not a
        recorded snapshot and cannot be selected. No interpolated frames are generated.
      </p>

      <LoadStateBlock :loaded="field" target="field values">
        <div v-if="field?.data" class="flow__render">
          <SnapshotViewer :field="field.data.meta" :values="field.data.values" />
          <MockBadge :origin="field.data.data_origin" :verification="field.data.meta.verification_status" />
        </div>
      </LoadStateBlock>

      <p v-if="field?.state === 'MISSING'" class="flow__missing" data-testid="snapshot-missing">
        {{ field.reason }}
      </p>
    </LoadStateBlock>
  </section>
</template>

<style scoped>
.flow__controls { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.8rem; margin-bottom: 0.6rem; }
.flow__snapshots, .flow__fields { display: flex; gap: 0.3rem; }
.flow__snap-btn, .flow__field-btn {
  min-width: 2rem; padding: 0.25rem 0.5rem; border: 1px solid #bbb; background: #fff;
  border-radius: 3px; cursor: pointer; font-size: 0.85rem;
}
.flow__snap-btn--active, .flow__field-btn--active { background: #1a4f8a; color: #fff; border-color: #1a4f8a; }
.flow__index-label { font-weight: 700; font-size: 1rem; margin: 0.3rem 0; }
.flow__time { display: flex; gap: 2rem; font-size: 0.85rem; margin: 0.2rem 0 0.5rem; }
.flow__time dt { color: #666; }
.flow__time dd { margin: 0; font-weight: 600; }
.flow__note { font-size: 0.78rem; color: #777; }
.flow__missing { font-size: 0.85rem; color: #8a4b00; background: #fffaf0; border-left: 3px solid #d08700; padding: 0.4rem 0.6rem; }
.flow__render { margin-top: 0.5rem; display: grid; gap: 0.4rem; justify-items: start; }
</style>
