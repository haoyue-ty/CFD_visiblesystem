<script setup lang="ts">
import type { components } from '../types/generated/api'

defineProps<{ evidenceId: components['schemas']['EvidenceRecord']['evidence_id'] }>()
</script>
<template><RouterLink :to="{ name: 'evidence', params: { evidence_id: evidenceId } }">Evidence</RouterLink></template>
