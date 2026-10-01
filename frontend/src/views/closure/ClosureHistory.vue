<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { known, type HistoryBundle } from '../../data/closure'
import ClosureChart from './ClosureChart.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'
const props = defineProps<{ bundle: HistoryBundle }>()
const stage = computed(() => props.bundle.history.granularity === 'PER_STAGE')
const selected = ref(0)
const extra = ref<string[]>([])
watch(() => props.bundle, () => { selected.value = 0; extra.value = [] })
const series = computed(() => props.bundle.history.series)
const required = computed(() => stage.value ? ['G', 'D_total', 'R_SD', 'eps_SD'] : ['DeltaS', 'E_obs_step', 'R_time_step', 'R_time_cumulative', 'E_bg_step', 'E_aa_step', 'E_at_step', 'E_total_independent_step'])
const optional = computed(() => series.value.filter(s => !required.value.includes(s.series_id)))
const shown = computed(() => series.value.filter(s => required.value.includes(s.series_id) || extra.value.includes(s.series_id)))
const groups = computed(() => {
  const additional = [...new Set(optional.value.filter(s => extra.value.includes(s.series_id)).map(s => s.result.unit.label))]
    .map(unit => ({ label: `Additional recorded columns · ${unit}`, ids: optional.value.filter(s => extra.value.includes(s.series_id) && s.result.unit.label === unit).map(s => s.series_id) }))
  return [...(stage.value
    ? [{ label: 'Stage closure: G and -D_total (display sign only)', ids: ['G', 'D_total'] }, { label: 'Semi-discrete residual', ids: ['R_SD', 'eps_SD'] }]
    : [{ label: 'Step increments: DeltaS and E_obs', ids: ['DeltaS', 'E_obs_step'] }, { label: 'Residual increment', ids: ['R_time_step'] }, { label: 'Recorded cumulative residual', ids: ['R_time_cumulative'] }, { label: 'Channel increments', ids: ['E_bg_step', 'E_aa_step', 'E_at_step', 'E_total_independent_step'] }]), ...additional]
})
function curves(ids: string[]) { return series.value.filter(s => ids.includes(s.series_id)).map(s => ({ name: stage.value && s.series_id === 'D_total' ? '-D_total (display sign only)' : s.label, unit: s.result.unit.label, points: s.points.map(p => [stage.value ? p.point_index + 1 : known(p.step_index)!, stage.value && s.series_id === 'D_total' ? -known(p.value)! : known(p.value)] as [number, number | null]) })) }
const page = computed(() => series.value[0]!.page)
</script>
<template>
  <section data-testid="closure-history" :data-granularity="bundle.history.granularity">
    <h2>{{ stage ? 'Semi-discrete' : 'Fully-discrete' }} · {{ bundle.history.granularity }}</h2>
    <p v-if="stage" data-testid="stage-clock">3 RK stages per accepted step. Record ordinal preserves source order. Recorded stage clock is the containing step time_n; actual stage-state physical time is NOT_ESTABLISHED. This is not a complete real state timeline.</p>
    <p v-if="stage">The comparison plots G and -D_total; the table keeps recorded D_total. R_SD = G + D_total retains its frozen definition.</p>
    <p v-else>PER_STEP · increment values belong to each accepted [time_n, time_np1] interval. Only R_time_cumulative is a recorded cumulative history; terminal R_total is displayed separately.</p>
    <p data-testid="history-range">Recorded rows {{ page.offset + 1 }}–{{ page.offset + page.returned_count }} of {{ page.total_count }}. Charts show this page only.</p>
    <div v-for="group in groups.filter(g => g.ids.length)" :key="group.label">
      <h3>{{ group.label }}</h3><ClosureChart :curves="curves(group.ids)" :x-label="stage ? 'Recorded stage ordinal (1-based)' : 'Accepted step (1-based)'" />
    </div>
    <fieldset><legend>Additional recorded columns</legend><label v-for="s in optional" :key="s.series_id"><input v-model="extra" type="checkbox" :value="s.series_id" />{{ s.label }} </label></fieldset>
    <label>Inspect record on this page <input v-model.number="selected" data-testid="record-selector" type="range" min="0" :max="page.returned_count - 1" /></label>
    <p v-if="series[0]?.points[selected]" data-testid="record-clock">accepted step={{ known(series[0]!.points[selected]!.step_index) }} · source stage={{ known(series[0]!.points[selected]!.source_stage_index) ?? 'not applicable' }} · recorded clock={{ known(series[0]!.points[selected]!.physical_time) }} · interval={{ known(series[0]!.points[selected]!.interval) }}</p>
    <table data-testid="recorded-values"><thead><tr><th>Recorded column</th><th>Value</th><th>Unit</th><th>Aggregation</th><th>Frozen definition</th></tr></thead><tbody>
      <tr v-for="s in shown" :key="s.series_id" :data-series="s.series_id"><th>{{ s.label }}</th><td>{{ known(s.points[selected]!.value) ?? 'UNKNOWN' }}</td><td>{{ s.result.unit.label }}</td><td>{{ s.aggregation }}</td><td>{{ bundle.definitions.find(d => d.id === s.definition_id)?.definition }}</td></tr>
    </tbody></table>
    <p>Independent D_total and E_total_independent_step retain their source definitions; channel attribution describes interface production, not separate state entropies.</p>
    <EvidenceLink v-for="id in bundle.history.evidence_refs" :key="id" :evidence-id="id" />
  </section>
</template>
<style scoped>table { width:100%; border-collapse:collapse; font-size:.85rem; } td,th { border:1px solid #ddd; padding:.4rem; text-align:left; } fieldset { margin:1rem 0; } label { display:inline-block; margin:.3rem; } input[type=range] { width:18rem; }</style>
