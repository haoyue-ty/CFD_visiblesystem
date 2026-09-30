<script setup lang="ts">
import type { components } from '../types/generated/api'
import BootstrapPlaceholder from '../components/BootstrapPlaceholder.vue'

defineProps<{
  snapshot: components['schemas']['FieldSnapshot']
  field: components['schemas']['FieldDescriptor']
  array?: components['schemas']['ScientificArray']
}>()
</script>
<template><BootstrapPlaceholder label="SnapshotViewer" /></template>
