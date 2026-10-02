<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createRequestGuard, type Loaded } from '../../data'
import { evidenceService, factText, knownValue, nonNumerical, supports, type EvidenceRecord } from '../../data/evidence'
import { returnContext } from './returnContext'
import EvidenceStatus from './EvidenceStatus.vue'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
const props = withDefaults(defineProps<{ evidence_id: string; embedded?: boolean }>(), { embedded: false })
const route = useRoute(), router = useRouter(), guard = createRequestGuard()
const detail = ref<Loaded<EvidenceRecord> | null>(null)
const backTarget = computed(() => returnContext(route.query.back))
const record = computed(() => detail.value?.data)
const config = computed(() => record.value ? knownValue(record.value.config) : null)
const freeze = computed(() => record.value ? knownValue(record.value.freeze_reference) : null)
const successor = computed(() => record.value ? knownValue(record.value.superseded_by) : null)
const configRows = computed(() => {
  const c = config.value
  const parameter = (name: string) => c?.parameters.find(p => p.name === name)
  const missing = 'Unknown — no recorded configuration field'
  return [
    ...['q_aa', 'q_at', 'gate', 'CFL'].map(name => ({ name, value: parameter(name) ? factText(parameter(name)!.value) : missing })),
    ...['grid', 'final_time', 'integrator', 'reconstruction', 'boundary_scope'].map(name => ({ name,
      value: c ? factText(c.protocol[name as keyof Pick<typeof c.protocol, 'grid' | 'final_time' | 'integrator' | 'reconstruction' | 'boundary_scope'>]) : missing })),
    ...(c?.parameters.filter(p => !['q_aa', 'q_at', 'gate', 'CFL'].includes(p.name)).map(p => ({ name: p.name, value: factText(p.value) })) ?? []),
  ]
})
async function load() {
  detail.value = null
  const result = await guard.run(signal => evidenceService.record(props.evidence_id, signal))
  if (result) detail.value = result
}
watch(() => props.evidence_id, load, { immediate: true })
onBeforeUnmount(() => guard.cancel())
function goBack() {
  if (!backTarget.value) return
  if (router.options.history.state.back === router.resolve(backTarget.value).fullPath) router.back()
  else void router.push(backTarget.value)
}
function relation(id: string) { return { name: 'evidence', params: { evidence_id: id }, query: { ...route.query, selection: undefined } } }
</script>
<template>
  <section data-testid="evidence-detail-view" class="evd">
    <nav v-if="!embedded" aria-label="Breadcrumb">
      <RouterLink :to="{ name: 'home' }">Home</RouterLink> → <RouterLink :to="{ name: 'evidence-center' }">Evidence Center</RouterLink> → {{ evidence_id }}
    </nav>
    <p v-if="!embedded">
      <button v-if="backTarget" data-testid="back-to-result" @click="goBack">← Back to {{ (backTarget as { name?: string }).name === 'evidence-center' ? 'Evidence Center' : 'result' }}</button>
      <RouterLink v-else :to="{ name: 'lab' }" data-testid="back-to-lab">← Back to Lab</RouterLink>
    </p>
    <section v-if="route.query.from === 'mechanism'" data-testid="mechanism-evidence-context">
      <h2>Mechanism explanation evidence</h2>
      <p>Theory and implementation evidence retains its own scope. Linked numerical records keep their own verification; they do not certify the schematic as CFD numerical verification or authoritative Near-1D asymptotic scaling.</p>
      <p>No authoritative five-epsilon raw numerical scan is registered.</p>
    </section>
    <LoadStateBlock :loaded="detail" target="evidence record">
      <article v-if="record" data-testid="evidence-record">
        <h1>Evidence: {{ record.evidence_id }}</h1>
        <p v-if="route.query.selection === 'HISTORY' || ['LEGACY', 'SUPERSEDED'].includes(record.verification.status)" class="historical" data-testid="evidence-historical"><strong>HISTORY — historical / nonselected record, outside the current formal selection.</strong></p>
        <h2>Verification</h2>
        <EvidenceStatus primary :verification="record.verification" :drift="record.source_drift" :origins="record.result_contexts.map(r => r.data_origin)" />
        <p class="inspectable" data-testid="evidence-inspectability">Evidence records can remain inspectable even when a scientific result is blocked because of source-data drift. An EVI02 response does not establish Numerical Result Available.</p>
        <section>
          <h2>Result identity · supports / does not support</h2>
          <dl>
            <dt>Evidence identity</dt><dd>{{ record.evidence_id }}</dd>
            <dt>Experiment</dt><dd data-testid="evidence-experiment">{{ factText(record.experiment_id) }}</dd>
            <dt>Config</dt><dd data-testid="evidence-config">{{ factText(record.config_id) }}</dd>
            <dt>Schema version</dt><dd>{{ record.schema_version }}</dd>
            <dt>Result count</dt><dd>{{ record.result_ids.length }}</dd>
          </dl>
          <p v-if="nonNumerical(record)" data-testid="evidence-non-numerical"><strong>NON-NUMERICAL EVIDENCE</strong> · no registered numerical result context. This record describes source/content provenance or a known gap.</p>
          <p><strong>Supports:</strong> {{ supports(record) }}</p>
          <p><strong>Does not support:</strong> Claims outside the recorded definitions, scope and source selection. {{ record.limitations.map(l => l.description).join('; ') }}</p>
          <article v-for="r in record.result_contexts" :key="r.result_id" class="subrecord" data-testid="evidence-result-context">
            <h3>{{ r.result_id }}</h3>
            <p>Experiment / config: {{ r.experiment_id }} / {{ r.config_id }} · Origin: {{ r.data_origin }}</p>
            <p>Semantic: {{ r.semantic_id }} · Unit: {{ r.unit.label }} ({{ r.unit.system }})</p>
            <p>Scope: {{ r.scope.description }} · Boundary: {{ factText(r.scope.boundary_scope) }}</p>
            <p>Time: {{ r.time.sampling }} / {{ r.time.accumulation }} · {{ r.time.index_convention }}</p>
            <p>Physical time: {{ factText(r.time.physical_time) }} · Interval: {{ factText(r.time.interval) }}</p>
            <p>Result verification: {{ r.verification.status }} · Dependency drift: {{ factText(r.provenance.source_drift) }}</p>
            <p>Step: {{ factText(r.time.step_index) }} · Stage: {{ factText(r.time.stage_index) }} · Snapshot: {{ factText(r.time.snapshot_index) }}</p>
            <ul><li v-for="lim in r.limitations" :key="lim.id">{{ lim.severity }} · {{ lim.code }} — {{ lim.description }}</li></ul>
          </article>
        </section>
        <section data-testid="evidence-method">
          <h2>Method &amp; source</h2>
          <dl>
            <dt>Method name</dt><dd>{{ factText(record.method_name) }}</dd>
            <dt>Method hash</dt><dd class="hash">{{ factText(record.method_hash) }}</dd>
            <dt>Recorded source hash</dt><dd class="hash">{{ factText(record.recorded_source_hash) }}</dd>
            <dt>Current source hash</dt><dd class="hash" data-testid="current-source-hash">{{ factText(record.current_source_hash) }}</dd>
            <dt>Data hash</dt><dd class="hash">{{ factText(record.data_hash) }}</dd>
            <dt>Source drift</dt><dd data-testid="evidence-drift">{{ knownValue(record.source_drift) === false ? 'No' : knownValue(record.source_drift) === true ? 'SOURCE DRIFT — recorded and current source differ' : factText(record.source_drift) }}</dd>
          </dl>
          <ul><li v-for="b in record.verification.basis" :key="b">{{ b }}</li></ul>
          <p>Created time: {{ factText(record.created_at) }} · Verified time: {{ factText(record.verified_at) }}</p>
        </section>
        <section data-testid="evidence-configuration">
          <h2>Configuration</h2>
          <p>{{ config ? `${config.name} · ${config.id}` : factText(record.config) }}</p>
          <table data-testid="evidence-params"><tbody><tr v-for="p in configRows" :key="p.name"><th>{{ p.name }}</th><td>{{ p.value }}</td></tr></tbody></table>
        </section>
        <section>
          <h2>Source assets</h2>
          <p>Controlled provenance descriptions only. Scientific files are not opened or downloaded.</p>
          <table data-testid="evidence-assets"><thead><tr><th>Asset</th><th>Role / format</th><th>Verification / drift</th></tr></thead><tbody>
            <tr v-for="a in record.source_assets" :key="a.asset_id"><td>{{ a.asset_id }} · {{ a.source_display }}</td><td>{{ a.role }} / {{ a.format }}</td><td>{{ a.verification.status }} / {{ factText(a.data_drift) }}</td></tr>
          </tbody></table>
          <p v-if="!record.source_assets.length">No source assets registered.</p>
          <article v-for="a in record.source_assets" :key="a.asset_id" class="subrecord" data-testid="evidence-source-asset">
            <h3>{{ a.asset_id }}</h3>
            <dl>
              <dt>Role / source identity</dt><dd>{{ a.role }} / {{ a.source_id }}</dd>
              <dt>Source display</dt><dd>{{ a.source_display }}</dd>
              <dt>Relative origin</dt><dd>{{ factText(a.relative_origin) }}</dd>
              <dt>Format</dt><dd>{{ a.format }}</dd>
              <dt>Recorded data hash</dt><dd class="hash">{{ factText(a.recorded_data_hash) }}</dd>
              <dt>Current data hash</dt><dd class="hash">{{ factText(a.current_data_hash) }}</dd>
              <dt>Canonical selected</dt><dd>{{ a.canonical_selected ? 'YES' : 'NO' }}</dd>
            </dl>
            <EvidenceStatus :verification="a.verification" :drift="a.data_drift" />
            <ul><li v-for="lim in a.limitations" :key="lim.id">{{ lim.severity }} / {{ lim.code }} — {{ lim.description }}</li></ul>
          </article>
          <h3>Recorded / current source observations</h3>
          <article v-for="o in record.source_observations" :key="o.asset_id" class="subrecord">
            <p>{{ o.asset_id }} · Drift: {{ factText(o.drift) }} · Observation time: {{ factText(o.observation_at) }}</p>
            <p class="hash">Recorded: {{ factText(o.recorded_hash) }}<br>Current: {{ factText(o.current_hash) }}</p>
          </article>
        </section>
        <section data-testid="evidence-freeze">
          <h2>Freeze</h2>
          <dl v-if="freeze">
            <dt>Freeze reference</dt><dd>{{ freeze.freeze_id }}</dd>
            <dt>Manifest identity</dt><dd>{{ freeze.manifest_asset_id }}</dd>
            <dt>Recorded time</dt><dd>{{ factText(freeze.recorded_at) }}</dd>
            <dt>Manifest hash</dt><dd class="hash">{{ factText(freeze.hash) }}</dd>
          </dl>
          <p v-else>{{ factText(record.freeze_reference) }}</p>
        </section>
        <section data-testid="evidence-processing">
          <h2>Processing lineage</h2>
          <p>Registered kinds: FORMAT_MAPPING · METADATA_CORRECTION · VERIFIED_DERIVATION · DISPLAY_ONLY. Only actual processing records follow.</p>
          <p v-if="!record.processing.length">No processing records registered.</p>
          <article v-for="p in record.processing" :key="p.id" class="subrecord">
            <h3>{{ p.kind }} · {{ p.id }}</h3><p>{{ p.description }}</p>
            <p>Input assets: {{ p.input_asset_ids.join(', ') || 'None recorded' }}</p>
            <p>Definition references: {{ p.definition_refs.join(', ') || 'None recorded' }}</p>
            <p class="hash">Processing hash: {{ factText(p.processing_hash) }}</p>
            <p>Verification: {{ p.verification.status }} · {{ p.verification.basis.join('; ') }}</p>
          </article>
        </section>
        <section data-testid="evidence-definitions">
          <h2>Scientific definitions</h2>
          <p v-if="!record.definitions.length">Unknown — no scientific definitions registered.</p>
          <article v-for="d in record.definitions" :key="d.id" class="subrecord">
            <h3>{{ d.title }} · {{ d.id }}</h3><p>{{ d.definition }}</p>
            <dl>
              <dt>Semantic</dt><dd>{{ d.semantic_id }}</dd>
              <dt>Unit</dt><dd>{{ d.unit.label }} · {{ d.unit.system }} · {{ d.unit.quantity }} · SI mapping: {{ factText(d.unit.si_mapping) }}</dd>
              <dt>Time rule</dt><dd>{{ d.time_rule }}</dd>
              <dt>Spatial rule</dt><dd>{{ d.spatial_rule }}</dd>
              <dt>Mask</dt><dd>{{ d.mask_refs.join(', ') || 'None recorded' }}</dd>
              <dt>Detector / scope</dt><dd>{{ factText(d.detector) }}</dd>
            </dl>
            <ul><li v-for="lim in d.limitations" :key="lim.id">{{ lim.code }} — {{ lim.description }}</li></ul>
          </article>
          <article v-for="m in record.masks" :key="m.id" class="subrecord">
            <h3>Mask: {{ m.id }} · {{ m.type }}</h3><p>{{ m.definition }}</p><p>{{ m.scope.description }}</p>
            <p>Parameters: {{ m.parameters.map(p => `${p.name}: ${factText(p.value)}`).join('; ') }}</p>
            <p>Domains: {{ m.domain_refs.join(', ') }} · Verification: {{ m.verification.status }}</p>
            <p v-for="s in m.index_sets" :key="s.axis">{{ s.axis }}: {{ s.indices.join(', ') }} · index base {{ s.index_base }}</p>
            <p>Array references: {{ m.mask_array_refs.map(a => `${a.result_id} / ${a.descriptor.array_id}`).join(', ') || 'None recorded' }}</p>
          </article>
        </section>
        <section data-testid="evidence-limitations">
          <h2>Limitations</h2>
          <ul><li v-for="lim in record.limitations" :key="lim.id"><strong>{{ lim.severity }} · {{ lim.code }}</strong> — {{ lim.description }}<br>Affected: {{ lim.affected_refs.join(', ') || 'Not enumerated' }}</li></ul>
          <p v-if="!record.limitations.length">No limitations registered; support is still bounded by recorded definitions and scope.</p>
        </section>
        <section data-testid="evidence-relations">
          <h2>Relations</h2>
          <h3>Related evidence</h3>
          <ul><li v-for="id in record.related_evidence_refs" :key="id"><RouterLink :to="relation(id)">{{ id }}</RouterLink></li></ul>
          <p v-if="!record.related_evidence_refs.length">No related evidence registered.</p>
          <h3>Parent / source results</h3>
          <p>No separate parent-result field is recorded. Registered result/source bindings:</p>
          <ul><li v-for="r in record.result_contexts" :key="r.result_id">{{ r.result_id }} · Source assets: {{ r.provenance.source_asset_ids.join(', ') }} · Evidence: <RouterLink v-for="id in r.provenance.evidence_refs" :key="id" :to="relation(id)">{{ id }} </RouterLink></li></ul>
          <p>Superseded by: <RouterLink v-if="successor" :to="relation(successor)">{{ successor }} → associated successor evidence</RouterLink><span v-else>{{ factText(record.superseded_by) }}</span></p>
        </section>
      </article>
    </LoadStateBlock>
    <button v-if="detail?.state === 'ERROR'" @click="load">Retry evidence record</button>
    <section v-if="detail?.state === 'MISSING'" data-testid="evidence-fallback"><h1>Evidence record not found</h1><p>{{ detail.reason }}</p><RouterLink :to="{ name: 'evidence-center' }">Back to Evidence Center</RouterLink></section>
  </section>
</template>
<style scoped>
.evd { max-width: 65rem; margin: auto; padding: 1.5rem; overflow-wrap: anywhere; } .evd section { border-top: 1px solid #ddd; padding: 1rem 0; }
.evd h1 { font-size: 1.4rem; } .evd h2 { font-size: 1.15rem; } .evd h3 { font-size: 1rem; }
dl { display: grid; grid-template-columns: minmax(9rem, 12rem) 1fr; gap: .4rem 1rem; } dt { color: #555; } dd { margin: 0; }
.hash { font-family: monospace; font-size: .85rem; } table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid #ddd; text-align: left; padding: .5rem; }
.subrecord { border: 1px solid #ddd; padding: .75rem; margin: .75rem 0; } .inspectable { background: #f0f5fa; padding: .8rem; }
.historical { border-left: .4rem solid #775936; background: #f8f5ef; padding: .75rem; }
li { margin: .4rem 0; } @media (max-width: 600px) { dl { grid-template-columns: 1fr; } .evd { padding: 1rem; } }
</style>
