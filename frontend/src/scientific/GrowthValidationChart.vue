<script setup lang="ts">
/**
 * GrowthValidationChart — recorded growth validation: linear vs CFD.
 *
 * SCIENTIFIC RULE: this chart compares RECORDED series; it never fits, extrapolates
 * or synthesizes a prediction.
 *
 *   CFD amplitude     the recorded 33-step history (values 0..32). Always drawn.
 *   linear amplitude  the recorded linear amplitude history. In the frozen source
 *                     this history was NOT saved, so every sample is a MISSING
 *                     fact (null). A MISSING series is drawn as an ABSENT legend
 *                     entry with an explicit note — it is NEVER a synthesized
 *                     exponential exp(sigma*t), and it is never a flat zero line.
 *
 * The recorded growth rates (linear / RK3 / CFD) are shown as horizontal
 * reference lines at their recorded values, each with its own legend name and its
 * own unit. The relative discrepancy is quoted verbatim from the frozen contract
 * (CFD−RK3, fraction) and is NOT recomputed by the frontend.
 */
import { computed, type Ref } from 'vue'
import type { GrowthValidationView } from '../data/domain'
import { useEcharts } from './useEcharts'

const props = defineProps<{ validation: GrowthValidationView }>()

const option = computed(() => {
  const v = props.validation
  const unitLabel = v.result.unit.label === 'rate (model units)' ? 'model' : v.result.unit.label
  const cfd = v.cfd_amplitude
  const linear = v.linear_amplitude
  const linearAvailable = linear.some(x => x !== null)
  const series: Record<string, unknown>[] = [
    {
      name: 'CFD amplitude (recorded)',
      type: 'line', smooth: false, connectNulls: false, symbol: 'circle', symbolSize: 4,
      data: cfd, lineStyle: { width: 1.6, color: '#1a4f8a' }, itemStyle: { color: '#1a4f8a' },
    },
  ]
  if (linearAvailable) {
    series.push({
      name: 'linear amplitude (recorded)',
      type: 'line', smooth: false, connectNulls: false, symbol: 'circle', symbolSize: 4,
      data: linear, lineStyle: { width: 1.6, color: '#c0392b' }, itemStyle: { color: '#c0392b' },
    })
  }
  // Recorded growth rates as reference lines at their recorded values.
  const marks = ([
    ['linear', v.growth_rate.linear, '#c0392b'],
    ['RK3', v.growth_rate.rk3, '#27795b'],
    ['CFD', v.growth_rate.cfd, '#1a4f8a'],
  ] as const).filter(([, value]) => value !== null)
    .map(([label, value, color]) => ({
      name: `σ_${label} = ${(value as number).toExponential(4)}`,
      yAxis: value as number, lineStyle: { color, type: 'dashed' as const, width: 1 },
      label: { formatter: `σ_${label}=${(value as number).toPrecision(4)}`, fontSize: 10, color },
    }))

  return {
    title: {
      text: `Growth validation — mode ${v.mode_index} · q_at=${v.q_at} · ε=${v.epsilon}`,
      subtext: `representation=GROWTH_VALIDATION · run ${v.run_id} · 33 recorded steps · amplitude=${v.amplitude_definition}`,
      left: 'left', textStyle: { fontSize: 13 }, subtextStyle: { fontSize: 11, color: '#666' },
    },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: number | null) => (value === null ? 'unavailable (not saved)' : Number(value).toExponential(6)),
    },
    legend: { top: 4, right: 4, textStyle: { fontSize: 11 } },
    grid: { left: 66, right: 24, top: 72, bottom: 46, containLabel: false },
    xAxis: {
      type: 'category', name: 'recorded step index', nameLocation: 'middle', nameGap: 30,
      data: v.step_indices.map(i => String(i)), axisLabel: { fontSize: 10 }, boundaryGap: false,
    },
    yAxis: {
      type: 'value', name: `amplitude [${unitLabel}]`, nameLocation: 'middle', nameGap: 50,
      scale: true, axisLabel: { fontSize: 10, formatter: (n: number) => n.toExponential(1) },
      splitLine: { lineStyle: { type: 'dashed', color: '#e6e6e6' } },
    },
    series: series.map((s, i) => (i === 0 ? { ...s, markLine: { silent: true, symbol: 'none', data: marks } } : s)),
    ...(linearAvailable ? {} : {
      graphic: [{
        type: 'text', left: 66, top: 44,
        style: { text: 'linear amplitude history was not saved — the linear series is ABSENT (no fitted exponential is drawn).', fontSize: 10, fill: '#8a4b00' },
      }],
    }),
  }
})

const { el } = useEcharts(option as Ref<unknown>)
</script>

<template>
  <figure class="gvc" data-testid="growth-validation-chart">
    <div ref="el" class="gvc__canvas" data-testid="growth-validation-canvas" role="img"
         :aria-label="`Growth validation for run ${validation.run_id}`"></div>
  </figure>
</template>

<style scoped>
.gvc { margin: 0; }
.gvc__canvas { width: 100%; height: 22rem; }
</style>
