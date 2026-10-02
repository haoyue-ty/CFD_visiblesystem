<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { verificationText } from "../../data/evidence"
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
    <nav v-if="!embedded" :aria-label="zh('Breadcrumb')">
      <RouterLink :to="{ name: 'home' }">{{ zh("Home") }}</RouterLink> → <RouterLink :to="{ name: 'evidence-center' }">{{ zh("Evidence Center") }}</RouterLink> → {{ zh(evidence_id) }}
    </nav>
    <p v-if="!embedded">
      <button v-if="backTarget" data-testid="back-to-result" @click="goBack">← {{ (backTarget as { name?: string }).name === 'evidence-center' ? '返回证据中心' : (backTarget as { name?: string }).name === 'explore' ? '返回引导探索' : (backTarget as { name?: string }).name === 'cross-flow' ? '返回对比页面' : '返回实验' }}</button>
      <RouterLink v-else :to="{ name: 'lab' }" data-testid="back-to-lab">{{ zh("← Back to Lab") }}</RouterLink>
    </p>
    <section v-if="route.query.from === 'mechanism'" data-testid="mechanism-evidence-context">
      <h2>{{ zh("Mechanism explanation evidence") }}</h2>
      <p>{{ zh("Theory and implementation evidence retains its own scope. Linked numerical records keep their own verification; they do not certify the schematic as CFD numerical verification or authoritative Near-1D asymptotic scaling.") }}</p>
      <p>{{ zh("No authoritative five-epsilon raw numerical scan is registered.") }}</p>
    </section>
    <LoadStateBlock :loaded="detail" :target="zh('evidence record')">
      <article v-if="record" data-testid="evidence-record">
        <h1>{{ zh("Evidence:") }} {{ zh(record.evidence_id) }}</h1>
        <p v-if="route.query.selection === 'HISTORY' || ['LEGACY', 'SUPERSEDED'].includes(record.verification.status)" class="historical" data-testid="evidence-historical"><strong>{{ zh("HISTORY — historical / nonselected record, outside the current formal selection.") }}</strong></p>
        <h2>{{ zh("Verification") }}</h2>
        <EvidenceStatus primary :verification="record.verification" :drift="record.source_drift" :origins="record.result_contexts.map(r => r.data_origin)" />
        <p class="inspectable" data-testid="evidence-inspectability">{{ zh("Evidence records can remain inspectable even when a scientific result is blocked because of source-data drift. An EVI02 response does not establish Numerical Result Available.") }}</p>
        <section>
          <h2>{{ zh("Result identity · supports / does not support") }}</h2>
          <dl>
            <dt>{{ zh("Evidence identity") }}</dt><dd>{{ zh(record.evidence_id) }}</dd>
            <dt>{{ zh("Experiment") }}</dt><dd data-testid="evidence-experiment">{{ zh(factText(record.experiment_id)) }}</dd>
            <dt>{{ zh("Config") }}</dt><dd data-testid="evidence-config">{{ zh(factText(record.config_id)) }}</dd>
            <dt>{{ zh("Schema version") }}</dt><dd>{{ zh(record.schema_version) }}</dd>
            <dt>{{ zh("Result count") }}</dt><dd>{{ zh(record.result_ids.length) }}</dd>
          </dl>
          <p v-if="nonNumerical(record)" data-testid="evidence-non-numerical"><strong>{{ zh("NON-NUMERICAL EVIDENCE") }}</strong> {{ zh("· no registered numerical result context. This record describes source/content provenance or a known gap.") }}</p>
          <p><strong>{{ zh("Supports:") }}</strong> {{ zh(supports(record)) }}</p>
          <p><strong>{{ zh("Does not support:") }}</strong> {{ zh("Claims outside the recorded definitions, scope and source selection.") }} {{ zh(record.limitations.map(l => zh(l.description)).join('; ')) }}</p>
          <article v-for="r in record.result_contexts" :key="r.result_id" class="subrecord" data-testid="evidence-result-context">
            <h3>{{ zh(r.result_id) }}</h3>
            <p>{{ zh("Experiment / config:") }} {{ zh(r.experiment_id) }} / {{ zh(r.config_id) }} {{ zh("· Origin:") }} {{ zh(r.data_origin) }}</p>
            <p>{{ zh("Semantic:") }} {{ zh(r.semantic_id) }} {{ zh("· Unit:") }} {{ zh(r.unit.label) }} ({{ zh(r.unit.system) }})</p>
            <p>{{ zh("Scope:") }} {{ zh(r.scope.description) }} {{ zh("· Boundary:") }} {{ zh(factText(r.scope.boundary_scope)) }}</p>
            <p>{{ zh("Time:") }} {{ zh(r.time.sampling) }} / {{ zh(r.time.accumulation) }} · {{ zh(r.time.index_convention) }}</p>
            <p>{{ zh("Physical time:") }} {{ zh(factText(r.time.physical_time)) }} {{ zh("· Interval:") }} {{ zh(factText(r.time.interval)) }}</p>
            <p>{{ zh("Result verification:") }} {{ zh(verificationText(r.verification)) }} {{ zh("· Dependency drift:") }} {{ zh(factText(r.provenance.source_drift)) }}</p>
            <p>{{ zh("Step:") }} {{ zh(factText(r.time.step_index)) }} {{ zh("· Stage:") }} {{ zh(factText(r.time.stage_index)) }} {{ zh("· Snapshot:") }} {{ zh(factText(r.time.snapshot_index)) }}</p>
            <ul><li v-for="lim in r.limitations" :key="lim.id">{{ zh(lim.severity) }} · {{ zh(lim.code) }} — {{ zh(lim.description) }}</li></ul>
          </article>
        </section>
        <section data-testid="evidence-method">
          <h2>{{ zh("Method & source") }}</h2>
          <dl>
            <dt>{{ zh("Method name") }}</dt><dd>{{ zh(factText(record.method_name)) }}</dd>
            <dt>{{ zh("Method hash") }}</dt><dd class="hash">{{ zh(factText(record.method_hash)) }}</dd>
            <dt>{{ zh("Recorded source hash") }}</dt><dd class="hash">{{ zh(factText(record.recorded_source_hash)) }}</dd>
            <dt>{{ zh("Current source hash") }}</dt><dd class="hash" data-testid="current-source-hash">{{ zh(factText(record.current_source_hash)) }}</dd>
            <dt>{{ zh("Data hash") }}</dt><dd class="hash">{{ zh(factText(record.data_hash)) }}</dd>
            <dt>{{ zh("Source drift") }}</dt><dd data-testid="evidence-drift">{{ knownValue(record.source_drift) === false ? '记录时源码与当前源码一致' : knownValue(record.source_drift) === true ? '检测到源码变化：记录时与当前源码不同' : factText(record.source_drift) }}</dd>
          </dl>
          <ul><li v-for="b in record.verification.basis" :key="b">{{ zh(b) }}</li></ul>
          <p>{{ zh("Created time:") }} {{ zh(factText(record.created_at)) }} {{ zh("· Verified time:") }} {{ zh(factText(record.verified_at)) }}</p>
        </section>
        <section data-testid="evidence-configuration">
          <h2>{{ zh("Configuration") }}</h2>
          <p>{{ zh(config ? `${config.name} · ${config.id}` : factText(record.config)) }}</p>
          <table data-testid="evidence-params"><tbody><tr v-for="p in configRows" :key="p.name"><th>{{ zh(p.name) }}</th><td>{{ zh(p.value) }}</td></tr></tbody></table>
        </section>
        <section>
          <h2>{{ zh("Source assets") }}</h2>
          <p>{{ zh("Controlled provenance descriptions only. Scientific files are not opened or downloaded.") }}</p>
          <table data-testid="evidence-assets"><thead><tr><th>{{ zh("Asset") }}</th><th>{{ zh("Role / format") }}</th><th>{{ zh("Verification / drift") }}</th></tr></thead><tbody>
            <tr v-for="a in record.source_assets" :key="a.asset_id"><td>{{ zh(a.asset_id) }} · {{ zh(a.source_display) }}</td><td>{{ zh(a.role) }} / {{ zh(a.format) }}</td><td>{{ zh(verificationText(a.verification)) }} / {{ zh(factText(a.data_drift)) }}</td></tr>
          </tbody></table>
          <p v-if="!record.source_assets.length">{{ zh("No source assets registered.") }}</p>
          <article v-for="a in record.source_assets" :key="a.asset_id" class="subrecord" data-testid="evidence-source-asset">
            <h3>{{ zh(a.asset_id) }}</h3>
            <dl>
              <dt>{{ zh("Role / source identity") }}</dt><dd>{{ zh(a.role) }} / {{ zh(a.source_id) }}</dd>
              <dt>{{ zh("Source display") }}</dt><dd>{{ zh(a.source_display) }}</dd>
              <dt>{{ zh("Relative origin") }}</dt><dd>{{ zh(factText(a.relative_origin)) }}</dd>
              <dt>{{ zh("Format") }}</dt><dd>{{ zh(a.format) }}</dd>
              <dt>{{ zh("Recorded data hash") }}</dt><dd class="hash">{{ zh(factText(a.recorded_data_hash)) }}</dd>
              <dt>{{ zh("Current data hash") }}</dt><dd class="hash">{{ zh(factText(a.current_data_hash)) }}</dd>
              <dt>{{ zh("Canonical selected") }}</dt><dd>{{ zh(a.canonical_selected ? 'YES' : 'NO') }}</dd>
            </dl>
            <EvidenceStatus :verification="a.verification" :drift="a.data_drift" subject="数据" />
            <ul><li v-for="lim in a.limitations" :key="lim.id">{{ zh(lim.severity) }} / {{ zh(lim.code) }} — {{ zh(lim.description) }}</li></ul>
          </article>
          <h3>{{ zh("Recorded / current source observations") }}</h3>
          <article v-for="o in record.source_observations" :key="o.asset_id" class="subrecord">
            <p>{{ zh(o.asset_id) }} {{ zh("· Drift:") }} {{ zh(factText(o.drift)) }} {{ zh("· Observation time:") }} {{ zh(factText(o.observation_at)) }}</p>
            <p class="hash">{{ zh("Recorded:") }} {{ zh(factText(o.recorded_hash)) }}<br>{{ zh("Current:") }} {{ zh(factText(o.current_hash)) }}</p>
          </article>
        </section>
        <section data-testid="evidence-freeze">
          <h2>{{ zh("Freeze") }}</h2>
          <dl v-if="freeze">
            <dt>{{ zh("Freeze reference") }}</dt><dd>{{ zh(freeze.freeze_id) }}</dd>
            <dt>{{ zh("Manifest identity") }}</dt><dd>{{ zh(freeze.manifest_asset_id) }}</dd>
            <dt>{{ zh("Recorded time") }}</dt><dd>{{ zh(factText(freeze.recorded_at)) }}</dd>
            <dt>{{ zh("Manifest hash") }}</dt><dd class="hash">{{ zh(factText(freeze.hash)) }}</dd>
          </dl>
          <p v-else>{{ zh(factText(record.freeze_reference)) }}</p>
        </section>
        <section data-testid="evidence-processing">
          <h2>{{ zh("Processing lineage") }}</h2>
          <p>{{ zh("Registered kinds: FORMAT_MAPPING · METADATA_CORRECTION · VERIFIED_DERIVATION · DISPLAY_ONLY. Only actual processing records follow.") }}</p>
          <p v-if="!record.processing.length">{{ zh("No processing records registered.") }}</p>
          <article v-for="p in record.processing" :key="p.id" class="subrecord">
            <h3>{{ zh(p.kind) }} · {{ zh(p.id) }}</h3><p>{{ zh(p.description) }}</p>
            <p>{{ zh("Input assets:") }} {{ zh(p.input_asset_ids.join(', ') || 'None recorded') }}</p>
            <p>{{ zh("Definition references:") }} {{ zh(p.definition_refs.join(', ') || 'None recorded') }}</p>
            <p class="hash">{{ zh("Processing hash:") }} {{ zh(factText(p.processing_hash)) }}</p>
            <p>{{ zh("Verification:") }} {{ zh(verificationText(p.verification)) }} · {{ zh(p.verification.basis.map(zh).join('；')) }}</p>
          </article>
        </section>
        <section data-testid="evidence-definitions">
          <h2>{{ zh("Scientific definitions") }}</h2>
          <p v-if="!record.definitions.length">{{ zh("Unknown — no scientific definitions registered.") }}</p>
          <article v-for="d in record.definitions" :key="d.id" class="subrecord">
            <h3>{{ zh(d.title) }} · {{ zh(d.id) }}</h3><p>{{ zh(d.definition) }}</p>
            <dl>
              <dt>{{ zh("Semantic") }}</dt><dd>{{ zh(d.semantic_id) }}</dd>
              <dt>{{ zh("Unit") }}</dt><dd>{{ zh(d.unit.label) }} · {{ zh(d.unit.system) }} · {{ zh(d.unit.quantity) }} {{ zh("· SI mapping:") }} {{ zh(factText(d.unit.si_mapping)) }}</dd>
              <dt>{{ zh("Time rule") }}</dt><dd>{{ zh(d.time_rule) }}</dd>
              <dt>{{ zh("Spatial rule") }}</dt><dd>{{ zh(d.spatial_rule) }}</dd>
              <dt>{{ zh("Mask") }}</dt><dd>{{ zh(d.mask_refs.join(', ') || 'None recorded') }}</dd>
              <dt>{{ zh("Detector / scope") }}</dt><dd>{{ zh(factText(d.detector)) }}</dd>
            </dl>
            <ul><li v-for="lim in d.limitations" :key="lim.id">{{ zh(lim.code) }} — {{ zh(lim.description) }}</li></ul>
          </article>
          <article v-for="m in record.masks" :key="m.id" class="subrecord">
            <h3>{{ zh("Mask:") }} {{ zh(m.id) }} · {{ zh(m.type) }}</h3><p>{{ zh(m.definition) }}</p><p>{{ zh(m.scope.description) }}</p>
            <p>{{ zh("Parameters:") }} {{ zh(m.parameters.map(p => `${p.name}: ${factText(p.value)}`).join('; ')) }}</p>
            <p>{{ zh("Domains:") }} {{ zh(m.domain_refs.join(', ')) }} {{ zh("· Verification:") }} {{ zh(verificationText(m.verification)) }}</p>
            <p v-for="s in m.index_sets" :key="s.axis">{{ zh(s.axis) }}: {{ zh(s.indices.join(', ')) }} {{ zh("· index base") }} {{ zh(s.index_base) }}</p>
            <p>{{ zh("Array references:") }} {{ zh(m.mask_array_refs.map(a => `${a.result_id} / ${a.descriptor.array_id}`).join(', ') || 'None recorded') }}</p>
          </article>
        </section>
        <section data-testid="evidence-limitations">
          <h2>{{ zh("Limitations") }}</h2>
          <ul><li v-for="lim in record.limitations" :key="lim.id"><strong>{{ zh(lim.severity) }} · {{ zh(lim.code) }}</strong> — {{ zh(lim.description) }}<br>{{ zh("Affected:") }} {{ zh(lim.affected_refs.join(', ') || 'Not enumerated') }}</li></ul>
          <p v-if="!record.limitations.length">{{ zh("No limitations registered; support is still bounded by recorded definitions and scope.") }}</p>
        </section>
        <section data-testid="evidence-relations">
          <h2>{{ zh("Relations") }}</h2>
          <h3>{{ zh("Related evidence") }}</h3>
          <ul><li v-for="id in record.related_evidence_refs" :key="id"><RouterLink :to="relation(id)">{{ zh(id) }}</RouterLink></li></ul>
          <p v-if="!record.related_evidence_refs.length">{{ zh("No related evidence registered.") }}</p>
          <h3>{{ zh("Parent / source results") }}</h3>
          <p>{{ zh("No separate parent-result field is recorded. Registered result/source bindings:") }}</p>
          <ul><li v-for="r in record.result_contexts" :key="r.result_id">{{ zh(r.result_id) }} {{ zh("· Source assets:") }} {{ zh(r.provenance.source_asset_ids.join(', ')) }} {{ zh("· Evidence:") }} <RouterLink v-for="id in r.provenance.evidence_refs" :key="id" :to="relation(id)">{{ zh(id) }} </RouterLink></li></ul>
          <p>{{ zh("Superseded by:") }} <RouterLink v-if="successor" :to="relation(successor)">{{ zh(successor) }} {{ zh("→ associated successor evidence") }}</RouterLink><span v-else>{{ zh(factText(record.superseded_by)) }}</span></p>
        </section>
      </article>
    </LoadStateBlock>
    <button v-if="detail?.state === 'ERROR'" @click="load">{{ zh("Retry evidence record") }}</button>
    <section v-if="detail?.state === 'MISSING'" data-testid="evidence-fallback"><h1>{{ zh("Evidence record not found") }}</h1><p>{{ zh(detail.reason) }}</p><RouterLink :to="{ name: 'evidence-center' }">{{ zh("Back to Evidence Center") }}</RouterLink></section>
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
