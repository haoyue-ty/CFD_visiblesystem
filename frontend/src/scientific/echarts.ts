/**
 * Scientific chart components import ECharts through this single module only.
 *
 * `use()` registers exactly the components the Spectral Lab charts need, once,
 * so no page or component has to remember to register a renderer or a component.
 * Importing a second time is a no-op in ECharts, so this is safe to keep here.
 */
import { use } from '../services/charts'
import { LineChart, ScatterChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DatasetComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  LineChart, ScatterChart, BarChart,
  GridComponent, TooltipComponent, LegendComponent, TitleComponent,
  DatasetComponent, DataZoomComponent, MarkLineComponent, MarkAreaComponent,
  CanvasRenderer,
])

export { init, dispose, type ECharts, type EChartsCoreOption } from '../services/charts'
