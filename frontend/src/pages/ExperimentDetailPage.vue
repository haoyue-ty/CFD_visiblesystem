<script setup lang="ts">
import ExperimentPage from './ExperimentPage.vue'
import ScientificLabPage from './ScientificLabPage.vue'
import CylinderPage from './CylinderPage.vue'
import ClosurePage from './ClosurePage.vue'
defineProps<{ experiment_id: string }>()
</script>
<template><ClosurePage v-if="experiment_id === 'entropy-closure'" /><CylinderPage v-else-if="experiment_id === 'cylinder'" /><ScientificLabPage v-else-if="['gate', 'spectrum', 'modal-validation'].includes(experiment_id)" :key="experiment_id" :experiment_id="experiment_id" /><ExperimentPage v-else :key="experiment_id" :experiment_id="experiment_id" /></template>
