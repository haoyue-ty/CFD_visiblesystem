<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

defineProps<{ resource: { availability: string; error?: { message: string; evidence_refs: string[] } }; label: string }>()
import EvidenceLink from '../../scientific/EvidenceLink.vue'
</script>
<template>
  <section :data-availability="resource.availability">
    <p v-if="resource.availability === 'PARTIAL'">{{ zh("Partial:") }} {{ zh(label) }}</p>
    <slot v-if="resource.availability === 'AVAILABLE' || resource.availability === 'PARTIAL'" />
    <template v-else>
      <p role="note"><strong>{{ zh(label) }} {{ zh("— Unavailable /") }} {{ zh(resource.availability === 'MISSING' ? 'Missing' : resource.availability) }}</strong>: {{ zh(resource.error?.message) }}</p>
      <EvidenceLink v-for="id in resource.error?.evidence_refs ?? []" :key="id" :evidence-id="id" />
    </template>
  </section>
</template>
