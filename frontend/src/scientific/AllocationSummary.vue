<script setup lang="ts">
/**
 * AllocationSummary — the budget / inside / outside block plus the explicit
 * measure rule.
 *
 * The measure rule is the reason the two representations are different objects:
 *  - FACE_FIELD: includes_spatial_measure = false, so the spatially integrated
 *    budget still needs dy/dx applied to the face sums.
 *  - CELL_FIELD: includes_spatial_measure = true, so the cell sum IS the budget.
 *
 * Showing the rule and its parameters next to the numbers makes it impossible to
 * read the two budgets as if they were computed the same way.
 */
import type { AllocationSummaryView } from '../data/domain'
import EvidenceLink from './EvidenceLink.vue'

const props = defineProps<{ summary: AllocationSummaryView; evidenceId?: string }>()

function fmt(value: number | null): string {
  return value === null ? 'UNKNOWN' : String(value)
}
</script>

<template>
  <section class="as" data-testid="allocation-summary" :data-measure="props.summary.measure_definition">
    <h3 class="as__h">Summary</h3>
    <dl class="as__grid">
      <div class="as__cell">
        <dt>Integrated budget</dt>
        <dd data-testid="alloc-budget">{{ fmt(props.summary.total_budget.value) }}</dd>
        <span class="as__unit">{{ props.summary.total_budget.unit_label }}</span>
      </div>
      <div class="as__cell">
        <dt>Inside window</dt>
        <dd data-testid="alloc-inside">{{ fmt(props.summary.inside.value) }}</dd>
        <span class="as__unit">{{ props.summary.inside.fraction_format ?? '' }}</span>
      </div>
      <div class="as__cell" v-if="props.summary.outside">
        <dt>Outside window</dt>
        <dd data-testid="alloc-outside">{{ fmt(props.summary.outside.value) }}</dd>
        <span class="as__unit">{{ props.summary.outside.fraction_format ?? '' }}</span>
      </div>
    </dl>

    <dl class="as__measure" data-testid="allocation-measure">
      <div>
        <dt>Measure definition</dt>
        <dd>{{ props.summary.measure_definition }}</dd>
      </div>
      <div>
        <dt>Integral rule</dt>
        <dd><code data-testid="alloc-integral-rule">{{ props.summary.integral_rule }}</code></dd>
      </div>
      <div>
        <dt>Time weights included</dt>
        <dd>{{ props.summary.includes_time_weights ? 'yes (already applied)' : 'no' }}</dd>
      </div>
      <div>
        <dt>Spatial measure included</dt>
        <dd data-testid="alloc-spatial-included">
          {{ props.summary.includes_spatial_measure ? 'yes (do not multiply again)' : 'no (dx/dy still required)' }}
        </dd>
      </div>
      <div v-if="props.summary.measure_parameters.length">
        <dt>Rule parameters</dt>
        <dd>
          <span v-for="p in props.summary.measure_parameters" :key="p.name" class="as__param">
            {{ p.name }} = {{ p.value }}
          </span>
        </dd>
      </div>
      <div>
        <dt>Integration interval</dt>
        <dd>{{ props.summary.integration_interval }}</dd>
      </div>
      <div>
        <dt>Time scope</dt>
        <dd>{{ props.summary.time_scope_label }}</dd>
      </div>
    </dl>
    <p v-if="props.evidenceId" class="as__ev">
      <EvidenceLink :evidence-id="props.evidenceId" context="allocation-summary" />
    </p>
  </section>
</template>

<style scoped>
.as { margin: 0; }
.as__h { font-size: 0.95rem; margin: 0 0 0.4rem; }
.as__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap: 0.6rem; margin: 0 0 0.8rem; }
.as__cell { border: 1px solid #e0e0e0; border-radius: 4px; padding: 0.4rem 0.6rem; }
.as__cell dt { font-size: 0.72rem; color: #666; text-transform: uppercase; letter-spacing: 0.03em; }
.as__cell dd { margin: 0.15rem 0 0; font-size: 1rem; font-weight: 700; color: #1a3a5c; word-break: break-all; }
.as__unit { font-size: 0.68rem; color: #888; }
.as__measure { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 0.35rem 1rem; font-size: 0.8rem; margin: 0; }
.as__measure dt { color: #666; font-size: 0.72rem; }
.as__measure dd { margin: 0; }
.as__param { margin-right: 0.5rem; }
.as__ev { margin: 0.5rem 0 0; }
</style>
