<script setup lang="ts">
/**
 * MockBadge — the visible MOCK provenance label.
 *
 * Shown next to any region whose data comes from the mock provider so no one
 * mistakes it for real scientific output. Required by the Window 3 spec:
 * "所有 mock 必须显著标注 data_origin=MOCK, verification=NOT_APPLICABLE".
 */
defineProps<{
  origin: string
  verification?: string
  compact?: boolean
}>()
</script>

<template>
  <span
    class="mock-badge"
    :class="{ 'mock-badge--compact': compact }"
    role="note"
    data-testid="mock-badge"
    data-origin="MOCK"
  >
    <span class="mock-badge__dot" aria-hidden="true"></span>
    data_origin={{ origin }}
    <template v-if="verification">· verification={{ verification }}</template>
  </span>
</template>

<style scoped>
.mock-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: #6a1b9a;
  background: #f3e5f5;
  border: 1px solid #ce93d8;
  border-radius: 3px;
  padding: 0.1rem 0.4rem;
  text-transform: uppercase;
}
.mock-badge--compact { font-size: 0.66rem; }
.mock-badge__dot { width: 6px; height: 6px; border-radius: 50%; background: #8e24aa; }
</style>
