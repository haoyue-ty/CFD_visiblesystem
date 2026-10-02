<script setup lang="ts">
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
        <button data-testid="quick-close" @click="closeEvidence">Close quick view</button>
        <h2 id="quick-title">Evidence Quick View</h2>
        <LoadStateBlock :loaded="record" target="evidence quick view">
          <template v-if="record?.data">
            <h3>{{ record.data.evidence_id }}</h3>
            <p data-testid="quick-identity"><strong>Result identity:</strong> {{ record.data.result_ids.join(', ') || 'No numerical result identity — provenance / content record' }}</p>
            <p v-if="nonNumerical(record.data)" data-testid="quick-non-numerical">NON-NUMERICAL EVIDENCE · no numerical availability claim.</p>
            <p><strong>Experiment / config:</strong> {{ factText(record.data.experiment_id) }} / {{ factText(record.data.config_id) }}</p>
            <p><strong>Semantic / scope:</strong> {{ supports(record.data) }}</p>
            <p v-for="r in record.data.result_contexts" :key="r.result_id">{{ r.semantic_id }} · {{ r.scope.description }}</p>
            <p><strong>Method:</strong> {{ factText(record.data.method_name) }}</p>
            <p class="hash"><strong>Method hash:</strong> {{ factText(record.data.method_hash) }}</p>
            <p class="hash"><strong>Recorded source hash:</strong> {{ factText(record.data.recorded_source_hash) }}<br><strong>Current source hash:</strong> {{ factText(record.data.current_source_hash) }}</p>
            <p><strong>Freeze reference:</strong> {{ knownValue(record.data.freeze_reference)?.freeze_id ?? factText(record.data.freeze_reference) }}</p>
            <EvidenceStatus primary :verification="record.data.verification" :drift="record.data.source_drift" :origins="record.data.result_contexts.map(r => r.data_origin)" />
            <p><strong>Source summary:</strong> {{ record.data.source_assets.length }} registered assets</p>
            <ul><li v-for="asset in record.data.source_assets" :key="asset.asset_id">{{ asset.role }} · {{ asset.source_display }}<p v-if="knownValue(asset.data_drift) === true" class="hash">SOURCE DRIFT · Recorded data hash: {{ factText(asset.recorded_data_hash) }}<br>Current data hash: {{ factText(asset.current_data_hash) }}</p></li></ul>
            <p><strong>Important limitations:</strong></p>
            <ul><li v-for="lim in record.data.limitations" :key="lim.id">{{ lim.severity }} · {{ lim.code }} — {{ lim.description }}</li></ul>
            <p v-if="!record.data.limitations.length">No limitations recorded; this does not establish unrestricted support.</p>
          </template>
        </LoadStateBlock>
        <p>Evidence records can remain inspectable when source-data drift blocks a scientific result. An evidence response does not certify numerical availability.</p>
        <RouterLink :to="quickView.target" data-testid="quick-full-record">View full record →</RouterLink>
      </section>
    </div>
  </Teleport>
</template>
<style scoped>
.evidence-overlay { position: fixed; inset: 0; background: #0006; z-index: 1000; display: flex; justify-content: flex-end; }
.evidence-drawer { width: min(40rem, 100%); overflow: auto; background: white; padding: 1.5rem; box-sizing: border-box; }
.evidence-drawer h3, .hash { overflow-wrap: anywhere; } .evidence-drawer li { margin: .4rem 0; }
</style>
