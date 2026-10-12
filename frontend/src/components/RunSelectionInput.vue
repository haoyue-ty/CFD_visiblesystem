<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { loadRun, type RunRecord } from '../data/v2/runs'
import { runCaseName, runDate } from '../presentation/runs'

const props = defineProps<{ modelValue: string; label: string; list: string; runs: RunRecord[]; disabled?: boolean; detailsId: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const id = computed(() => props.modelValue.trim())
const listed = computed(() => props.runs.find(run => run.run_id === id.value))
const lookup = useQuery({
  queryKey: computed(() => ['v2', 'run-selection', id.value]),
  queryFn: () => loadRun(id.value),
  enabled: computed(() => !listed.value && /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i.test(id.value)),
  staleTime: 60_000,
  retry: false,
})
const selected = computed(() => listed.value ?? (lookup.data.value?.run_id === id.value ? lookup.data.value : undefined))
</script>

<template>
  <label class="run-selection">{{ label }}
    <input :value="modelValue" :disabled="disabled" :list="list" :aria-label="label" :aria-describedby="detailsId" required placeholder="按创建时间选择，或粘贴 Run ID" @input="emit('update:modelValue', ($event.target as HTMLInputElement).value.trim())" />
    <small :id="detailsId" class="run-selection__details" :data-testid="detailsId" aria-live="polite">
      <template v-if="selected">
        <time :datetime="selected.created_at">创建于 {{ runDate(selected.created_at) }}</time>
        <span>{{ runCaseName(selected.experiment.normalized_config.case_id) }} · {{ selected.experiment.normalized_config.grid.nx }} × {{ selected.experiment.normalized_config.grid.ny }} · T={{ selected.requested_final_time }}</span>
        <span>q_aa={{ selected.experiment.normalized_config.method.q_aa }} · q_at={{ selected.experiment.normalized_config.method.q_at }} · ID {{ selected.run_id.slice(0, 8) }}</span>
      </template>
      <span v-else-if="lookup.isFetching.value">正在读取运行时间与参数…</span>
      <span v-else-if="lookup.isError.value">无法读取该运行的备注，请核对 ID 或重新选择。</span>
      <span v-else>列表备注包含创建时间、网格、系数和短 ID。</span>
    </small>
  </label>
</template>

<style scoped>
.run-selection { display: grid; gap: 8px; flex: 1 1 280px; min-width: 0; }
.run-selection input { width: 100%; min-width: 0; min-height: 44px; padding: 10px 12px; border: 1px solid var(--sp-border); border-radius: 12px; background: var(--sp-surface); color: var(--sp-text); font: inherit; font-size: 14px; }
.run-selection input::placeholder { color: var(--sp-muted); font-size: 12px; }
.run-selection__details { display: grid; gap: 3px; margin: 0; font-size: 11px; line-height: 1.6; color: var(--sp-muted); overflow-wrap: anywhere; }
.run-selection__details time { color: #4e596d; font-size: 12px; }
</style>
