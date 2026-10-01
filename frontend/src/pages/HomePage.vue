<script setup lang="ts">
import { activeProvider } from '../data'
/**
 * P02 — Home (system home).
 *
 * Shows: the core scientific question, a short mechanism chain, the Explore
 * entry (explicitly PLANNED and NOT a clickable empty flow), the Lab entry, the
 * Evidence explanation, and the per-experiment DELIVERY status summary.
 *
 * CRITICAL: an unimplemented capability is marked by DELIVERY status
 * (PLANNED/IMPLEMENTED). It is NEVER labelled as MISSING scientific data —
 * those are different layers (IA 14.1, API contract §1.1 delivery rule).
 */
import { onMounted, ref } from 'vue'
import { dataService, type Loaded } from '../data'
import type { ExperimentCatalogEntry, ProjectView } from '../data/domain'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import MockBadge from '../components/MockBadge.vue'

const project = ref<Loaded<ProjectView> | null>(null)
const experiments = ref<Loaded<ExperimentCatalogEntry[]> | null>(null)

onMounted(async () => {
  project.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  experiments.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  project.value = await dataService.getProject()
  experiments.value = await dataService.listExperiments()
})
</script>

<template>
  <main data-page="home" class="home">
    <header class="home__hero">
      <h1>ShockPath</h1>
      <p class="home__question" data-testid="home-question">
        What triggers numerical dissipation, where does it act, and how does it change modal and
        macroscopic flow behaviour?
      </p>

      <LoadStateBlock :loaded="project" target="project identity">
        <p v-if="project?.data" class="home__tagline">{{ project.data.tagline }}</p>
        <div v-if="project?.data" class="home__chain" aria-label="Mechanism chain">
          <template v-for="(step, i) in project.data.mechanism_chain" :key="step">
            <span class="home__chain-node">{{ step }}</span>
            <span v-if="i < project.data.mechanism_chain.length - 1" class="home__chain-arrow" aria-hidden="true">→</span>
          </template>
        </div>
        <MockBadge v-if="activeProvider.kind === 'MOCK'" origin="MOCK" :verification="activeProvider.kind === 'MOCK' ? 'NOT_APPLICABLE' : undefined" />
      </LoadStateBlock>
    </header>

    <section class="home__modes" aria-label="Modes">
      <article class="card" data-testid="explore-entry">
        <h2>Explore</h2>
        <p>A guided ~4-minute seven-scene scientific story.</p>
        <p class="badge badge--planned" data-testid="explore-status">PLANNED — not yet available</p>
        <p class="card__hint">
          The guided flow is not implemented in this slice. It is intentionally not a clickable
          empty page; it will be delivered in a later window.
        </p>
      </article>

      <article class="card card--active">
        <h2>Lab</h2>
        <p>Choose a real experiment and configuration, inspect recorded data, analysis and provenance.</p>
        <RouterLink class="card__cta" :to="{ name: 'lab' }" data-testid="home-to-lab">进入实验室 / Open the Lab</RouterLink>
      </article>

      <article class="card">
        <h2>Evidence</h2>
        <p>Every scientific result can be traced to its method, config, source and verification state.</p>
        <p class="card__hint">Open a result's "View evidence" link to reach a full evidence record.</p>
      </article>
    </section>

    <section class="home__experiments" aria-label="Experiment delivery status">
      <h2>Experiment availability (delivery status)</h2>
      <p class="home__caption">
        Status below is <strong>software delivery status</strong>, not scientific capability and not
        asset verification.
      </p>
      <LoadStateBlock :loaded="experiments" target="experiment catalog">
        <ul class="exp-list" data-testid="home-experiment-list">
          <li v-for="exp in experiments?.data || []" :key="exp.experiment_id" class="exp-list__item">
            <div class="exp-list__head">
              <span class="exp-list__name">{{ exp.name }}</span>
              <span
                class="badge"
                :class="exp.delivery_status === 'IMPLEMENTED' ? 'badge--implemented' : 'badge--planned'"
                :data-testid="`delivery-${exp.experiment_id}`"
              >{{ exp.delivery_status }}</span>
            </div>
            <p class="exp-list__summary">{{ exp.summary }}</p>
            <p v-if="exp.availability_note" class="exp-list__note">{{ exp.availability_note }}</p>
            <p v-else class="exp-list__note exp-list__note--planned">
              Delivery status: PLANNED (software not yet implemented — capability is not missing scientific data).
            </p>
            <RouterLink
              v-if="exp.delivery_status === 'IMPLEMENTED' && exp.implementable_route"
              class="exp-list__link"
              :to="{ name: 'experiment', params: { experiment_id: exp.implementable_route } }"
            >Open {{ exp.name }} →</RouterLink>
          </li>
        </ul>
      </LoadStateBlock>
    </section>
  </main>
</template>

<style scoped>
.home { max-width: 60rem; margin: 0 auto; padding: 1.5rem; }
.home__question { font-size: 1.15rem; font-weight: 600; color: #1a3a5c; line-height: 1.5; }
.home__tagline { color: #444; line-height: 1.6; }
.home__chain { display: flex; flex-wrap: wrap; align-items: center; gap: 0.3rem; margin: 0.6rem 0; }
.home__chain-node { background: #e8f0fa; border: 1px solid #b8d0ea; border-radius: 3px; padding: 0.15rem 0.5rem; font-size: 0.82rem; }
.home__chain-arrow { color: #888; }
.home__modes { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1rem; margin: 1.5rem 0; }
.card { border: 1px solid #ddd; border-radius: 5px; padding: 1rem; background: #fff; }
.card--active { border-color: #1a4f8a; }
.card h2 { margin: 0 0 0.4rem; font-size: 1.1rem; }
.card p { font-size: 0.88rem; color: #444; line-height: 1.5; }
.card__hint { color: #777 !important; font-size: 0.8rem !important; }
.card__cta { display: inline-block; margin-top: 0.4rem; padding: 0.45rem 1rem; background: #1a4f8a; color: #fff; text-decoration: none; border-radius: 3px; font-size: 0.88rem; }
.home__experiments h2 { font-size: 1.1rem; }
.home__caption { font-size: 0.82rem; color: #666; margin-top: -0.4rem; }
.exp-list { list-style: none; padding: 0; display: grid; gap: 0.7rem; }
.exp-list__item { border: 1px solid #e2e2e2; border-radius: 4px; padding: 0.7rem 0.9rem; }
.exp-list__head { display: flex; align-items: center; gap: 0.6rem; }
.exp-list__name { font-weight: 600; }
.exp-list__summary { font-size: 0.85rem; color: #444; margin: 0.3rem 0; }
.exp-list__note { font-size: 0.8rem; color: #666; margin: 0.2rem 0; }
.exp-list__note--planned { color: #8a6d00; }
.exp-list__link { font-size: 0.85rem; }
.badge { font-size: 0.68rem; font-weight: 700; padding: 0.1rem 0.45rem; border-radius: 3px; text-transform: uppercase; }
.badge--planned { background: #fff4d6; color: #8a6d00; border: 1px solid #e6c86a; }
.badge--implemented { background: #e3f5e6; color: #186a2b; border: 1px solid #8cc79a; }
</style>
