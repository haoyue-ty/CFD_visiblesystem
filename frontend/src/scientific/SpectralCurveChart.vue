<script setup lang="ts">
/**
 * SpectralCurveChart — the spectral abscissa curve.
 *
 * SCIENTIFIC RULE: this is a plot of the DISCRETE recorded Fourier blocks.
 *   x = mode k (ell, 0..16, categorical, one tick per recorded block)
 *   y = Re(lambda)  (the recorded real part of the leading eigenvalue)
 *
 * Each block is one recorded sample; the points are joined by the line ONLY as a
 * visual guide between adjacent recorded blocks. There is NO interpolation, no
 * smoothing and no fitted curve: q is one of four exact configurations and the
 * 17 modes are discrete, so a smooth spline would misrepresent the data. A block
 * whose Re(lambda) is an unresolved fact is rendered as a GAP (a null point) and
 * a visible note — never as zero.
 *
 * Re is dimensionless in the model's own units, so the y-axis keeps the model
 * coordinate with its unit label; the tooltip carries the exact recorded value
 * and the wave number so a reader can reproduce the point.
 */
import { computed, type Ref } from 'vue'
import type { SpectrumCurveView, SpectralPointView } from '../data/domain'
import { useEcharts } from './useEcharts'

const props = defineProps<{ curve: SpectrumCurveView }>()

const option = computed(() => {
  const points: SpectralPointView[] = props.curve.points
  const xs = points.map(p => `k=${p.mode_index}`)
  const ys = points.map(p => (p.real_lambda === null ? null : p.real_lambda))
  const unitLabel = props.curve.result.unit.label
  const missingCount = points.filter(p => p.real_lambda === null).length
  return {
    // legend + title keep the representation and the recorded q explicit.
    title: {
      text: 'Spectral abscissa curve — Re(λ)',
      subtext: `representation=SPECTRUM_CURVE · q_at=${props.curve.q_at} · ${points.length} recorded blocks (ell 0…16)`,
      left: 'left',
      textStyle: { fontSize: 13 },
      subtextStyle: { fontSize: 11, color: '#666' },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const list = params as { dataIndex: number }[]
        const point = points[list[0]?.dataIndex ?? 0]
        if (!point) return ''
        const fmt = (v: number | null) => (v === null ? 'unavailable' : v.toExponential(6))
        return [
          `<strong>mode k = ${point.mode_index}</strong>`,
          `wave number = ${point.wave_number ?? 'unavailable'}`,
          `Re(λ) = ${fmt(point.real_lambda)}`,
          `Im(λ) = ${fmt(point.imag_lambda)}`,
          `spectral abscissa = ${fmt(point.spectral_abscissa)}`,
          `record = ${point.spectrum_record_id}`,
        ].join('<br/>')
      },
    },
    legend: { top: 4, right: 4, data: ['Re(λ)'], textStyle: { fontSize: 11 } },
    grid: { left: 62, right: 24, top: 72, bottom: 46, containLabel: false },
    xAxis: {
      type: 'category',
      name: 'mode k',
      nameLocation: 'middle',
      nameGap: 28,
      data: xs,
      axisLabel: { fontSize: 10, rotate: 45 },
      axisTick: { alignWithLabel: true },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      name: `Re(λ) [${unitLabel}]`,
      nameLocation: 'middle',
      nameGap: 48,
      axisLabel: { fontSize: 10, formatter: (v: number) => v.toPrecision(3) },
      scale: true,
      splitLine: { lineStyle: { type: 'dashed', color: '#e6e6e6' } },
    },
    series: [{
      name: 'Re(λ)',
      type: 'line',
      data: ys,
      // No smoothing; gaps for unresolved facts.
      smooth: false,
      connectNulls: false,
      symbol: 'circle',
      symbolSize: 7,
      lineStyle: { width: 1.5, color: '#1a4f8a' },
      itemStyle: { color: '#1a4f8a' },
      emphasis: { focus: 'series' },
    }],
    ...(missingCount
      ? { graphic: [{ type: 'text', left: 62, top: 44, style: { text: `${missingCount} block(s) have an unresolved Re(λ) fact — shown as a gap, never as zero.`, fontSize: 10, fill: '#8a4b00' } }] }
      : {}),
  }
})

const { el } = useEcharts(option as Ref<unknown>)
</script>

<template>
  <figure class="scc" data-testid="spectral-curve-chart">
    <div ref="el" class="scc__canvas" data-testid="spectral-curve-canvas" role="img"
         :aria-label="`Spectral abscissa curve for q_at ${curve.q_at}`"></div>
  </figure>
</template>

<style scoped>
.scc { margin: 0; }
.scc__canvas { width: 100%; height: 22rem; }
</style>
