<script setup lang="ts">
/**
 * EigenmodeChart — a saved eigenmode vector or primitive amplitude profile.
 *
 * SCIENTIFIC RULE: the component draws exactly what the descriptor declares.
 *
 *   COMPLEX_VECTOR  shape [128,4], complex128. A raw composite vector has NO
 *                   single real ordering, so it is drawn as the chosen
 *                   PROJECTION (REAL / IMAGINARY / AMPLITUDE) of each of the
 *                   four component slots, one series per component. COMPLEX is
 *                   shown as a parametric (Re, Im) scatter, never as a line.
 *   PRIMITIVE_PROFILE shape [128], float64. One sourced component amplitude on
 *                   128 cells — a single monotone series.
 *
 * The component order is part of the projection, not a presentation choice; the
 * caption states the exact selected (side, rank, representation, projection,
 * field_component). No value is interpolated, phase-shifted or renormalized.
 */
import { computed, type Ref } from 'vue'
import type { EigenmodeView, SpectralArrayView } from '../data/domain'
import { useEcharts } from './useEcharts'

const props = defineProps<{ mode: EigenmodeView; array: SpectralArrayView }>()

const COMPONENTS = ['ρ', 'ρu', 'ρv', 'E']

function projectionOf(value: [number, number] | number, projection: EigenmodeView['projection']): number {
  if (typeof value === 'number') return value
  const [re, im] = value
  if (projection === 'REAL') return re
  if (projection === 'IMAGINARY') return im
  if (projection === 'AMPLITUDE') return Math.hypot(re, im)
  return re // COMPLEX is handled as a scatter, not here
}

const option = computed(() => {
  const values = props.array.values
  const isComplex = props.mode.eigen_representation === 'COMPLEX_VECTOR'
  const cells = props.mode.shape[0]
  const unitLabel = props.mode.result.unit.label

  const base = {
    title: {
      text: `Eigenmode — mode k=${props.mode.mode_index} · ${props.mode.side} · rank ${props.mode.rank}`,
      subtext: `representation=${props.mode.eigen_representation} · projection=${props.mode.projection} · component=${props.mode.field_component} · shape ${props.mode.shape.join('×')}`,
      left: 'left', textStyle: { fontSize: 13 }, subtextStyle: { fontSize: 11, color: '#666' },
    },
    tooltip: { trigger: isComplex && props.mode.projection === 'COMPLEX' ? 'item' : 'axis' },
    grid: { left: 62, right: 24, top: 72, bottom: 46, containLabel: false },
  }

  // COMPLEX projection of a raw vector: draw a parametric scatter of (Re, Im).
  if (isComplex && props.mode.projection === 'COMPLEX') {
    const pairs = (values as [number, number][])
    const slots = COMPONENTS.map((name, slot) => ({
      name: `${name} (cell index)`, type: 'scatter' as const,
      data: pairs.map((pair, i) => (Math.floor(i % 4) === slot ? pair : null)).filter((v): v is [number, number] => v !== null),
      symbolSize: 4, itemStyle: { color: ['#1a4f8a', '#c0392b', '#27795b', '#8e44ad'][slot] },
      // cell index is the parameter; tooltip reports it.
      encode: { x: 0, y: 1 },
    }))
    return {
      ...base,
      legend: { top: 4, right: 4, data: COMPONENTS.map(n => `${n} (cell index)`), textStyle: { fontSize: 11 } },
      xAxis: { type: 'value', name: 'Re(λ·v) [model]', nameLocation: 'middle', nameGap: 30, scale: true, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: 'Im(λ·v) [model]', nameLocation: 'middle', nameGap: 48, scale: true, axisLabel: { fontSize: 10 } },
      series: slots,
      graphic: [{ type: 'text', left: 62, top: 44, style: { text: 'Raw complex composite vector shown as a parametric (Re, Im) scatter per component slot (no single real ordering).', fontSize: 10, fill: '#555' } }],
    }
  }

  // REAL / IMAGINARY / AMPLITUDE of a complex vector, or a primitive profile.
  const x = Array.from({ length: cells }, (_, i) => i)
  let series: { name: string; type: 'line'; data: number[]; smooth: false; symbol: string; symbolSize: number; lineStyle: { width: number }; itemStyle: { color: string } }[]
  if (isComplex) {
    const pairs = values as [number, number][]
    series = COMPONENTS.map((name, slot) => ({
      name, type: 'line' as const, smooth: false as const, symbol: 'circle' as const, symbolSize: 4,
      lineStyle: { width: 1.4 }, itemStyle: { color: ['#1a4f8a', '#c0392b', '#27795b', '#8e44ad'][slot] },
      data: x.map(i => projectionOf(pairs[i * 4 + slot] ?? [0, 0], props.mode.projection)),
    }))
  } else {
    series = [{
      name: props.mode.field_component, type: 'line' as const, smooth: false as const, symbol: 'circle' as const, symbolSize: 3,
      lineStyle: { width: 1.5 }, itemStyle: { color: '#1a4f8a' }, data: (values as number[]).slice(0, cells),
    }]
  }
  return {
    ...base,
    legend: { top: 4, right: 4, data: series.map(s => s.name), textStyle: { fontSize: 11 } },
    xAxis: { type: 'category', name: 'cell index along the saved axis', nameLocation: 'middle', nameGap: 30, data: x, axisLabel: { fontSize: 10 }, axisTick: { alignWithLabel: true }, boundaryGap: false },
    yAxis: { type: 'value', name: `${props.mode.projection === 'AMPLITUDE' ? '|λ·v|' : props.mode.projection} [${unitLabel === 'rate (model units)' ? 'model' : unitLabel}]`, nameLocation: 'middle', nameGap: 50, scale: true, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { type: 'dashed', color: '#e6e6e6' } } },
    series,
  }
})

const { el } = useEcharts(option as Ref<unknown>)
</script>

<template>
  <figure class="emc" data-testid="eigenmode-chart">
    <div ref="el" class="emc__canvas" data-testid="eigenmode-canvas" role="img"
         :aria-label="`Eigenmode vector for mode ${mode.mode_index}, ${mode.side} rank ${mode.rank}`"></div>
  </figure>
</template>

<style scoped>
.emc { margin: 0; }
.emc__canvas { width: 100%; height: 22rem; }
</style>
