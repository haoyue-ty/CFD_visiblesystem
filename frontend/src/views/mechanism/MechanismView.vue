<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { contentService, type MechanismContent } from '../../data/content'
import type { Loaded } from '../../data/domain'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'
import { evidenceService } from '../../data/evidence'
import type { components } from '../../types/generated/api'

withDefaults(defineProps<{ controlsEnabled?: boolean }>(), { controlsEnabled: true })
const route = useRoute()
const router = useRouter()
const content = ref<Loaded<MechanismContent> | null>(null)
const provenance = ref<Loaded<components['schemas']['ResultProvenance']> | null>(null)
const controller = new AbortController()
async function loadMechanism() {
  content.value = null
  try {
    content.value = await contentService.mechanism(controller.signal)
    if (content.value.data) provenance.value = await evidenceService.provenance(content.value.data.content_id, controller.signal)
  }
  catch (error) { if ((error as Error).name !== 'AbortError') throw error }
}
onMounted(loadMechanism)
onUnmounted(() => controller.abort())
const state = computed(() => route.query.state === 'WEAKLY_2D' ? 'WEAKLY_2D' : 'STRICT_1D')
const qat = computed(() => route.query.q_at === 'OFF' ? 'OFF' : 'ENABLED')
const selected = computed(() => content.value?.data?.nodes.find(n => n.id === route.query.node) ?? content.value?.data?.nodes.find(n => n.id === 'acoustic-gate'))
const output = computed(() => qat.value === 'OFF' ? 'Pathway disabled' : state.value === 'STRICT_1D' ? 'Inactive / zero' : 'Active — conditional on acoustic trigger')
function update(key: string, value: string) { return router.push({ query: { ...route.query, [key]: value } }) }
function select(event: Event, key: string) { void update(key, (event.target as HTMLSelectElement).value) }
const returnTo = computed(() => ({ name: route.name as string, params: route.params, query: { ...route.query } }))

// Coordinates only; graph identities, prose and directed edges come from CONTENT03.
const positions: Record<string, [number, number]> = {
  'interface-state': [380, 35], 'background-psd': [120, 135], 'acoustic-information': [380, 135],
  'tangential-content': [640, 135], 'acoustic-gate': [380, 245], 'q-aa': [290, 355],
  'q-at': [540, 355], 'normal-output': [290, 465], 'tangential-output': [540, 465],
  combiner: [290, 585], 'entropy-variable-mapping': [290, 695],
}
function position(id: string): [number, number] { return positions[id] ?? [640, 695] }
function edgePath(from: string, to: string) {
  const [x, y] = position(from), [tx, ty] = position(to)
  // Background bypasses the trigger and joins the combiner independently.
  if (from === 'background-psd' && to === 'combiner') return `M ${x} ${y + 34} V ${ty} H ${tx - 106}`
  if (from === 'tangential-content') return `M ${x} ${y + 34} H 715 V ${ty - 55} H ${tx} V ${ty - 38}`
  return `M ${x} ${y + 34} L ${tx} ${ty - 38}`
}
function role(id: string) { return id === 'acoustic-gate' ? 'TRIGGER' : ['normal-output', 'tangential-output'].includes(id) ? 'OUTPUT' : '' }
function nodeState(id: string) {
  if (id === 'acoustic-gate') return 'Acoustic trigger may remain nonzero'
  if (id === 'tangential-content') return state.value === 'STRICT_1D' ? 'Receiving content: zero' : 'Receiving content: nonzero'
  if (id === 'q-at') return qat.value === 'OFF' ? 'Pathway disabled' : 'Pathway enabled'
  if (id === 'tangential-output') return state.value === 'WEAKLY_2D' && qat.value === 'ENABLED' ? 'Active (conditional)' : output.value
  return ''
}
</script>

<template>
  <section data-testid="mechanism-view" class="mechanism">
    <p><strong data-testid="schematic-badge">{{ zh("SCHEMATIC") }}</strong> {{ zh("· Discrete explanatory states; no numerical simulation.") }}</p>
    <LoadStateBlock :loaded="content" :target="zh('mechanism content')">
      <div v-if="content?.data" class="workspace">
        <section :aria-label="zh('Mechanism architecture')">
          <h2>{{ zh("Mechanism architecture") }}</h2>
          <p>{{ zh("Dashed node =") }} <strong>{{ zh("TRIGGER") }}</strong>{{ zh("; solid output nodes =") }} <strong>{{ zh("OUTPUT") }}</strong>{{ zh(". Arrows show dependencies.") }}</p>
          <svg viewBox="0 0 770 745" role="group" :aria-label="zh('Schematic dissipation architecture')" data-testid="mechanism-architecture">
            <defs><marker id="mechanism-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#526477" /></marker></defs>
            <g v-for="edge in content.data.edges" :key="`${edge.from_node}:${edge.to_node}`" :data-from="edge.from_node" :data-to="edge.to_node">
              <title>{{ zh(edge.label) }}</title>
              <path :d="edgePath(edge.from_node, edge.to_node)" fill="none" stroke="#526477" stroke-width="2" marker-end="url(#mechanism-arrow)" />
            </g>
            <g v-for="node in content.data.nodes" :key="node.id" :transform="`translate(${position(node.id).join(',')})`"
              role="button" tabindex="0" :aria-label="`${zh(role(node.id))} ${zh(node.label)}`.trim()" :aria-pressed="selected?.id === node.id"
              :data-testid="`node-${node.id}`" :data-role="role(node.id)" :class="['node', { trigger: role(node.id) === 'TRIGGER', output: role(node.id) === 'OUTPUT', selected: selected?.id === node.id }]"
              @click="update('node', node.id)" @keydown.enter.prevent="update('node', node.id)" @keydown.space.prevent="update('node', node.id)">
              <title>{{ zh(node.explanation) }}</title>
              <rect x="-105" y="-34" width="210" height="68" rx="5" />
              <text v-if="role(node.id)" y="-17" class="role-label">{{ zh(role(node.id)) }}</text>
              <text :y="role(node.id) ? 2 : -3" text-anchor="middle">{{ zh(node.id === 'combiner' ? 'Dissipation combiner' : node.id === 'entropy-variable-mapping' ? 'Physical entropy variables' : node.label) }}</text>
              <text v-if="nodeState(node.id)" y="22" class="state-label">{{ zh(nodeState(node.id)) }}</text>
            </g>
          </svg>
          <p>{{ zh("Background PSD + normal acoustic + tangential output → entropy-scaled dissipation combiner → physical entropy-variable dissipation.") }}</p>
        </section>
        <aside>
          <section :aria-label="zh('Selected node explanation')" data-testid="selected-node">
            <h2>{{ zh(selected?.label) }}</h2>
            <strong>{{ zh(selected ? role(selected.id) : '') }}</strong>
            <p>{{ zh(selected?.explanation) }}</p>
            <p v-if="selected?.id === 'tangential-output'" data-testid="delta-t-not-gate">{{ zh("δ_t does not enter gate, but tangential receiving content affects output amplitude.") }}</p>
            <p v-if="selected?.id === 'acoustic-gate'">{{ zh("δ_t does not enter the acoustic gate J. J uses acoustic / normal information.") }}</p>
          </section>
          <section :aria-label="zh('Schematic state controls')">
            <h2>{{ zh("SCHEMATIC STATE") }}</h2>
            <template v-if="controlsEnabled">
              <label>{{ zh("State") }} <select data-testid="mechanism-state" :value="state" @change="select($event, 'state')"><option value="STRICT_1D">{{ zh("Strict 1D") }}</option><option value="WEAKLY_2D">{{ zh("Weakly 2D") }}</option></select></label>
              <label>q_at <select data-testid="mechanism-qat" :value="qat" @change="select($event, 'q_at')"><option value="OFF">{{ zh("Off") }}</option><option value="ENABLED">{{ zh("Enabled") }}</option></select></label>
            </template>
            <p v-else>{{ zh("Scene S2: select trigger / output nodes. State controls are available in S3 or the workspace.") }}</p>
            <dl aria-live="polite">
              <dt>{{ zh("State") }}</dt><dd>{{ zh(state === 'STRICT_1D' ? 'Strict 1D' : 'Weakly 2D') }}</dd>
              <dt>{{ zh("Acoustic gate J") }}</dt><dd data-testid="gate-state">{{ zh("Trigger retained — may be nonzero; q_at does not alter gate input.") }}</dd>
              <dt>{{ zh("Tangential receiving content") }}</dt><dd data-testid="receiving-state">{{ zh(state === 'STRICT_1D' ? 'zero' : 'nonzero') }}</dd>
              <dt>{{ zh("Cross-mode output") }}</dt><dd data-testid="output-state">{{ zh(output) }}</dd>
            </dl>
            <p>{{ zh("Enabled permits action; actual amplitude depends on receiving content and the acoustic trigger. No J or flux values are evaluated.") }}</p>
          </section>
          <section :aria-label="zh('Scientific limitations')" data-testid="mechanism-limitations">
            <h2>{{ zh("Scientific limitations · theory") }}</h2>
            <p>{{ zh("Under the theoretical assumptions, near-1D pathway action scales O(epsilon); entropy contribution scales O(epsilon^2).") }}</p>
            <p data-testid="near1d-gap"><strong>{{ zh("No authoritative five-epsilon raw numerical scan is registered.") }}</strong></p>
            <ul><li v-for="lim in content.data.limitations" :key="lim.id">{{ zh(lim.description) }}</li></ul>
          </section>
          <section :aria-label="zh('Mechanism evidence')" data-testid="mechanism-evidence">
            <h2>{{ zh("Evidence for selected node") }}</h2>
            <p><strong>{{ zh("Theory:") }}</strong> {{ zh("schematic explanations and conditional scaling; no numerical verification claim.") }}</p>
            <p><strong>{{ zh("Implementation:") }}</strong> {{ zh("frozen production method and source hash in the linked record.") }}</p>
            <p><strong>{{ zh("Numerical result:") }}</strong> {{ zh("linked spectra retain their own verification; they do not certify Near-1D scaling or this schematic as CFD numerical verification.") }}</p>
            <LoadStateBlock :loaded="provenance" :target="zh('mechanism provenance')">
              <div v-for="record in provenance?.data?.evidence_records" :key="record.evidence_id" class="evidence-actions">
                <EvidenceLink :evidence-id="record.evidence_id" context="mechanism" :return-to="returnTo" />
              </div>
            </LoadStateBlock>
            <p>{{ zh("Related numerical evidence retains separate result scope:") }}</p>
            <div v-for="id in content.data.evidence_refs" :key="id" class="evidence-actions">
              <EvidenceLink :evidence-id="id" context="mechanism" :return-to="returnTo" />
            </div>
          </section>
        </aside>
      </div>
    </LoadStateBlock>
    <button v-if="content?.state === 'ERROR'" @click="loadMechanism">{{ zh("Retry real API") }}</button>
  </section>
</template>

<style scoped>
.workspace { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(20rem, 1fr); gap: 1.5rem; }
svg { width: 100%; min-width: 32rem; }
.workspace > section { overflow-x: auto; }
aside section { border-top: 1px solid #ccc; padding: .75rem 0; }
h2 { font-size: 1.1rem; }
p, li, dl { font-size: .9rem; line-height: 1.5; }
label { display: block; margin: .5rem 0; }
select { margin-left: .5rem; padding: .3rem; }
dd { margin: 0 0 .5rem; font-weight: 600; }
.node { cursor: pointer; }
.node rect { fill: #f5f7fa; stroke: #526477; stroke-width: 2; }
.node.trigger rect { stroke: #8a5400; stroke-dasharray: 7 4; fill: #fff5dd; }
.node.output rect { stroke: #1a4f8a; stroke-width: 3; fill: #e8f2ff; }
.node.selected rect, .node:focus rect { stroke: #111; stroke-width: 4; }
.node text { font-size: 13px; pointer-events: none; }
.node .role-label { font-size: 11px; font-weight: bold; text-anchor: middle; }
.node .state-label { font-size: 10px; text-anchor: middle; }
.evidence-actions { display: flex; align-items: center; gap: .75rem; }
.hash { overflow-wrap: anywhere; }
@media (max-width: 850px) { .workspace { grid-template-columns: 1fr; } }
</style>
