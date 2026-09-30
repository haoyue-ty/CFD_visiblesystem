<script setup lang="ts">
import type { components } from '../types/generated/api'
import BootstrapPlaceholder from '../components/BootstrapPlaceholder.vue'

defineProps<{
  verification: components['schemas']['Verification']
  availability: components['schemas']['Experiment']['status']
  limitations: components['schemas']['ScientificLimitation'][]
}>()
</script>
<template><BootstrapPlaceholder label="ScientificStatus" /></template>
