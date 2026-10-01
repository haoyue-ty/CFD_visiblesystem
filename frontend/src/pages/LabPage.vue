<script setup lang="ts">
import { activeProvider } from '../data'
/**
 * P04 — Lab Workspace (experiment catalog + analysis shortcuts).
 *
 * Case8 and Cylinder are enterable when the API declares IMPLEMENTED. Other
 * catalog entries retain their API delivery status. They are not labelled as
 * MISSING scientific data (IA 17.1: "不能把'未实现'标记为科研数据 MISSING").
 */
import { onMounted, ref } from 'vue'
import { dataService, type Loaded } from '../data'
import type { ExperimentCatalogEntry, ExperimentOverview } from '../data/domain'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import MockBadge from '../components/MockBadge.vue'

const experiments = ref<Loaded<ExperimentCatalogEntry[]> | null>(null)
const case8 = ref<Loaded<ExperimentOverview> | null>(null)

onMounted(async () => {
  experiments.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  case8.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  experiments.value = await dataService.listExperiments()
  case8.value = await dataService.getExperimentOverview('case8')
})
</script>

<template>
  <main data-page="lab" class="lab">
    <nav class="lab__subnav" aria-label="Lab sections">
      <span class="lab__subnav-current">实验目录 / Experiment catalog</span>
      <span class="lab__subnav-item lab__subnav-item--planned">机制工作台 Mechanism · PLANNED</span>
      <RouterLink :to="{ name: 'cross-flow' }">跨流动比较 Cross-flow</RouterLink>
    </nav>

    <h1>Lab Workspace</h1>
    <p class="lab__intro">
      The Lab opens real experiments and their supported controls. Availability below is
      <strong>software delivery status</strong>; it does not report scientific capability or asset
      verification.
    </p>

    <LoadStateBlock :loaded="experiments" target="experiment catalog">
      <ul class="lab__list" data-testid="lab-experiment-list">
        <li
          v-for="exp in experiments?.data || []"
          :key="exp.experiment_id"
          class="lab__item"
          :class="{ 'lab__item--implemented': exp.delivery_status === 'IMPLEMENTED' }"
          :data-testid="`lab-experiment-${exp.experiment_id}`"
        >
          <div class="lab__item-head">
            <h2>{{ exp.name }}</h2>
            <span
              class="badge"
              :class="exp.delivery_status === 'IMPLEMENTED' ? 'badge--implemented' : 'badge--planned'"
              :data-testid="`lab-delivery-${exp.experiment_id}`"
            >{{ exp.delivery_status }}</span>
          </div>
          <p class="lab__family">{{ exp.scientific_family }}</p>
          <p class="lab__summary">{{ exp.summary }}</p>

          <!-- IMPLEMENTED: enterable, with real capability summary -->
          <template v-if="exp.delivery_status === 'IMPLEMENTED' && exp.implementable_route">
            <p class="lab__capability" :data-testid="`${exp.experiment_id}-capability`">{{ exp.experiment_id === 'cylinder' ? 'SUPPORTED · 5 instantaneous snapshots + 9757 scalar steps + 16 sectors; cumulative 2D Missing' : exp.experiment_id === 'case8' ? 'SUPPORTED · 6 snapshots + 1912 scalar steps' : exp.summary }}</p>
            <RouterLink
              class="lab__cta"
              :to="{ name: 'experiment', params: { experiment_id: exp.experiment_id } }"
              :data-testid="`open-${exp.experiment_id}`"
            >Open {{ exp.name }} →</RouterLink>
          </template>

          <!-- PLANNED: explicit delivery note, NOT a missing-data label -->
          <template v-else>
            <p class="lab__planned-note" :data-testid="`lab-planned-note-${exp.experiment_id}`">
              Delivery: PLANNED — no interactive page is registered yet. This is an application
              delivery state, <strong>not</strong> MISSING scientific data.
            </p>
            <span class="lab__cta lab__cta--disabled" aria-disabled="true">Not yet available</span>
          </template>
        </li>
      </ul>
    </LoadStateBlock>

    <section class="lab__case8-preview" aria-label="Case8 configurations">
      <h2>Case8 configurations</h2>
      <LoadStateBlock :loaded="case8" target="Case8 overview">
        <table class="lab__configs" data-testid="lab-case8-configs">
          <thead>
            <tr><th>Config</th><th>q_aa</th><th>q_at</th></tr>
          </thead>
          <tbody>
            <tr v-for="cfg in case8?.data?.configurations || []" :key="cfg.config_id">
              <td>{{ cfg.config_id }}</td>
              <td>{{ cfg.q_aa }}</td>
              <td>{{ cfg.q_at }}</td>
            </tr>
          </tbody>
        </table>
        <p class="lab__preview-note">
          All four configs are equally selectable; D_u is only a convenient starting point, not
          "best".
        </p>
      </LoadStateBlock>
    </section>

    <footer class="lab__provenance">
      <MockBadge v-if="activeProvider.kind === 'MOCK'" origin="MOCK" :verification="activeProvider.kind === 'MOCK' ? 'NOT_APPLICABLE' : undefined" />
      <span v-if="activeProvider.kind === 'MOCK'" class="lab__provenance-text">All data in this slice is synthetic mock data for layout and interaction development.</span>
    </footer>
  </main>
</template>

<style scoped>
.lab { max-width: 60rem; margin: 0 auto; padding: 1.5rem; }
.lab__subnav { display: flex; gap: 1rem; font-size: 0.85rem; border-bottom: 1px solid #e0e0e0; padding-bottom: 0.5rem; }
.lab__subnav-current { font-weight: 700; color: #1a4f8a; }
.lab__subnav-item--planned { color: #999; }
.lab__intro { font-size: 0.9rem; color: #555; line-height: 1.6; }
.lab__list { list-style: none; padding: 0; display: grid; gap: 0.8rem; }
.lab__item { border: 1px solid #e2e2e2; border-radius: 5px; padding: 0.9rem 1.1rem; }
.lab__item--implemented { border-color: #1a4f8a; background: #f8fbff; }
.lab__item-head { display: flex; align-items: center; gap: 0.6rem; }
.lab__item-head h2 { margin: 0; font-size: 1.05rem; }
.lab__family { font-size: 0.78rem; color: #777; margin: 0.15rem 0; text-transform: uppercase; letter-spacing: 0.04em; }
.lab__summary { font-size: 0.87rem; color: #444; margin: 0.3rem 0; }
.lab__capability { font-size: 0.82rem; color: #186a2b; font-weight: 600; }
.lab__planned-note { font-size: 0.82rem; color: #8a6d00; background: #fffaf0; border-left: 3px solid #e6c86a; padding: 0.35rem 0.6rem; }
.lab__cta { display: inline-block; margin-top: 0.4rem; padding: 0.4rem 1rem; background: #1a4f8a; color: #fff; text-decoration: none; border-radius: 3px; font-size: 0.85rem; }
.lab__cta--disabled { background: #ccc; color: #666; cursor: not-allowed; }
.lab__case8-preview { margin-top: 1.5rem; }
.lab__case8-preview h2 { font-size: 1.05rem; }
.lab__configs { border-collapse: collapse; font-size: 0.85rem; }
.lab__configs th, .lab__configs td { border: 1px solid #ddd; padding: 0.25rem 0.8rem; text-align: left; }
.lab__configs th { background: #f2f2f2; }
.lab__preview-note { font-size: 0.8rem; color: #777; }
.lab__provenance { margin-top: 2rem; display: flex; align-items: center; gap: 0.6rem; }
.lab__provenance-text { font-size: 0.78rem; color: #777; }
.badge { font-size: 0.68rem; font-weight: 700; padding: 0.1rem 0.45rem; border-radius: 3px; text-transform: uppercase; }
.badge--planned { background: #fff4d6; color: #8a6d00; border: 1px solid #e6c86a; }
.badge--implemented { background: #e3f5e6; color: #186a2b; border: 1px solid #8cc79a; }
</style>
