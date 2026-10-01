// The shared chart entry. Pages import ECharts ONLY through this module so the
// bundle has a single charting entry point and the mock/production boundary is
// never crossed by a chart component reaching into a transport.
//
// Phase 7B Window 3 (Spectral Lab) adds the full `echarts/core` composable set a
// spectral curve / eigenmode / growth chart requires. Scientific charts MUST keep
// real coordinates and units — no smoothing, no dataZoom-driven data synthesis.
export { init, dispose, use, graphic } from 'echarts/core'
export type { ECharts, EChartsCoreOption } from 'echarts/core'
export { LineChart, ScatterChart, BarChart } from 'echarts/charts'
export {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DatasetComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent,
} from 'echarts/components'
export { CanvasRenderer } from 'echarts/renderers'
