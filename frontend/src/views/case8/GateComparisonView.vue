<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { verificationText } from "../../data/evidence"
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { contentService } from '../../data/content'
import { dataService, createRequestGuard, type Loaded, type AllocationView, type EvidenceDetailView } from '../../data'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import CellAllocationView from '../../scientific/CellAllocationView.vue'
import AllocationSummary from '../../scientific/AllocationSummary.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'
const comparison = ref<Awaited<ReturnType<typeof contentService.gateComparison>> | null>(null)
const evidence = ref<Record<string, Loaded<EvidenceDetailView>>>({})
const fields = ref<Record<string, Loaded<AllocationView>>>({})
const guard = createRequestGuard()
const extent = computed<[number, number] | null>(() => {
  const values = comparison.value?.data?.shared_extent.map(slot => 'value' in slot && slot.value.value.state === 'KNOWN' ? slot.value.value.value : null)
  return values?.length === 2 && values.every(v => v !== null) ? values as [number, number] : null
})
function qAt(configId: string) {
  return evidence.value[configId]?.data?.config_parameters.find(p => p.name === 'q_at')?.value ?? 'UNKNOWN'
}
onMounted(async () => {
  const result = await guard.run(async signal => {
    const compare = await contentService.gateComparison(signal)
    if (!signal.aborted) comparison.value = compare
    if (!compare.data) return compare
    await Promise.all(compare.data.entries.map(async entry => {
      const [loaded, configEvidence] = await Promise.all([dataService.describeAllocation({ experimentId: 'gate', configId: entry.config_id }, signal), dataService.getEvidence(`ev.gate.${entry.config_id}.allocation`, signal)])
      if (!signal.aborted) { fields.value[entry.config_id] = loaded; evidence.value[entry.config_id] = configEvidence }
    }))
    return compare
  })
  if (result) comparison.value = result
})
onBeforeUnmount(() => { guard.cancel() })
</script>
<template>
  <section data-testid="gate-comparison">
    <p>{{ zh("Approximately matched budgets; not exactly identical. Fixed shock window; no universal localization ranking.") }}</p>
    <LoadStateBlock :loaded="comparison" :target="zh('Gate comparison')">
      <template v-if="comparison?.data">
        <p data-testid="gate-shared-scale">{{ zh(comparison.data.colour_scale) }} · {{ zh(extent?.join(' … ') ?? 'unavailable') }}</p>
        <p v-if="!extent" role="alert">{{ zh("Shared colour extent unavailable. Comparison maps cannot be rendered.") }}</p>
        <div class="gate-grid" v-if="extent">
          <article v-for="entry in comparison.data.entries" :key="entry.result_id" :data-testid="`gate-${entry.config_id}`">
            <LoadStateBlock :loaded="evidence[entry.config_id] ?? null" :target="zh('Gate matched configuration')" />
            <h3>{{ zh(entry.config_id) }} · q_at=<span data-testid="matched-qat">{{ zh(qAt(entry.config_id)) }}</span></h3>
            <LoadStateBlock :loaded="fields[entry.config_id] ?? null" :target="zh('Gate allocation')">
              <template v-if="fields[entry.config_id]?.data?.representation_type === 'CELL_FIELD'">
                <CellAllocationView v-for="array in fields[entry.config_id]!.data!.arrays" :key="array.array_id" :array="array" :colour-extent="extent" />
                <AllocationSummary :summary="fields[entry.config_id]!.data!.summary" />
                <p data-testid="gate-window">{{ zh(fields[entry.config_id]!.data!.mask.definition) }} {{ zh("· counts=") }}{{ zh(fields[entry.config_id]!.data!.mask.counts.join(',')) }}</p>
                <p>{{ zh(verificationText(fields[entry.config_id]!.data!.verification)) }} · {{ zh(fields[entry.config_id]!.data!.data_origin) }}</p>
                <p>{{ zh(fields[entry.config_id]!.data!.definition) }} · {{ zh(fields[entry.config_id]!.data!.time_rule) }}</p>
                <p v-for="lim in fields[entry.config_id]!.data!.limitations" :key="lim.id">{{ zh(lim.code) }} — {{ zh(lim.description) }}</p>
              </template>
            </LoadStateBlock>
            <EvidenceLink v-for="id in fields[entry.config_id]?.data?.evidence_refs ?? []" :key="id" :evidence-id="id" />
          </article>
        </div>
      </template>
    </LoadStateBlock>
  </section>
</template>
<style scoped>.gate-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); gap: 1rem; } article { min-width: 0; padding: .7rem; border: 1px solid #ddd; } p { overflow-wrap: anywhere; }</style>
