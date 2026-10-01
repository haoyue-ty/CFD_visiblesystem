<script setup lang="ts">
import EvidenceDetailView from '../views/evidence/EvidenceDetailView.vue'
defineProps<{ evidence_id: string }>()
</script>
<template><main data-page="evidence"><EvidenceDetailView :evidence_id="evidence_id" /></main></template>
