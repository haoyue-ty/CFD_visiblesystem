<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { verificationText } from "../../data/evidence"
import { computed } from 'vue'
import type { Science, Definitions } from '../../data/cylinder'
import { known, slotValue } from '../../data/cylinder'
import ResultContext from './ResultContext.vue'
import ResourceState from './ResourceState.vue'
const props = defineProps<{ collection: Science['MetricCollection']; definitions: Definitions; compact?: boolean }>()
const displayed = computed(() => props.compact ? props.collection.items.slice(0, 4) : props.collection.items)
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
    <ResourceState v-for="(resource, i) in displayed" :key="i" :resource="resource" label="Canonical metric">
      <article v-if="slotValue(resource)" :data-metric="slotValue(resource)!.metric_id">
        <h3>{{ zh(labels[slotValue(resource)!.metric_id] ?? slotValue(resource)!.display_label) }}</h3>
        <p>{{ zh("Value:") }} <strong>{{ zh(known(slotValue(resource)!.value) ?? 'Missing') }}</strong> {{ zh(slotValue(resource)!.result.unit.label) }}</p>
        <template v-if="!compact">
        <p>{{ zh("Detector:") }} {{ zh(known(slotValue(resource)!.detector)?.name ?? 'N/A') }} — {{ zh(known(slotValue(resource)!.detector)?.definition ?? 'No spatial detector recorded') }}</p>
        <ul><li v-for="parameter in known(slotValue(resource)!.detector)?.parameters ?? []" :key="parameter.name">{{ zh(parameter.name) }}: {{ zh(known(parameter.value) ?? 'UNKNOWN') }}</li></ul>
        <p data-testid="detector-floor">{{ zh("Detector floor / resolution limit:") }} {{ zh(floorLabel(slotValue(resource)!)) }}</p>
        <ResultContext :result="slotValue(resource)!.result" :definitions="definitions" />
        </template>
        <template v-else>
          <p>{{ zh("Detector:") }} {{ zh(known(slotValue(resource)!.detector)?.name ?? 'N/A') }} · {{ zh(slotValue(resource)!.result.time.sampling) }} / {{ zh(slotValue(resource)!.result.time.accumulation) }}</p>
          <p>{{ zh(slotValue(resource)!.result.scope.description) }} · {{ zh(verificationText(slotValue(resource)!.result.verification)) }}</p>
          <details><summary>{{ zh("Definition, scope and provenance") }}</summary><ResultContext :result="slotValue(resource)!.result" :definitions="definitions" /></details>
        </template>
      </article>
    </ResourceState>
    <details v-if="compact"><summary>{{ zh("All canonical metrics and full detector definitions") }}</summary><CanonicalMetrics :collection="collection" :definitions="definitions" /></details>
  </div>
</template>
<style scoped>article { border: 1px solid #ddd; padding: .8rem; margin: .7rem 0; } h3 { margin: 0; }</style>
