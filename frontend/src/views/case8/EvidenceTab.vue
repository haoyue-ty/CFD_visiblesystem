<script setup lang="ts">
import { verificationText } from "../../data/evidence"
import { activeProvider } from '../../data'
/**
 * Case8 Evidence tab — overview of the current experiment's result sources,
 * each linking to the full P09 evidence record. The return context (experiment,
 * config, tab) is carried so P09 can offer "back to result".
 */
import { onMounted, ref, watch } from 'vue'
import { dataService, createRequestGuard, type Loaded } from '../../data'
import type { EvidenceSummaryView } from '../../data/domain'
import LoadStateBlock from '../../components/LoadStateBlock.vue'
import MockBadge from '../../components/MockBadge.vue'
import EvidenceLink from '../../scientific/EvidenceLink.vue'

const props = defineProps<{ configId: string }>()
const items = ref<Loaded<EvidenceSummaryView[]> | null>(null)
const guard = createRequestGuard()

async function load() {
  items.value = { state: 'LOADING', data: null, reason: null, origin: 'MOCK' }
  const result = await guard.run((signal) => dataService.listEvidenceForConfig(props.configId, signal))
  if (result) items.value = result
}

onMounted(load)
watch(() => props.configId, load)
</script>

<template>
  <section class="ev" data-testid="case8-evidence">
    <p class="ev__intro">
      Sources backing the currently displayed results. Open any record for the full
      method/config/source/hash/verification/limitations detail in P09.
    </p>
    <LoadStateBlock :loaded="items" target="evidence sources">
      <ul class="ev__list" data-testid="evidence-source-list">
        <li v-for="item in items?.data || []" :key="item.evidence_id" class="ev__item">
          <div class="ev__head">
            <span class="ev__title">{{ item.title }}</span>
            <span class="badge" :class="item.source_drift ? 'badge--drift' : 'badge--ok'">
              {{ item.source_drift === null ? 'DRIFT UNKNOWN' : item.source_drift ? 'SOURCE DRIFT' : 'NO DRIFT' }}
            </span>
          </div>
          <p class="ev__meta">
            verification: {{ verificationText(item.verification) }} · results:
            <code>{{ item.result_ids.join(', ') }}</code>
          </p>
          <EvidenceLink :evidence-id="item.evidence_id" />
        </li>
      </ul>
      <MockBadge v-if="activeProvider.kind === 'MOCK'" origin="MOCK" :verification="activeProvider.kind === 'MOCK' ? 'NOT_APPLICABLE' : undefined" />
    </LoadStateBlock>
  </section>
</template>

<style scoped>
.ev__intro { font-size: 0.85rem; color: #555; }
.ev__list { list-style: none; padding: 0; display: grid; gap: 0.6rem; }
.ev__item { border: 1px solid #e2e2e2; border-radius: 4px; padding: 0.7rem 0.9rem; }
.ev__head { display: flex; align-items: center; gap: 0.6rem; }
.ev__title { font-weight: 600; font-size: 0.9rem; }
.ev__meta { font-size: 0.78rem; color: #666; margin: 0.3rem 0; }
.ev__link { font-size: 0.85rem; color: #1a4f8a; }
.badge { font-size: 0.66rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 3px; }
.badge--ok { background: #e3f5e6; color: #186a2b; }
.badge--drift { background: #fdecea; color: #a3312a; }
</style>
