<script setup lang="ts">
import { factText, knownValue, verificationLabels, type Fact } from '../../data/evidence'
import type { components } from '../../types/generated/api'
defineProps<{ verification: components['schemas']['Verification']; drift: Fact<boolean>; origins?: string[]; primary?: boolean }>()
</script>
<template>
  <div class="evidence-status">
    <strong v-if="knownValue(drift) === true" class="drift" role="alert">SOURCE DRIFT — recorded and current sources differ</strong>
    <span v-else>{{ knownValue(drift) === false ? 'NO SOURCE DRIFT' : `SOURCE DRIFT ${factText(drift)}` }}</span>
    <strong :data-testid="primary ? 'evidence-verification' : undefined">{{ verification.canonical_status }} · Source: {{ verificationLabels[verification.status] }} · DTO: {{ verification.status }}</strong>
    <strong v-if="origins?.includes('DIAGNOSTIC_RERUN')">DIAGNOSTIC_RERUN · recorded origin</strong>
  </div>
</template>
<style scoped>
.evidence-status { display: grid; gap: .35rem; margin: .6rem 0; font-size: .85rem; }
.drift { background: #fff0e8; border: 2px solid #a3312a; padding: .6rem; color: #8b251c; }
</style>
