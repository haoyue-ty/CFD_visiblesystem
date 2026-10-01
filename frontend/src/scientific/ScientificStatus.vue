<script setup lang="ts">
/**
 * ScientificStatus — renders the three INDEPENDENT status layers that must never
 * be collapsed into one badge (IA 14.1):
 *   1. scientific capability (SUPPORTED / PARTIAL / MISSING / UNSUPPORTED)
 *   2. evidence / verification status
 *   3. interface load state
 *
 * Public props kept stable per README: `verification`, `availability`,
 * `limitations`.
 */
import type { components } from '../types/generated/api'

defineProps<{
  verification: components['schemas']['Verification']
  availability: components['schemas']['Experiment']['status']
  limitations: components['schemas']['ScientificLimitation'][]
}>()
</script>

<template>
  <section class="ss" aria-label="Scientific status">
    <dl class="ss__layers">
      <div>
        <dt>Scientific capability</dt>
        <dd :data-capability="availability">{{ availability }}</dd>
      </div>
      <div>
        <dt>Verification</dt>
        <dd :data-verification="verification.status">{{ verification.status }}</dd>
      </div>
    </dl>
    <p class="ss__note">
      These layers are independent: availability is data support, verification is asset state.
    </p>
    <ul v-if="limitations.length" class="ss__limits">
      <li v-for="l in limitations" :key="l.id">
        <strong>{{ l.severity }}</strong> {{ l.code }} — {{ l.description }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.ss__layers { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap: 0.6rem; margin: 0; }
.ss__layers dt { font-size: 0.74rem; color: #666; text-transform: uppercase; letter-spacing: 0.04em; }
.ss__layers dd { margin: 0.1rem 0 0; font-weight: 600; font-size: 0.9rem; }
.ss__note { font-size: 0.78rem; color: #777; }
.ss__limits { font-size: 0.8rem; padding-left: 1.1rem; }
</style>
