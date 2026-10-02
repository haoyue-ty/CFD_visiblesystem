<script setup lang="ts">
import { zh } from '../presentation/zh-CN'

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
  const unitLabel = zh(props.mode.result.unit.label)

  const base = {
    title: {
      text: `特征模态 — k=${props.mode.mode_index} · ${props.mode.side} · 特征对序号 ${props.mode.rank}`,
      subtext: `表示=${zh(props.mode.eigen_representation)} · 投影=${zh(props.mode.projection)} · 分量=${props.mode.field_component} · 形状 ${props.mode.shape.join('×')}`,
      left: 'left', textStyle: { fontSize: 13 }, subtextStyle: { fontSize: 11, color: '#666' },
    },
    tooltip: { trigger: isComplex && props.mode.projection === 'COMPLEX' ? 'item' : 'axis' },
    grid: { left: 62, right: 24, top: 92, bottom: 46, containLabel: false },
  }

  // COMPLEX projection of a raw vector: draw a parametric scatter of (Re, Im).
  if (isComplex && props.mode.projection === 'COMPLEX') {
    const pairs = (values as [number, number][])
    const slots = COMPONENTS.map((name, slot) => ({
      name: `${name}（单元索引）`, type: 'scatter' as const,
      data: pairs.map((pair, i) => (Math.floor(i % 4) === slot ? pair : null)).filter((v): v is [number, number] => v !== null),
      symbolSize: 4, itemStyle: { color: ['#1a4f8a', '#c0392b', '#27795b', '#8e44ad'][slot] },
      // cell index is the parameter; tooltip reports it.
      encode: { x: 0, y: 1 },
    }))
    return {
      ...base,
      legend: { top: 4, right: 4, data: COMPONENTS.map(n => `${n}（单元索引）`), textStyle: { fontSize: 11 } },
      xAxis: { type: 'value', name: `Re(v) [${unitLabel}]`, nameLocation: 'middle', nameGap: 30, scale: true, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: `Im(v) [${unitLabel}]`, nameLocation: 'middle', nameGap: 48, scale: true, axisLabel: { fontSize: 10 } },
      series: slots,
      graphic: [{ type: 'text', left: 62, top: 60, style: { text: 'Raw complex composite vector shown as a parametric (Re, Im) scatter per component slot (no single real ordering).', fontSize: 10, fill: '#555' } }],
    }
  }

  // REAL / IMAGINARY / AMPLITUDE of a complex vector, or a primitive profile.
  const x = Array.from({ length: cells }, (_, i) => i)
  let series: { name: string; type: 'line'; data: (number | null)[]; smooth: false; symbol: string; symbolSize: number; lineStyle: { width: number }; itemStyle: { color: string } }[]
  if (isComplex) {
    const pairs = values as [number, number][]
    series = COMPONENTS.map((name, slot) => ({
      name, type: 'line' as const, smooth: false as const, symbol: 'circle' as const, symbolSize: 4,
      lineStyle: { width: 1.4 }, itemStyle: { color: ['#1a4f8a', '#c0392b', '#27795b', '#8e44ad'][slot] },
      data: x.map(i => pairs[i * 4 + slot] === undefined ? null : projectionOf(pairs[i * 4 + slot], props.mode.projection)),
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
    yAxis: { type: 'value', name: `${props.mode.projection === 'AMPLITUDE' ? '|v|' : zh(props.mode.projection)} [${unitLabel}]`, nameLocation: 'middle', nameGap: 50, scale: true, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { type: 'dashed', color: '#e6e6e6' } } },
    series,
  }
})

const { el } = useEcharts(option as Ref<unknown>)
</script>

<template>
  <figure class="emc" data-testid="eigenmode-chart">
    <div ref="el" class="emc__canvas" data-testid="eigenmode-canvas" role="img"
         :aria-label="`模态 ${mode.mode_index} 的特征向量，${mode.side} 特征对序号 ${mode.rank}`"></div>
  </figure>
</template>

<style scoped>
.emc { margin: 0; }
.emc__canvas { width: 100%; height: 22rem; }
</style>
