<script setup lang="ts">
import ExperimentPage from './ExperimentPage.vue'
import ScientificLabPage from './ScientificLabPage.vue'
import CylinderPage from './CylinderPage.vue'
defineProps<{ experiment_id: string }>()
</script>
<template><CylinderPage v-if="experiment_id === 'cylinder'" /><ScientificLabPage v-else-if="['gate', 'spectrum', 'modal-validation'].includes(experiment_id)" :experiment_id="experiment_id" /><ExperimentPage v-else :key="experiment_id" :experiment_id="experiment_id" /></template>
