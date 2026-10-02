<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { computed } from 'vue'
import type { AllocationBundle } from '../../data/cylinder'
import { known, slotValue } from '../../data/cylinder'
import { useEcharts } from '../../scientific/useEcharts'
import ResultContext from './ResultContext.vue'
import ResourceState from './ResourceState.vue'
const props = defineProps<{ bundle: AllocationBundle }>()
const sectors = computed(() => { const v = slotValue(props.bundle.overview.sectors); return v?.representation_type === 'ANGULAR_SECTORS' ? v : null })
const band = computed(() => { const v = slotValue(props.bundle.overview.front_band); return v?.representation_type === 'REGION_SCALAR' ? v : null })
const option = computed(() => ({
  animation: false, tooltip: { trigger: 'axis' }, legend: { data: props.bundle.channels.map(c => c.channel) },
  grid: { left: 90, right: 20, bottom: 85 },
  xAxis: { type: 'category', name: 'Native angular bin (radian edges in table)', data: Array.from({ length: 16 }, (_, i) => String(i + 1)), nameLocation: 'middle', nameGap: 35 },
  yAxis: { type: 'value', name: sectors.value?.result.unit.label ?? 'Recorded entropy' },
  series: props.bundle.channels.map(c => ({ name: c.channel, type: 'bar', data: c.values })),
}))
const { el } = useEcharts(option)
</script>
<template>
  <section data-testid="sector-allocation">
    <h2>{{ zh("ANGULAR_SECTORS · 16 sectors") }}</h2>
    <p><strong>{{ zh("trajectory-integrated · interior-only") }}</strong> {{ zh("· Native measured SSP-RK3 statistics; time weights and face measure already included.") }}</p>
    <ResourceState :resource="bundle.overview.sectors" label="Angular sectors">
      <template v-if="sectors">
        <div ref="el" data-testid="angular-sector-chart" style="height: 23rem; width: 100%" role="img" :aria-label="zh('Sixteen native angular sectors, trajectory integrated interior entropy channels')" />
        <table data-testid="sector-table"><thead><tr><th>{{ zh("Sector") }}</th><th>{{ zh("Angular edges (radian)") }}</th><th>{{ zh("at fraction") }}</th></tr></thead><tbody>
          <tr v-for="(fraction, i) in sectors.sector_fractions" :key="i"><td>{{ zh(i + 1) }}</td><td>{{ zh(bundle.edges[i]) }} … {{ zh(bundle.edges[i + 1]) }}</td><td>{{ zh(known(fraction) ?? 'N/A (zero denominator)') }}</td></tr>
        </tbody></table>
        <ResultContext :result="sectors.result" :definitions="bundle.definitions" />
      </template>
    </ResourceState>
    <section data-testid="front-band">
      <h2>{{ zh("Front-band REGION_SCALAR") }}</h2>
      <ResourceState :resource="bundle.overview.front_band" label="Front-band scalar">
        <template v-if="band">
          <p>{{ zh("Fraction:") }} <strong>{{ zh(known(band.fraction) ?? 'N/A (zero denominator)') }}</strong> {{ zh("· integrated value:") }} {{ zh(known(band.integrated_value) ?? 'Missing') }}</p>
          <p>{{ zh("Denominator:") }} {{ zh(band.denominator_result_id) }}</p>
          <p>{{ zh("Mask:") }} {{ zh(band.region_mask.id) }} · {{ zh(band.region_mask.type) }} — {{ zh(band.region_mask.definition) }}</p>
          <p>{{ zh("Mask parameters:") }} <span v-for="p in band.region_mask.parameters" :key="p.name">{{ zh(p.name) }}={{ zh(known(p.value) ?? 'UNKNOWN') }}; </span></p>
          <ResultContext :result="band.result" :definitions="bundle.definitions" />
        </template>
      </ResourceState>
    </section>
    <section data-testid="cumulative-2d-missing"><h2>{{ zh("Full trajectory cumulative 2D Pi_at") }}</h2>
      <ResourceState :resource="bundle.overview.cumulative_2d" :label="zh('Full trajectory cumulative 2D Pi_at')" />
    </section>
  </section>
</template>
<style scoped>table { border-collapse: collapse; font-size: .8rem; } th, td { border: 1px solid #ddd; padding: .25rem .5rem; } section { margin: 1rem 0; }</style>
