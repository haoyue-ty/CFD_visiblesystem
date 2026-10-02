<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { activeProvider } from '../../data'
/**
 * Case8 Overview tab — parameters, protocol, availability and capabilities.
 * The config selector lives on the page shell; this tab summarises the current
 * selection and the capability/limitation layers.
 */
import { computed } from 'vue'
import type { ExperimentOverview } from '../../data/domain'
import MockBadge from '../../components/MockBadge.vue'

const props = defineProps<{ overview: ExperimentOverview; configId: string }>()

const config = computed(() => props.overview.configurations.find((c) => c.config_id === props.configId) ?? null)
</script>

<template>
  <section class="ov" data-testid="case8-overview">
    <h2>{{ zh(overview.name) }} — {{ zh(configId) }}</h2>
    <p class="ov__desc">{{ zh(overview.description) }}</p>

    <div class="ov__grid">
      <div class="ov__block">
        <h3>{{ zh("Config parameters") }}</h3>
        <table class="ov__table" data-testid="overview-parameters">
          <tbody>
            <tr><th>{{ zh("Config") }}</th><td data-testid="overview-config">{{ zh(configId) }}</td></tr>
            <tr><th>q_aa</th><td data-testid="overview-q_aa">{{ zh(config?.q_aa ?? '—') }}</td></tr>
            <tr><th>q_at</th><td data-testid="overview-q_at">{{ zh(config?.q_at ?? '—') }}</td></tr>
          </tbody>
        </table>
      </div>

      <div class="ov__block">
        <h3>{{ zh("Protocol") }}</h3>
        <table class="ov__table">
          <tbody>
            <tr><th>{{ zh("Method") }}</th><td>{{ zh(overview.protocol.method_name ?? 'UNKNOWN') }}</td></tr>
            <tr><th>{{ zh("Integrator") }}</th><td>{{ zh(overview.protocol.integrator ?? 'UNKNOWN') }}</td></tr>
            <tr><th>{{ zh("Reconstruction") }}</th><td>{{ zh(overview.protocol.reconstruction ?? 'UNKNOWN') }}</td></tr>
            <tr><th>{{ zh("Grid") }}</th><td>{{ zh(overview.protocol.grid ?? 'UNKNOWN') }}</td></tr>
            <tr><th>{{ zh("Final time") }}</th><td>{{ zh(overview.protocol.final_time ?? 'UNKNOWN') }}</td></tr>
          </tbody>
        </table>
      </div>

      <div class="ov__block">
        <h3>{{ zh("Recorded data availability") }}</h3>
        <ul class="ov__list">
          <li><strong>{{ zh(overview.snapshot_count) }}</strong> {{ zh("recorded spatial snapshots (indices 1…") }}{{ zh(overview.snapshot_count) }})</li>
          <li><strong>{{ zh(overview.scalar_step_count) }}</strong> {{ zh("accepted-step scalar points (1…") }}{{ zh(overview.scalar_step_count) }})</li>
          <li>{{ zh("Two independent time granularities (snapshot vs scalar)") }}</li>
        </ul>
        <p class="ov__capability">{{ zh("Capability: SUPPORTED —") }} {{ zh(overview.snapshot_count) }} {{ zh("snapshots +") }} {{ zh(overview.scalar_step_count) }} {{ zh("scalar steps") }}</p>
      </div>
    </div>

    <p v-if="overview.limitation" class="ov__limitation" data-testid="overview-limitation">
      <strong>{{ zh(overview.limitation.severity) }}</strong> · {{ zh(overview.limitation.description) }}
    </p>
    <MockBadge v-if="activeProvider.kind === 'MOCK'" origin="MOCK" :verification="activeProvider.kind === 'MOCK' ? 'NOT_APPLICABLE' : undefined" />
  </section>
</template>

<style scoped>
.ov__desc { font-size: 0.9rem; color: #444; line-height: 1.6; }
.ov__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1rem; margin: 1rem 0; }
.ov__block h3 { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.04em; color: #555; }
.ov__table { border-collapse: collapse; font-size: 0.85rem; }
.ov__table th, .ov__table td { border: 1px solid #e0e0e0; padding: 0.25rem 0.7rem; text-align: left; }
.ov__table th { background: #f7f7f7; color: #555; font-weight: 500; }
.ov__list { font-size: 0.85rem; padding-left: 1.1rem; }
.ov__capability { font-size: 0.82rem; color: #186a2b; font-weight: 600; }
.ov__limitation { font-size: 0.8rem; color: #8a4b00; background: #fffaf0; border-left: 3px solid #d08700; padding: 0.4rem 0.6rem; }
</style>
