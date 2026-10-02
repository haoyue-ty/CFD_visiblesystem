<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createRequestGuard, type Loaded } from '../../data'
import { evidenceService, factText, knownValue, nonNumerical, supports, type EvidenceRecord } from '../../data/evidence'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import EvidenceStatus from './EvidenceStatus.vue'
import { quickView, closeEvidence } from './quickView'
const route = useRoute(), guard = createRequestGuard()
const record = ref<Loaded<EvidenceRecord> | null>(null), panel = ref<HTMLElement | null>(null)
watch(() => quickView.value?.id, async id => {
  record.value = null; guard.cancel()
  if (!id) return
  await nextTick(); panel.value?.querySelector<HTMLButtonElement>('button')?.focus()
  const result = await guard.run(signal => evidenceService.record(id, signal))
  if (result) record.value = result
})
watch(() => route.fullPath, closeEvidence)
onBeforeUnmount(() => { guard.cancel(); closeEvidence() })
function keydown(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); closeEvidence() }
  if (event.key !== 'Tab' || !panel.value) return
  const nodes = Array.from(panel.value.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], [tabindex="0"]'))
  const first = nodes[0], last = nodes[nodes.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}
</script>
<template>
  <Teleport to="body">
    <div v-if="quickView" class="evidence-overlay" @click.self="closeEvidence">
      <section ref="panel" class="evidence-drawer" role="dialog" aria-modal="true" aria-labelledby="quick-title" data-testid="evidence-quick-view" @keydown="keydown">
        <button data-testid="quick-close" @click="closeEvidence">{{ zh("Close quick view") }}</button>
        <h2 id="quick-title">{{ zh("Evidence Quick View") }}</h2>
        <LoadStateBlock :loaded="record" :target="zh('evidence quick view')">
          <template v-if="record?.data">
            <h3>{{ zh(record.data.evidence_id) }}</h3>
            <p data-testid="quick-identity"><strong>{{ zh("Result identity:") }}</strong> {{ zh(record.data.result_ids.join(', ') || 'No numerical result identity — provenance / content record') }}</p>
            <p v-if="nonNumerical(record.data)" data-testid="quick-non-numerical">{{ zh("NON-NUMERICAL EVIDENCE · no numerical availability claim.") }}</p>
            <p><strong>{{ zh("Experiment / config:") }}</strong> {{ zh(factText(record.data.experiment_id)) }} / {{ zh(factText(record.data.config_id)) }}</p>
            <p><strong>{{ zh("Semantic / scope:") }}</strong> {{ zh(supports(record.data)) }}</p>
            <p v-for="r in record.data.result_contexts" :key="r.result_id">{{ zh(r.semantic_id) }} · {{ zh(r.scope.description) }}</p>
            <p><strong>{{ zh("Method:") }}</strong> {{ zh(factText(record.data.method_name)) }}</p>
            <p class="hash"><strong>{{ zh("Method hash:") }}</strong> {{ zh(factText(record.data.method_hash)) }}</p>
            <p class="hash"><strong>{{ zh("Recorded source hash:") }}</strong> {{ zh(factText(record.data.recorded_source_hash)) }}<br><strong>{{ zh("Current source hash:") }}</strong> {{ zh(factText(record.data.current_source_hash)) }}</p>
            <p><strong>{{ zh("Freeze reference:") }}</strong> {{ zh(knownValue(record.data.freeze_reference)?.freeze_id ?? factText(record.data.freeze_reference)) }}</p>
            <EvidenceStatus primary :verification="record.data.verification" :drift="record.data.source_drift" :origins="record.data.result_contexts.map(r => r.data_origin)" />
            <p><strong>{{ zh("Source summary:") }}</strong> {{ zh(record.data.source_assets.length) }} {{ zh("registered assets") }}</p>
            <ul><li v-for="asset in record.data.source_assets" :key="asset.asset_id">{{ zh(asset.role) }} · {{ zh(asset.source_display) }}<p v-if="knownValue(asset.data_drift) === true" class="hash">{{ zh("SOURCE DRIFT · Recorded data hash:") }} {{ zh(factText(asset.recorded_data_hash)) }}<br>{{ zh("Current data hash:") }} {{ zh(factText(asset.current_data_hash)) }}</p></li></ul>
            <p><strong>{{ zh("Important limitations:") }}</strong></p>
            <ul><li v-for="lim in record.data.limitations" :key="lim.id">{{ zh(lim.severity) }} · {{ zh(lim.code) }} — {{ zh(lim.description) }}</li></ul>
            <p v-if="!record.data.limitations.length">{{ zh("No limitations recorded; this does not establish unrestricted support.") }}</p>
          </template>
        </LoadStateBlock>
        <p>{{ zh("Evidence records can remain inspectable when source-data drift blocks a scientific result. An evidence response does not certify numerical availability.") }}</p>
        <RouterLink :to="quickView.target" data-testid="quick-full-record">{{ zh("View full record →") }}</RouterLink>
      </section>
    </div>
  </Teleport>
</template>
<style scoped>
.evidence-overlay { position: fixed; inset: 0; background: #0006; z-index: 1000; display: flex; justify-content: flex-end; }
.evidence-drawer { width: min(40rem, 100%); overflow: auto; background: white; padding: 1.5rem; box-sizing: border-box; }
.evidence-drawer h3, .hash { overflow-wrap: anywhere; } .evidence-drawer li { margin: .4rem 0; }
</style>
