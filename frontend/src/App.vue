<script setup lang="ts">
import { activeProvider } from './data'
import MockBadge from './components/MockBadge.vue'
import EvidenceQuickView from './views/evidence/EvidenceQuickView.vue'
import { quickView } from './views/evidence/quickView'
</script>

<template>
  <div :inert="Boolean(quickView)">
  <header class="appbar">
    <nav aria-label="System navigation" class="appbar__nav">
      <RouterLink :to="{ name: 'entry' }" class="appbar__brand">ShockPath</RouterLink>
      <RouterLink :to="{ name: 'home' }">Home</RouterLink>
      <RouterLink :to="{ name: 'explore', query: { scene: '1' } }">Explore</RouterLink>
      <RouterLink :to="{ name: 'lab' }">Lab</RouterLink>
      <RouterLink :to="{ name: 'evidence-center' }">Evidence</RouterLink>
    </nav>
    <div class="appbar__env">
      <span class="appbar__env-label">data source</span>
      <span v-if="activeProvider.kind === 'API'" data-testid="provider-kind">REAL API</span>
      <MockBadge v-else origin="MOCK" :verification="activeProvider.kind === 'MOCK' ? 'NOT_APPLICABLE' : undefined" compact />
    </div>
  </header>
  <RouterView />
  </div>
  <EvidenceQuickView />
</template>

<style scoped>
.appbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.6rem 1.5rem; border-bottom: 1px solid #e0e0e0; background: #fafafa;
}
.appbar__nav { display: flex; align-items: center; gap: 1.2rem; }
.appbar__brand { font-weight: 700; text-decoration: none; color: #1a3a5c; }
.appbar__nav a { text-decoration: none; color: #333; font-size: 0.9rem; }
.appbar__nav a.router-link-active { color: #1a4f8a; font-weight: 600; }
.appbar__env { display: flex; align-items: center; gap: 0.4rem; }
.appbar__env-label { font-size: 0.72rem; color: #888; text-transform: uppercase; letter-spacing: 0.04em; }
</style>
