<script setup lang="ts">
import type { components } from '../types/generated/api'
import BootstrapPlaceholder from '../components/BootstrapPlaceholder.vue'

defineProps<{ collection: components['schemas']['MetricCollection'] }>()
</script>
<template><BootstrapPlaceholder label="MetricsPanel" /></template>
