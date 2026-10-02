<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { factText, knownValue, verificationText, type Fact } from '../../data/evidence'
import type { components } from '../../types/generated/api'
defineProps<{ verification: components['schemas']['Verification']; drift: Fact<boolean>; origins?: string[]; primary?: boolean; subject?: string }>()
</script>
<template>
  <div class="evidence-status">
    <strong v-if="knownValue(drift) === true" class="drift" role="alert">检测到{{ subject ?? '源码' }}变化：记录时与当前来源不同</strong>
    <span v-else>{{ knownValue(drift) === false ? `记录时${subject ?? '源码'}与当前${subject ?? '源码'}一致` : `${subject ?? '源码'}一致性：${factText(drift)}` }}</span>
    <strong :data-testid="primary ? 'evidence-verification' : undefined" :title="verificationText(verification)">{{ verificationText(verification) }}</strong>
    <strong v-if="origins?.includes('DIAGNOSTIC_RERUN')">{{ zh("DIAGNOSTIC_RERUN · recorded origin") }}</strong>
  </div>
</template>
<style scoped>
.evidence-status { display: grid; gap: .35rem; margin: .6rem 0; font-size: .85rem; }
.drift { background: #fff0e8; border: 2px solid #a3312a; padding: .6rem; color: #8b251c; }
</style>
