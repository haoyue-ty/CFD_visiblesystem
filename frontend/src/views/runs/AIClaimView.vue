<script setup lang="ts">
import type { AIAnalysis, AIClaim } from '../../data/v2/ai'
defineProps<{ claim: AIClaim; analysis: AIAnalysis }>()
const labels = { FACT: '事实', INTERPRETATION: '解释', LIMITATION: '局限' }
</script>
<template>
  <article class="claim">
    <strong>{{ labels[claim.kind] }}</strong><p>{{ claim.text }}</p>
    <ul><li v-for="ref in claim.evidence_refs" :key="ref">
      <template v-for="fact in analysis.evidence.filter(f => f.evidence_id === ref)" :key="fact.evidence_id">
        <RouterLink :to="`/runs/${analysis.run_id}/evidence`" :title="fact.definition">{{ fact.label }}</RouterLink>：
        <span>{{ fact.availability === 'AVAILABLE' ? `${fact.value ?? '—'} ${fact.unit}` : `不可用：${fact.reason ?? '缺少数据'}` }}</span>
      </template>
    </li></ul>
  </article>
</template>
<style scoped>
.claim { padding: .8rem 0; border-bottom: 1px solid #e1e8ee; }p,li { line-height: 1.65; overflow-wrap: anywhere; }strong { font-size: .8rem; color: #496579; }ul { padding-left: 1rem; font-size: .78rem; }a { color: #214f75; }
</style>
