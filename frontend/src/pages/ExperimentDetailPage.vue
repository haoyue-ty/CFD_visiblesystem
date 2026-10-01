<script setup lang="ts">
import ExperimentPage from './ExperimentPage.vue'
import CylinderPage from './CylinderPage.vue'
defineProps<{ experiment_id: string }>()
</script>
<template><CylinderPage v-if="experiment_id === 'cylinder'" /><ExperimentPage v-else :key="experiment_id" :experiment_id="experiment_id" /></template>
