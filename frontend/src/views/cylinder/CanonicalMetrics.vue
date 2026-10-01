<script setup lang="ts">
import type { Science, Definitions } from '../../data/cylinder'
import { known, slotValue } from '../../data/cylinder'
import ResultContext from './ResultContext.vue'
import ResourceState from './ResourceState.vue'
defineProps<{ collection: Science['MetricCollection']; definitions: Definitions }>()
const labels: Record<string, string> = {
  cylinder_centerline_width: 'Centerline width', cylinder_front_mean_width: 'Front-mean width',
  cylinder_front_RMS: 'Front RMS', cylinder_front_HF_RMS: 'HF-RMS',
}
function floorLabel(metric: Science['Metric']) {
  return metric.resolution_limit.state === 'KNOWN' ? metric.resolution_limit.value : metric.resolution_limit.reason
}
</script>
<template>
  <div data-testid="canonical-metrics">
    <ResourceState v-for="(resource, i) in collection.items" :key="i" :resource="resource" label="Canonical metric">
      <article v-if="slotValue(resource)" :data-metric="slotValue(resource)!.metric_id">
        <h3>{{ labels[slotValue(resource)!.metric_id] ?? slotValue(resource)!.display_label }}</h3>
        <p>Value: <strong>{{ known(slotValue(resource)!.value) ?? 'Missing' }}</strong> {{ slotValue(resource)!.result.unit.label }}</p>
        <p>Detector: {{ known(slotValue(resource)!.detector)?.name ?? 'N/A' }} — {{ known(slotValue(resource)!.detector)?.definition ?? 'No spatial detector recorded' }}</p>
        <ul><li v-for="parameter in known(slotValue(resource)!.detector)?.parameters ?? []" :key="parameter.name">{{ parameter.name }}: {{ known(parameter.value) ?? 'UNKNOWN' }}</li></ul>
        <p data-testid="detector-floor">Detector floor / resolution limit: {{ floorLabel(slotValue(resource)!) }}</p>
        <ResultContext :result="slotValue(resource)!.result" :definitions="definitions" />
      </article>
    </ResourceState>
  </div>
</template>
<style scoped>article { border: 1px solid #ddd; padding: .8rem; margin: .7rem 0; } h3 { margin: 0; }</style>
