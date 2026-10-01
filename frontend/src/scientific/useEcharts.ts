/**
 * useEcharts — mount / resize / dispose an ECharts instance in one place.
 *
 * Scientific charts on the Spectral Lab share one lifecycle rule: the option is
 * rebuilt from the loaded view every time it changes, the instance is resized
 * with its container, and it is disposed on unmount. No chart component ever
 * reaches into a transport or a mock module — they receive already-loaded,
 * already-typed views.
 */
import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { init, dispose, type ECharts } from './echarts'

export function useEcharts(option: Ref<unknown>) {
  const el = ref<HTMLElement | null>(null)
  let chart: ECharts | null = null
  let observer: ResizeObserver | null = null

  function render() {
    if (!el.value) return
    if (!chart) {
      chart = init(el.value)
      observer = new ResizeObserver(() => chart?.resize())
      observer.observe(el.value)
    }
    // notMerge: a new selector must never merge into a stale series.
    chart.setOption(option.value as never, true)
  }

  onMounted(render)
  watch(option, render, { deep: true })
  onBeforeUnmount(() => {
    observer?.disconnect()
    observer = null
    if (chart) {
      dispose(chart)
      chart = null
    }
  })

  return { el }
}
