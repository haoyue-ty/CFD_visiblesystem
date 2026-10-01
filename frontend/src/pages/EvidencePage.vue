<script setup lang="ts">
/**
 * P09 — Evidence Detail (independently shareable).
 *
 * Shows the result identity, what it does / does not support, method/config,
 * recorded vs current source, hashes, verification state, freeze reference and
 * limitations. When the user arrived from a result, a "back to result" link
 * restores the originating experiment / config / tab / selection from the
 * compact `back` query payload.
 *
 * When there is no real incoming history, no fake back target is shown — only a
 * stable Evidence / Lab entry.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import { dataService, createRequestGuard, type Loaded } from '../data'
import type { EvidenceDetailView } from '../data/domain'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import MockBadge from '../components/MockBadge.vue'

const props = defineProps<{ evidence_id: string }>()
const route = useRoute()
const router = useRouter()

const detail = ref<Loaded<EvidenceDetailView> | null>(null)
const guard = createRequestGuard()

/** Decode the compact `back` payload carried from the originating result. */
const backTarget = computed<RouteLocationRaw | null>(() => {
  const raw = route.query.back
  if (typeof raw !== 'string') return null
  try {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && 'name' in parsed) return parsed as RouteLocationRaw
  } catch {
    return null
  }
  return null
})

async function load() {
  detail.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await guard.run((signal) => dataService.getEvidence(props.evidence_id, signal))
  if (result) detail.value = result
}

function goBackToResult() {
  if (backTarget.value) router.push(backTarget.value)
}

onMounted(load)
watch(() => props.evidence_id, load)
</script>

<template>
  <main data-page="evidence" class="evd">
    <nav class="evd__crumb" aria-label="Breadcrumb">
      <RouterLink :to="{ name: 'home' }">Home</RouterLink> →
      <span>Evidence</span> →
      <span class="evd__crumb-current">{{ evidence_id }}</span>
    </nav>

    <header class="evd__actions">
      <button v-if="backTarget" class="evd__back" data-testid="back-to-result" @click="goBackToResult">← Back to result</button>
      <RouterLink v-else class="evd__back" :to="{ name: 'lab' }" data-testid="back-to-lab">← Back to Lab</RouterLink>
    </header>
    <section v-if="route.query.from === 'mechanism'" data-testid="mechanism-evidence-context">
      <h2>Mechanism explanation evidence</h2>
      <p>Theory: conditional schematic explanations. Implementation: frozen production method and hash in this record. Numerical result: the linked spectra keep their own scope and verification; they do not certify the schematic as CFD numerical verification or the Near-1D asymptotic scaling.</p>
      <p>No authoritative five-epsilon raw numerical scan is registered.</p>
    </section>

    <LoadStateBlock :loaded="detail" target="evidence record">
      <article v-if="detail?.data" class="evd__record" data-testid="evidence-record">
        <header class="evd__head">
          <h1>Evidence: {{ detail.data.evidence_id }}</h1>
          <MockBadge :origin="detail.data.data_origin" :verification="detail.data.verification.status" />
        </header>

        <section class="evd__block">
          <h2>Identity</h2>
          <dl class="evd__dl">
            <dt>Experiment</dt><dd data-testid="evidence-experiment">{{ detail.data.experiment_id ?? 'UNKNOWN' }}</dd>
            <dt>Config</dt><dd data-testid="evidence-config">{{ detail.data.config_id ?? 'UNKNOWN' }}</dd>
            <dt>Schema version</dt><dd>{{ detail.data.schema_version }}</dd>
          </dl>
        </section>

        <section class="evd__block">
          <h2>Supports / does not support</h2>
          <p class="evd__supports"><strong>Supports:</strong> {{ detail.data.supports }}</p>
          <p class="evd__not-supports"><strong>Does not support:</strong> {{ detail.data.does_not_support }}</p>
        </section>

        <section class="evd__block">
          <h2>Config parameters</h2>
          <table class="evd__table" data-testid="evidence-params">
            <tbody>
              <tr v-for="p in detail.data.config_parameters" :key="p.name">
                <th>{{ p.name }}</th><td>{{ p.value }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="evd__block">
          <h2>Method &amp; source</h2>
          <dl class="evd__dl">
            <dt>Method</dt><dd>{{ detail.data.method_name ?? 'UNKNOWN' }}</dd>
            <dt>Method hash</dt><dd class="evd__hash">{{ detail.data.method_hash ?? 'UNKNOWN' }}</dd>
            <dt>Recorded source hash</dt><dd class="evd__hash">{{ detail.data.recorded_source_hash ?? 'UNKNOWN' }}</dd>
            <dt>Current source hash</dt><dd class="evd__hash" data-testid="current-source-hash">{{ detail.data.current_source_hash ?? 'UNKNOWN' }}</dd>
            <dt>Data hash</dt><dd class="evd__hash">{{ detail.data.data_hash ?? 'UNKNOWN (not recorded — method hash is NOT a substitute)' }}</dd>
            <dt>Source drift</dt>
            <dd data-testid="evidence-drift">{{ detail.data.source_drift === null ? 'UNKNOWN' : detail.data.source_drift ? 'YES — recorded and current source differ' : 'No' }}</dd>
            <dt>Freeze reference</dt><dd>{{ detail.data.freeze_id ?? 'UNKNOWN (no per-file freeze record)' }}</dd>
          </dl>
        </section>

        <section class="evd__block">
          <h2>Verification</h2>
          <p data-testid="evidence-verification">status: <strong>{{ detail.data.verification.status }}</strong></p>
          <ul class="evd__basis">
            <li v-for="b in detail.data.verification.basis" :key="b">{{ b }}</li>
          </ul>
        </section>

        <section class="evd__block">
          <h2>Source assets</h2>
          <table class="evd__table" data-testid="evidence-assets">
            <thead><tr><th>Asset</th><th>Role</th><th>Drift</th><th>Verification</th></tr></thead>
            <tbody>
              <tr v-for="a in detail.data.source_assets" :key="a.asset_id">
                <td>{{ a.source_display }}</td>
                <td>{{ a.role }}</td>
                <td>{{ a.drift === null ? 'UNKNOWN' : a.drift ? 'YES' : 'No' }}</td>
                <td>{{ a.verification.status }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="evd__block">
          <h2>Related results</h2>
          <ul><li v-for="r in detail.data.related_result_ids" :key="r"><code>{{ r }}</code></li></ul>
        </section>

        <section class="evd__block">
          <h2>Limitations</h2>
          <ul class="evd__limits">
            <li v-for="l in detail.data.limitations" :key="l.id">
              <strong>{{ l.severity }}</strong> {{ l.code }} — {{ l.description }}
            </li>
          </ul>
        </section>
      </article>
    </LoadStateBlock>

    <section v-if="detail?.state === 'MISSING'" data-testid="evidence-fallback">
      <h1>Evidence record not found</h1>
      <p>{{ detail.reason }}</p>
      <RouterLink :to="{ name: 'home' }">← Back to Home</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.evd { max-width: 56rem; margin: 0 auto; padding: 1.5rem; }
.evd__crumb { font-size: 0.82rem; color: #666; }
.evd__crumb a { color: #1a4f8a; text-decoration: none; }
.evd__crumb-current { font-weight: 600; color: #333; word-break: break-all; }
.evd__actions { margin: 0.8rem 0; }
.evd__back { font-size: 0.85rem; color: #1a4f8a; background: none; border: none; cursor: pointer; padding: 0; }
.evd__head { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
.evd__head h1 { font-size: 1.25rem; word-break: break-all; }
.evd__block { border-top: 1px solid #e6e6e6; padding: 0.8rem 0; }
.evd__block h2 { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.04em; color: #555; margin: 0 0 0.4rem; }
.evd__dl { display: grid; grid-template-columns: 12rem 1fr; gap: 0.2rem 0.6rem; font-size: 0.84rem; margin: 0; }
.evd__dl dt { color: #666; }
.evd__dl dd { margin: 0; color: #333; }
.evd__hash { font-family: monospace; font-size: 0.78rem; word-break: break-all; }
.evd__table { border-collapse: collapse; font-size: 0.82rem; width: 100%; }
.evd__table th, .evd__table td { border: 1px solid #e0e0e0; padding: 0.25rem 0.6rem; text-align: left; }
.evd__table th { background: #f7f7f7; font-weight: 500; color: #555; }
.evd__supports { font-size: 0.85rem; color: #186a2b; }
.evd__not-supports { font-size: 0.85rem; color: #a3312a; }
.evd__basis, .evd__limits { font-size: 0.83rem; padding-left: 1.1rem; }
</style>
