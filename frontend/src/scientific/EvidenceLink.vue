<script setup lang="ts">
import { zh } from '../presentation/zh-CN'

/**
 * EvidenceLink opens the shared Quick View without unmounting the result.
 * The full-record link retains the experiment / config / tab / selection in an
 * internal return context. Modified clicks still open the independently shareable P09.
 *
 * Public prop kept stable per README: `evidenceId`. `context` and `return` are
 * additive and optional.
 */
import { useRoute, type RouteLocationRaw } from 'vue-router'
import { openEvidence } from '../views/evidence/quickView'
const route = useRoute()

const props = defineProps<{
  evidenceId: string
  context?: string
  /** Query payload restored when the user returns from P09. */
  returnTo?: RouteLocationRaw
}>()

function target(): RouteLocationRaw {
  if (props.evidenceId.startsWith('ev.run.')) {
    return { name: 'run-evidence', params: { runId: props.evidenceId.slice(7) } }
  }
  const query: Record<string, string> = {}
  if (props.context) query.from = props.context
  if (props.returnTo && typeof props.returnTo === 'object' && 'query' in props.returnTo && props.returnTo.query) {
    // Encode the return target compactly so P09 can offer "back to result".
    query.back = JSON.stringify({ ...props.returnTo })
  }
  if (!query.back) query.back = JSON.stringify({ name: route.name, params: route.params, query: route.query })
  return { name: 'evidence', params: { evidence_id: props.evidenceId }, query }
}
function open(event: MouseEvent) {
  if (props.evidenceId.startsWith('ev.run.')) return
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return
  event.preventDefault()
  openEvidence(props.evidenceId, target())
}
</script>

<template>
  <a class="evidence-link" :href="$router.resolve(target()).href" data-testid="evidence-link" @click="open">{{ zh("View evidence") }}</a>
</template>

<style scoped>
.evidence-link { font-size: 0.82rem; color: #1a4f8a; }
</style>
