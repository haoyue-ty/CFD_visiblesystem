<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { verificationText } from "../../data/evidence"
import type { Science, Definitions } from '../../data/cylinder'
import { known } from '../../data/cylinder'
import EvidenceLink from '../../scientific/EvidenceLink.vue'
defineProps<{ result: Science['ScientificResult']; definitions: Definitions }>()
</script>
<template>
  <dl class="facts">
    <dt>{{ zh("Definition") }}</dt><dd>{{ zh(definitions.find(d => d.semantic_id === result.semantic_id)?.definition ?? 'Definition unavailable') }} <code>{{ zh(result.semantic_id) }}</code></dd>
    <dt>{{ zh("Unit") }}</dt><dd>{{ zh(result.unit.label) }} ({{ zh(result.unit.system) }})</dd>
    <dt>{{ zh("Scope") }}</dt><dd>{{ zh(result.scope.description) }} · {{ zh(known(result.scope.boundary_scope) ?? 'UNKNOWN') }}</dd>
    <dt>{{ zh("Time semantics") }}</dt><dd>{{ zh(result.time.sampling) }} · {{ zh(result.time.accumulation) }} · t={{ zh(known(result.time.physical_time) ?? 'N/A') }} {{ zh("· interval=") }}{{ zh(known(result.time.interval) ?? 'N/A') }} {{ zh("· completed step=") }}{{ zh(known(result.time.step_index) ?? 'N/A') }}<br>{{ zh(result.time.index_convention) }}</dd>
    <dt>{{ zh("Origin / verification") }}</dt><dd>{{ zh(result.data_origin) }} · {{ zh(verificationText(result.verification)) }}</dd>
    <dt>{{ zh("Limitation") }}</dt><dd><template v-if="result.limitations.length"><p v-for="l in result.limitations" :key="l.id">{{ zh(l.code) }} — {{ zh(l.description) }}</p></template><template v-else>{{ zh("No additional result limitation recorded.") }}</template></dd>
  </dl>
  <footer><EvidenceLink v-for="id in result.provenance.evidence_refs.filter(id => id.startsWith('ev.'))" :key="id" :evidence-id="id" /></footer>
</template>
<style scoped>
.facts { display: grid; grid-template-columns: 9rem 1fr; gap: .3rem .7rem; font-size: .85rem; }
dd { margin: 0; overflow-wrap: anywhere; } dd p { margin: 0; } footer { display: flex; flex-wrap: wrap; gap: .7rem; }
</style>
