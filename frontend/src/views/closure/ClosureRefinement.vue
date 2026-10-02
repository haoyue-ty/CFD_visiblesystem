<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { computed } from 'vue'
import { known, slotValue, type ClosureRun, type Refinement } from '../../data/closure'
import ClosureChart from './ClosureChart.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'
const props = defineProps<{ summary: Refinement; runs: ClosureRun[] }>()
const rows = computed(() => props.summary.metrics_by_run.map(entry => {
  const run = props.runs.find(r => r.run_id === entry.run_id)
  const metrics = entry.metrics.map(slot => slotValue(slot)).filter(m => m !== null)
  const residual = metrics.find(m => m.metric_id === 'R_total')
  const value = residual ? known(residual.value) : null
  return { id: entry.run_id, cfl: run ? known(run.config.parameters.find(p => p.name === 'CFL')!.value) : null,
    magnitude: value === null ? null : Math.abs(value), dt: known(metrics.find(m => m.metric_id === 'dt_eff')?.value ?? { state: 'UNKNOWN' }),
    slopes: metrics.filter(m => m.metric_id.startsWith('pairwise_slope')), unit: residual?.result.unit.label ?? 'UNKNOWN' }
}))
const curve = computed(() => [{ name: 'Terminal |R(T)| — four frozen D_u runs', unit: rows.value[0]?.unit ?? 'UNKNOWN', points: rows.value.filter(r => r.cfl !== null && r.magnitude !== null).map(r => [r.cfl!, r.magnitude] as [number, number | null]) }])
</script>
<template>
  <section data-testid="closure-refinement">
    <h2>{{ zh("D_u temporal refinement") }}</h2>
    <p>{{ zh("Four recorded points · terminal |R(T)| · log-log display against CFL. Frozen slope / order uses dt_eff; no frontend fit.") }}</p>
    <ClosureChart :curves="curve" x-label="CFL" log />
    <table data-testid="refinement-table"><thead><tr><th>{{ zh("Run") }}</th><th>CFL</th><th>dt_eff</th><th>{{ zh("Terminal |R(T)|") }}</th><th>{{ zh("Frozen pairwise slope / order") }}</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><th>{{ zh(row.id) }}</th><td>{{ zh(row.cfl ?? 'UNKNOWN') }}</td><td>{{ zh(row.dt ?? 'UNKNOWN') }}</td><td>{{ zh(row.magnitude ?? 'UNKNOWN') }}</td><td><span v-for="slope in row.slopes" :key="slope.metric_id">{{ zh(slope.metric_id) }}={{ zh(known(slope.value)) }} </span></td></tr></tbody></table>
    <p data-testid="refinement-slope">{{ zh("Frozen global slope / order (dt_eff):") }} {{ zh(summary.refinement_slope.availability) }} · {{ zh(slotValue(summary.refinement_slope) ? known(slotValue(summary.refinement_slope)!.value) : 'UNKNOWN') }}</p>
    <EvidenceLink v-for="id in summary.evidence_refs" :key="id" :evidence-id="id" />
  </section>
</template>
<style scoped>td,th { border:1px solid #ddd; padding:.4rem; text-align:left; } table { border-collapse:collapse; width:100%; font-size:.85rem; }</style>
