<script setup lang="ts">
import type { Science, Definitions } from '../../data/cylinder'
import { known } from '../../data/cylinder'
import EvidenceLink from '../../scientific/EvidenceLink.vue'
defineProps<{ result: Science['ScientificResult']; definitions: Definitions }>()
</script>
<template>
  <dl class="facts">
    <dt>Definition</dt><dd>{{ definitions.find(d => d.semantic_id === result.semantic_id)?.definition ?? 'Definition unavailable' }} <code>{{ result.semantic_id }}</code></dd>
    <dt>Unit</dt><dd>{{ result.unit.label }} ({{ result.unit.system }})</dd>
    <dt>Scope</dt><dd>{{ result.scope.description }} · {{ known(result.scope.boundary_scope) ?? 'UNKNOWN' }}</dd>
    <dt>Time semantics</dt><dd>{{ result.time.sampling }} · {{ result.time.accumulation }} · t={{ known(result.time.physical_time) ?? 'N/A' }} · interval={{ known(result.time.interval) ?? 'N/A' }} · completed step={{ known(result.time.step_index) ?? 'N/A' }}<br>{{ result.time.index_convention }}</dd>
    <dt>Origin / verification</dt><dd>{{ result.data_origin }} · {{ result.verification.status }}</dd>
    <dt>Limitation</dt><dd><template v-if="result.limitations.length"><p v-for="l in result.limitations" :key="l.id">{{ l.code }} — {{ l.description }}</p></template><template v-else>No additional result limitation recorded.</template></dd>
  </dl>
  <footer><EvidenceLink v-for="id in result.provenance.evidence_refs.filter(id => id.startsWith('ev.'))" :key="id" :evidence-id="id" /></footer>
</template>
<style scoped>
.facts { display: grid; grid-template-columns: 9rem 1fr; gap: .3rem .7rem; font-size: .85rem; }
dd { margin: 0; overflow-wrap: anywhere; } dd p { margin: 0; } footer { display: flex; flex-wrap: wrap; gap: .7rem; }
</style>
