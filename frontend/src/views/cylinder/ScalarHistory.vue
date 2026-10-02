<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { computed } from 'vue'
import type { HistoryBundle } from '../../data/cylinder'
import { known } from '../../data/cylinder'
import { useEcharts } from '../../scientific/useEcharts'
import ResultContext from './ResultContext.vue'
const props = defineProps<{ bundle: HistoryBundle }>()
const step = defineModel<number>('step', { default: 9757 })
const option = computed(() => ({
  animation: false, tooltip: { trigger: 'axis' }, legend: { data: props.bundle.history.series.map(s => zh(s.label)) },
  grid: { left: 90, right: 20, bottom: 55 },
  xAxis: { type: 'value', min: 1, max: 9757, name: 'Completed accepted step', nameLocation: 'middle', nameGap: 30 },
  yAxis: { type: 'value', name: props.bundle.history.series[0]?.result.unit.label, scale: true },
  series: props.bundle.history.series.map(s => ({ name: s.label, type: 'line', showSymbol: false, sampling: 'none',
    data: s.points.map(p => [known(p.step_index), known(p.value)]) })),
}))
const { el } = useEcharts(option)
</script>
<template>
  <section data-testid="cylinder-history">
    <h2>{{ zh("9757-step scalar history") }}</h2>
    <p>{{ zh("All 9757 recorded accepted-step endpoints per series. The scalar timeline and the five snapshot selections are independent.") }}</p>
    <div ref="el" data-testid="cylinder-entropy-chart" role="img" :aria-label="zh('9757 recorded scalar endpoints per series')" style="height: 24rem" />
    <label>{{ zh("Scalar completed step") }} <input v-model.number="step" type="range" min="1" max="9757" step="1" data-testid="scalar-step" /></label>
    <article v-for="series in bundle.history.series" :key="series.series_id" :data-series="series.series_id" :data-point-count="series.points.length">
      <h3>{{ zh(series.label) }} · {{ zh(series.points.length) }} {{ zh("records") }}</h3>
      <p v-if="series.points[step - 1]" data-testid="scalar-selected">{{ zh("completed step=") }}{{ zh(known(series.points[step - 1].step_index)) }} {{ zh("· source step=") }}{{ zh(known(series.points[step - 1].source_step_index)) }} {{ zh("· physical time=") }}{{ zh(known(series.points[step - 1].physical_time)) }} {{ zh("· accepted interval=") }}{{ zh(known(series.points[step - 1].interval)) }} {{ zh("· value=") }}{{ zh(known(series.points[step - 1].value)) }}</p>
      <p>{{ zh("Series definition:") }} {{ zh(series.definition_id) }} {{ zh("· source column:") }} {{ zh(series.source_column) }} {{ zh("· aggregation:") }} {{ zh(series.aggregation) }}</p>
      <ResultContext :result="series.result" :definitions="bundle.definitions" />
    </article>
  </section>
</template>
<style scoped>article { border-top: 1px solid #ddd; padding: .8rem 0; } input { width: 60%; }</style>
