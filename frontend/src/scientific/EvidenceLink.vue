<script setup lang="ts">
/**
 * EvidenceLink — navigates from any scientific result to the full evidence
 * record (P09). It carries a compact `context` string plus an optional `return`
 * object so that going back restores the originating experiment / config / tab /
 * selection.
 *
 * Public prop kept stable per README: `evidenceId`. `context` and `return` are
 * additive and optional.
 */
import type { RouteLocationRaw } from 'vue-router'

const props = defineProps<{
  evidenceId: string
  context?: string
  /** Query payload restored when the user returns from P09. */
  returnTo?: RouteLocationRaw
}>()

function target(): RouteLocationRaw {
  const query: Record<string, string> = {}
  if (props.context) query.from = props.context
  if (props.returnTo && typeof props.returnTo === 'object' && 'query' in props.returnTo && props.returnTo.query) {
    // Encode the return target compactly so P09 can offer "back to result".
    query.back = JSON.stringify({ ...props.returnTo })
  }
  return { name: 'evidence', params: { evidence_id: props.evidenceId }, query }
}
</script>

<template>
  <RouterLink class="evidence-link" :to="target()" data-testid="evidence-link">View evidence</RouterLink>
</template>

<style scoped>
.evidence-link { font-size: 0.82rem; color: #1a4f8a; }
</style>
