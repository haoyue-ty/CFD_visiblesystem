<script setup lang="ts">
import { zh } from '../presentation/zh-CN'

/**
 * MetricsPanel — displays each metric WITH its definition, unit, detector scope
 * and evidence link. Three bare numbers are explicitly not enough (Window 3).
 *
 * Public props kept stable per README: `collection`.
 */
import type { MetricCollectionView } from '../data/domain'
import EvidenceLink from './EvidenceLink.vue'

defineProps<{ collection: MetricCollectionView }>()
</script>

<template>
  <div class="mp" data-testid="metrics-panel">
    <article v-for="metric in collection.items" :key="metric.metric_id" class="mp__item" :data-testid="`metric-${metric.metric_id}`" :data-availability="metric.availability">
      <header class="mp__head">
        <h3 class="mp__label">{{ zh(metric.display_label) }}</h3>
        <span class="mp__value">
          <template v-if="metric.value !== null">{{ zh(metric.value) }} <span class="mp__unit">{{ zh(metric.unit.label) }}</span></template>
          <template v-else>—</template>
        </span>
        <span class="badge" :class="metric.availability === 'AVAILABLE' ? 'badge--ok' : 'badge--partial'">{{ zh(metric.availability) }}</span>
      </header>

      <dl class="mp__meta">
        <dt>{{ zh("Definition") }}</dt>
        <dd>{{ zh(metric.definition_text) }} <span class="mp__def-id">[{{ zh(metric.definition_id) }}]</span></dd>
        <dt>{{ zh("Unit") }}</dt>
        <dd>{{ zh(metric.unit.label) }} <span class="mp__def-id">({{ zh(metric.unit.system) }})</span></dd>
        <dt>{{ zh("Detector / scope") }}</dt>
        <dd>{{ zh(metric.detector_scope) }}</dd>
        <dt>{{ zh("Time scope") }}</dt>
        <dd>{{ zh(metric.time_scope_label) }}</dd>
        <dt>{{ zh("Resolution limit") }}</dt>
        <dd>{{ zh(metric.resolution_limit === null ? 'UNKNOWN (not recorded)' : metric.resolution_limit) }}</dd>
      </dl>

      <p v-if="metric.unavailable_reason" class="mp__reason">{{ zh(metric.unavailable_reason) }}</p>

      <footer class="mp__footer">
        <EvidenceLink v-for="ref in metric.evidence_refs" :key="ref" :evidence-id="ref" :context="`metric:${metric.metric_id}`" />
      </footer>
    </article>
  </div>
</template>

<style scoped>
.mp { display: grid; gap: 0.9rem; }
.mp__item { border: 1px solid #e2e2e2; border-radius: 5px; padding: 0.8rem 1rem; }
.mp__head { display: flex; align-items: baseline; gap: 0.7rem; }
.mp__label { margin: 0; font-size: 1rem; }
.mp__value { font-size: 1.05rem; font-weight: 700; color: #1a3a5c; }
.mp__unit { font-size: 0.78rem; font-weight: 400; color: #666; }
.mp__meta { display: grid; grid-template-columns: 9rem 1fr; gap: 0.2rem 0.6rem; font-size: 0.83rem; margin: 0.5rem 0; }
.mp__meta dt { color: #666; }
.mp__meta dd { margin: 0; color: #333; }
.mp__def-id { color: #888; font-size: 0.76rem; }
.mp__reason { font-size: 0.8rem; color: #8a6d00; background: #fffaf0; border-left: 3px solid #e6c86a; padding: 0.3rem 0.6rem; }
.mp__footer { margin-top: 0.3rem; }
.badge { font-size: 0.66rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 3px; text-transform: uppercase; }
.badge--ok { background: #e3f5e6; color: #186a2b; }
.badge--partial { background: #fff4d6; color: #8a6d00; }
</style>
