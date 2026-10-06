<script setup lang="ts">
import { zh, chartCopy } from '../presentation/zh-CN'

/**
 * EntropyChart — ECharts rendering of the recorded scalar entropy history.
 *
 * Renders E_bg / E_aa / E_at series. Supports selecting a scalar point (which is
 * a real accepted step). When a point is selected the component reports it so
 * the page can fetch the nearest recorded snapshot and display BOTH times.
 *
 * Two distinct time granularities are never conflated:
 *   - the selected scalar step time (1..1912 accepted steps)
 *   - the displayed snapshot time (1..6 recorded snapshots)
 * The component renders the selected scalar time; the dual-time notice is
 * rendered by the parent next to it.
 *
 * Public props kept stable per README: `history`.
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { EntropyHistoryView } from '../data/domain'

type ChartHistory = Pick<EntropyHistoryView, 'total_point_count'> & {
  series: Array<{ series_id: string; label: string; points: Array<{ step_index: number; physical_time: number; value: number }> }>
}
const props = withDefaults(defineProps<{ history: ChartHistory; selectable?: boolean; physicalTime?: boolean }>(), { selectable: true, physicalTime: false })
const emit = defineEmits<{ (e: 'select-scalar-step', step: number): void }>()

const host = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const SERIES_COLORS: Record<string, string> = {
  E_bg: '#3b6ea5',
  E_aa: '#c0703a',
  E_at: '#2e7d32',
}

function buildOption() {
  const seriesData = props.history.series.map((s) => ({
    name: s.label.replace(/ \(.*\)$/, ''),
    type: 'line' as const,
    showSymbol: false,
    sampling: 'none' as const, // never downsample scientific points
    lineStyle: { width: 1.4, color: SERIES_COLORS[s.series_id.split('.').pop() as string], type: s.series_id.startsWith('b.') ? 'dashed' as const : 'solid' as const },
    itemStyle: { color: SERIES_COLORS[s.series_id.split('.').pop() as string] },
    data: s.points.map((p) => [props.physicalTime ? p.physical_time : p.step_index, p.value]),
  }))
  return {
    animation: false,
    grid: { left: 60, right: 20, top: 40, bottom: 45 },
    tooltip: {
      trigger: 'axis' as const,
      confine: true,
      formatter: (params: unknown) => {
        const arr = params as { seriesName: string; value: [number, number] }[]
        if (!arr?.length) return ''
        if (props.physicalTime) return `模型时间 ${arr[0].value[0]}<br/>` + arr.map(p => `${p.seriesName}: ${p.value[1]}`).join('<br/>')
        const step = arr[0].value[0]
        const t = props.history.series[0]?.points.find(point => point.step_index === step)?.physical_time
        return `已完成步 ${step}<br/>标量时间 ${t ?? '未知'}<br/>` +
          arr.map((p) => `${p.seriesName}: ${p.value[1]}`).join('<br/>')
      },
    },
    legend: { top: 5, data: seriesData.map((s) => s.name) },
    xAxis: {
      type: 'value' as const,
      name: props.physicalTime ? '模型时间' : 'completed accepted step',
      nameLocation: 'middle' as const,
      nameGap: 26,
      min: props.physicalTime ? 0 : 1,
      max: props.physicalTime ? Math.max(...props.history.series.flatMap(s => s.points.map(p => p.physical_time))) : props.history.total_point_count,
    },
    yAxis: { type: 'value' as const, name: 'entropy production (model units)', scale: true },
    series: seriesData,
  }
}

function render() {
  if (!host.value) return
  if (!chart) chart = echarts.init(host.value)
  chart.setOption(chartCopy(buildOption()), true)

  // Click anywhere in the plot to select the nearest REAL accepted step. Using
  // the coordinate system (rather than a per-symbol hit test) keeps selection
  // reliable even with showSymbol:false, and never invents an interpolated
  // point — the snapped step is one of the recorded step values.
  chart.off('click')
  chart.getZr().off('click')
  if (!props.selectable || props.physicalTime) return
  chart.on('click', (params: { value?: unknown }) => {
    const value = params.value as [number, number] | undefined
    if (value && typeof value[0] === 'number') emit('select-scalar-step', value[0])
  })
  chart.getZr().on('click', (event: { offsetX: number; offsetY: number }) => {
    const converted = chart?.convertFromPixel({ gridIndex: 0 }, [event.offsetX, event.offsetY])
    if (!converted || typeof converted[0] !== 'number' || Number.isNaN(converted[0])) return
    emit('select-scalar-step', snapToRecordedStep(converted[0]))
  })
}

/** Snap a raw x-coordinate to the nearest actually-recorded step index. */
function snapToRecordedStep(rawStep: number): number {
  const all = props.history.series.flatMap((s) => s.points.map((p) => p.step_index))
  const steps = all.length ? all : [1]
  let best = steps[0]
  let bestDistance = Infinity
  for (const step of steps) {
    const distance = Math.abs(step - rawStep)
    if (distance < bestDistance) {
      bestDistance = distance
      best = step
    }
  }
  return best
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})

watch(() => [props.history, props.physicalTime, props.selectable], render, { deep: false })
</script>

<template>
  <div class="ec">
    <div ref="host" class="ec__canvas" data-testid="entropy-chart" :data-axis="physicalTime ? 'physical_time' : 'accepted_step'" :style="{ height: '20rem' }"></div>
    <p v-if="selectable" class="ec__hint">{{ zh("Click a point to select a real accepted step. The nearest recorded snapshot is shown alongside.") }}</p>
  </div>
</template>

<style scoped>
.ec { width: 100%; min-width: 0; }
.ec__canvas { width: 100%; }
.ec__hint { font-size: 0.75rem; color: #777; }
</style>
