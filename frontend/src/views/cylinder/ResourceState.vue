<script setup lang="ts">
defineProps<{ resource: { availability: string; error?: { message: string; evidence_refs: string[] } }; label: string }>()
import EvidenceLink from '../../scientific/EvidenceLink.vue'
</script>
<template>
  <section :data-availability="resource.availability">
    <p v-if="resource.availability === 'PARTIAL'">Partial: {{ label }}</p>
    <slot v-if="resource.availability === 'AVAILABLE' || resource.availability === 'PARTIAL'" />
    <template v-else>
      <p role="note"><strong>{{ label }} — Unavailable / {{ resource.availability === 'MISSING' ? 'Missing' : resource.availability }}</strong>: {{ resource.error?.message }}</p>
      <EvidenceLink v-for="id in resource.error?.evidence_refs ?? []" :key="id" :evidence-id="id" />
    </template>
  </section>
</template>
