<script setup lang="ts">
import ExperimentPage from './ExperimentPage.vue'
import CylinderPage from './CylinderPage.vue'
import ClosurePage from './ClosurePage.vue'
defineProps<{ experiment_id: string }>()
</script>
<template><ClosurePage v-if="experiment_id === 'entropy-closure'" /><CylinderPage v-else-if="experiment_id === 'cylinder'" /><ExperimentPage v-else :key="experiment_id" :experiment_id="experiment_id" /></template>
