<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { computed } from 'vue'
import { useEcharts } from '../../scientific/useEcharts'
const props = defineProps<{ curves: { name: string; unit: string; points: [number, number | null][] }[]; xLabel: string; log?: boolean }>()
const option = computed(() => {
  const units = [...new Set(props.curves.map(c => c.unit))]
  return {
    animation: false, tooltip: { trigger: 'axis' }, legend: { type: 'scroll', top: 5 },
    grid: { left: 95, right: units.length > 1 ? 100 : 35, top: 65, bottom: 80 },
    xAxis: { type: props.log ? 'log' : 'value', name: props.xLabel, nameLocation: 'middle', nameGap: 35, scale: true },
    yAxis: units.map((unit, i) => ({ type: props.log ? 'log' : 'value', name: unit, position: i ? 'right' : 'left', scale: true,
      axisLabel: { formatter: (value: number) => value !== 0 && (Math.abs(value) < .001 || Math.abs(value) >= 1e5) ? value.toExponential(2) : String(value) } })),
    dataZoom: props.log ? [] : [{ type: 'inside' }, { type: 'slider', bottom: 5 }],
    series: props.curves.map(c => ({ type: props.log ? 'scatter' : 'line', name: c.name,
      yAxisIndex: units.indexOf(c.unit), showSymbol: props.log, symbolSize: 10, connectNulls: false, data: c.points })),
  }
})
const { el } = useEcharts(option)
</script>
<template><div ref="el" role="img" :aria-label="curves.map(c => zh(c.name)).join(', ')" :data-point-count="curves[0]?.points.length" style="height: 24rem; width: 100%" /></template>
