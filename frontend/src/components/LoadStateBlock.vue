<script setup lang="ts">
/**
 * LoadStateBlock — renders the interface loading layer consistently.
 * Every data-backed region goes through this so Loading / Partial / Missing /
 * Unsupported / Error are never silently swallowed.
 */
import type { Loaded } from '../data/domain'

defineProps<{
  loaded: Loaded<unknown> | null
  /** Label of the region being loaded, shown during LOADING. */
  target: string
  /** Slot name to use when READY / PARTIAL. */
  readyState?: 'READY' | 'PARTIAL'
}>()
</script>

<template>
  <div v-if="!loaded" class="ls ls--loading" role="status">Loading {{ target }}…</div>
  <div v-else-if="loaded.state === 'LOADING'" class="ls ls--loading" role="status">Loading {{ target }}…</div>
  <div v-else-if="loaded.state === 'ERROR'" class="ls ls--error" role="alert">
    <strong>Error loading {{ target }}.</strong>
    <span v-if="loaded.reason"> {{ loaded.reason }}</span>
  </div>
  <div v-else-if="loaded.state === 'MISSING'" class="ls ls--missing" role="note" data-state="missing">
    <strong>Missing:</strong> {{ target }} — {{ loaded.reason }}
  </div>
  <div v-else-if="loaded.state === 'UNSUPPORTED'" class="ls ls--unsupported" role="note" data-state="unsupported">
    <strong>Unsupported:</strong> {{ target }} — {{ loaded.reason }}
  </div>
  <div v-else class="ls ls--ready">
    <p v-if="loaded.state === 'PARTIAL'" class="ls__partial" role="note" data-state="partial">
      Partial: {{ loaded.reason }}
    </p>
    <slot />
  </div>
</template>

<style scoped>
.ls { font-size: 0.9rem; }
.ls--loading { color: #555; font-style: italic; }
.ls--error { color: #b00020; border-left: 3px solid #b00020; padding: 0.4rem 0.6rem; background: #fff5f6; }
.ls--missing { color: #8a4b00; border-left: 3px solid #d08700; padding: 0.4rem 0.6rem; background: #fffaf0; }
.ls--unsupported { color: #5a2d82; border-left: 3px solid #8a63c4; padding: 0.4rem 0.6rem; background: #faf7ff; }
.ls__partial { color: #8a4b00; background: #fffaf0; border-left: 3px solid #d08700; padding: 0.4rem 0.6rem; }
</style>
