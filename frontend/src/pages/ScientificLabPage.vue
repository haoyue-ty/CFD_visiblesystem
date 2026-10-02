<script setup lang="ts">
import ExploreReturn from '../components/ExploreReturn.vue'
import GateComparisonView from '../views/case8/GateComparisonView.vue'
import SpectralTab from '../views/case8/SpectralTab.vue'
defineProps<{ experiment_id: string }>()
</script>
<template><main data-page="scientific-lab" class="science-lab"><ExploreReturn /><h1>{{ experiment_id === 'gate' ? 'Gate Allocation' : 'Spectral Lab' }}</h1><GateComparisonView v-if="experiment_id === 'gate'" /><SpectralTab v-else /></main></template>
<style scoped>.science-lab { padding: 1.5rem; max-width: 90rem; margin: auto; }</style>
