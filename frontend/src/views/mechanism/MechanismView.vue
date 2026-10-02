<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { contentService, type MechanismContent, type MechanismEvidence } from '../../data/content'
import type { Loaded } from '../../data/domain'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'

withDefaults(defineProps<{ controlsEnabled?: boolean }>(), { controlsEnabled: true })
const route = useRoute()
const router = useRouter()
const content = ref<Loaded<MechanismContent> | null>(null)
const evidence = ref<Loaded<MechanismEvidence> | null>(null)
const quickOpen = ref(false)
const controller = new AbortController()
async function loadMechanism() {
  content.value = null
  try { content.value = await contentService.mechanism(controller.signal) }
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
async function quickEvidence(id: string) {
  quickOpen.value = true
  evidence.value = { state: 'LOADING', data: null, origin: 'VERIFIED_PRODUCTION', reason: null }
  try { evidence.value = await contentService.evidence(id, controller.signal) }
  catch (error) { if ((error as Error).name !== 'AbortError') throw error }
}

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
    <p><strong data-testid="schematic-badge">SCHEMATIC</strong> · Discrete explanatory states; no numerical simulation.</p>
    <LoadStateBlock :loaded="content" target="mechanism content">
      <div v-if="content?.data" class="workspace">
        <section aria-label="Mechanism architecture">
          <h2>Mechanism architecture</h2>
          <p>Dashed node = <strong>TRIGGER</strong>; solid output nodes = <strong>OUTPUT</strong>. Arrows show dependencies.</p>
          <svg viewBox="0 0 770 745" role="group" aria-label="Schematic dissipation architecture" data-testid="mechanism-architecture">
            <defs><marker id="mechanism-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#526477" /></marker></defs>
            <g v-for="edge in content.data.edges" :key="`${edge.from_node}:${edge.to_node}`" :data-from="edge.from_node" :data-to="edge.to_node">
              <title>{{ edge.label }}</title>
              <path :d="edgePath(edge.from_node, edge.to_node)" fill="none" stroke="#526477" stroke-width="2" marker-end="url(#mechanism-arrow)" />
            </g>
            <g v-for="node in content.data.nodes" :key="node.id" :transform="`translate(${position(node.id).join(',')})`"
              role="button" tabindex="0" :aria-label="`${role(node.id)} ${node.label}`" :aria-pressed="selected?.id === node.id"
              :data-testid="`node-${node.id}`" :data-role="role(node.id)" :class="['node', { trigger: role(node.id) === 'TRIGGER', output: role(node.id) === 'OUTPUT', selected: selected?.id === node.id }]"
              @click="update('node', node.id)" @keydown.enter.prevent="update('node', node.id)" @keydown.space.prevent="update('node', node.id)">
              <title>{{ node.explanation }}</title>
              <rect x="-105" y="-34" width="210" height="68" rx="5" />
              <text v-if="role(node.id)" y="-17" class="role-label">{{ role(node.id) }}</text>
              <text :y="role(node.id) ? 2 : -3" text-anchor="middle">{{ node.id === 'combiner' ? 'Dissipation combiner' : node.id === 'entropy-variable-mapping' ? 'Physical entropy variables' : node.label }}</text>
              <text v-if="nodeState(node.id)" y="22" class="state-label">{{ nodeState(node.id) }}</text>
            </g>
          </svg>
          <p>Background PSD + normal acoustic + tangential output → entropy-scaled dissipation combiner → physical entropy-variable dissipation.</p>
        </section>
        <aside>
          <section aria-label="Selected node explanation" data-testid="selected-node">
            <h2>{{ selected?.label }}</h2>
            <strong>{{ selected ? role(selected.id) : '' }}</strong>
            <p>{{ selected?.explanation }}</p>
            <p v-if="selected?.id === 'tangential-output'" data-testid="delta-t-not-gate">δ_t does not enter gate, but tangential receiving content affects output amplitude.</p>
            <p v-if="selected?.id === 'acoustic-gate'">δ_t does not enter the acoustic gate J. J uses acoustic / normal information.</p>
          </section>
          <section aria-label="Schematic state controls">
            <h2>SCHEMATIC STATE</h2>
            <template v-if="controlsEnabled">
              <label>State <select data-testid="mechanism-state" :value="state" @change="select($event, 'state')"><option value="STRICT_1D">Strict 1D</option><option value="WEAKLY_2D">Weakly 2D</option></select></label>
              <label>q_at <select data-testid="mechanism-qat" :value="qat" @change="select($event, 'q_at')"><option value="OFF">Off</option><option value="ENABLED">Enabled</option></select></label>
            </template>
            <p v-else>Scene S2: select trigger / output nodes. State controls are available in S3 or the workspace.</p>
            <dl aria-live="polite">
              <dt>State</dt><dd>{{ state === 'STRICT_1D' ? 'Strict 1D' : 'Weakly 2D' }}</dd>
              <dt>Acoustic gate J</dt><dd data-testid="gate-state">Trigger retained — may be nonzero; q_at does not alter gate input.</dd>
              <dt>Tangential receiving content</dt><dd data-testid="receiving-state">{{ state === 'STRICT_1D' ? 'zero' : 'nonzero' }}</dd>
              <dt>Cross-mode output</dt><dd data-testid="output-state">{{ output }}</dd>
            </dl>
            <p>Enabled permits action; actual amplitude depends on receiving content and the acoustic trigger. No J or flux values are evaluated.</p>
          </section>
          <section aria-label="Scientific limitations" data-testid="mechanism-limitations">
            <h2>Scientific limitations · theory</h2>
            <p>Under the theoretical assumptions, near-1D pathway action scales O(epsilon); entropy contribution scales O(epsilon^2).</p>
            <p data-testid="near1d-gap"><strong>No authoritative five-epsilon raw numerical scan is registered.</strong></p>
            <ul><li v-for="lim in content.data.limitations" :key="lim.id">{{ lim.description }}</li></ul>
          </section>
          <section aria-label="Mechanism evidence" data-testid="mechanism-evidence">
            <h2>Evidence for selected node</h2>
            <p><strong>Theory:</strong> schematic explanations and conditional scaling; no numerical verification claim.</p>
            <p><strong>Implementation:</strong> frozen production method and source hash in the linked record.</p>
            <p><strong>Numerical result:</strong> linked spectra retain their own verification; they do not certify Near-1D scaling or this schematic as CFD numerical verification.</p>
            <div v-for="id in content.data.evidence_refs" :key="id" class="evidence-actions">
              <button data-testid="evidence-quick" @click="quickEvidence(id)">Evidence quick</button>
              <EvidenceLink :evidence-id="id" context="mechanism" :return-to="returnTo" />
            </div>
            <section v-if="quickOpen" aria-label="Evidence quick view" data-testid="evidence-quick-view">
              <button @click="quickOpen = false">Close quick view</button>
              <LoadStateBlock :loaded="evidence" target="mechanism evidence">
                <template v-if="evidence?.data">
                  <p>{{ evidence.data.evidence_id }}</p>
                  <p>Record verification: {{ evidence.data.verification.status }} (linked result / sources).</p>
                  <p>Implementation method: {{ evidence.data.method_name.state === 'KNOWN' ? evidence.data.method_name.value : 'UNKNOWN' }}</p>
                  <p class="hash">Method hash: {{ evidence.data.method_hash.state === 'KNOWN' ? evidence.data.method_hash.value : 'UNKNOWN' }}</p>
                  <ul><li v-for="lim in evidence.data.limitations" :key="lim.id">{{ lim.description }}</li></ul>
                </template>
              </LoadStateBlock>
            </section>
          </section>
        </aside>
      </div>
    </LoadStateBlock>
    <button v-if="content?.state === 'ERROR'" @click="loadMechanism">Retry real API</button>
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
