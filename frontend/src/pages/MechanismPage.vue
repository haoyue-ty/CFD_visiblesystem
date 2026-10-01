<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MechanismView from '../views/mechanism/MechanismView.vue'
const route = useRoute()
const sourceScene = computed(() => ['2', '3'].includes(String(route.query.source_scene)) ? String(route.query.source_scene) : null)
const back = computed(() => sourceScene.value ? { name: 'explore', query: { ...route.query, scene: sourceScene.value } } : { name: 'lab' })
</script>
<template>
  <main data-page="mechanism" class="mechanism-page">
    <RouterLink :to="back" data-testid="mechanism-return">← {{ sourceScene ? `Back to Explore S${sourceScene}` : 'Back to Lab' }}</RouterLink>
    <h1>Mechanism Explorer</h1>
    <MechanismView />
  </main>
</template>
<style scoped>.mechanism-page { max-width: 90rem; padding: 1.5rem; margin: auto; }</style>
