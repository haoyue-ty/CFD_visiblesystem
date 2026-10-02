<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { activeProvider } from '../../data'
/**
 * Case8 Metrics tab — width / front RMS / HF with full definition context.
 */
import { onMounted, ref, watch } from 'vue'
import { dataService, createRequestGuard, type Loaded } from '../../data'
import type { MetricCollectionView } from '../../data/domain'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import MockBadge from '../../components/MockBadge.vue'
import MetricsPanel from '../../scientific/MetricsPanel.vue'

const props = defineProps<{ configId: string }>()
const metrics = ref<Loaded<MetricCollectionView> | null>(null)
const guard = createRequestGuard()

async function load() {
  metrics.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await guard.run((signal) => dataService.getMetrics(props.configId, signal))
  if (result) metrics.value = result
}

onMounted(load)
watch(() => props.configId, load)
</script>

<template>
  <section class="mt" data-testid="case8-metrics">
    <p class="mt__intro">
      {{ zh("Each metric is shown with its definition, unit, detector scope, time scope and an evidence link. Terminal metrics do not change with the scalar cursor.") }}
    </p>
    <LoadStateBlock :loaded="metrics" target="metrics">
      <div v-if="metrics?.data" class="mt__body">
        <MetricsPanel :collection="metrics.data" />
        <MockBadge v-if="activeProvider.kind === 'MOCK'" origin="MOCK" :verification="activeProvider.kind === 'MOCK' ? 'NOT_APPLICABLE' : undefined" />
      </div>
    </LoadStateBlock>
  </section>
</template>

<style scoped>
.mt__intro { font-size: 0.85rem; color: #555; }
.mt__body { display: grid; gap: 0.6rem; justify-items: start; }
</style>
