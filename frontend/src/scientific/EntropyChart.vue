<script setup lang="ts">
import type { components } from '../types/generated/api'
import BootstrapPlaceholder from '../components/BootstrapPlaceholder.vue'

defineProps<{ history: components['schemas']['EntropyHistory'] }>()
</script>
<template><BootstrapPlaceholder label="EntropyChart" /></template>
