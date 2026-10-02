<script setup lang="ts">
import { zh } from '../presentation/zh-CN'

import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const scene = computed(() => typeof route.query.source_scene === 'string' && /^[1-7]$/.test(route.query.source_scene) ? route.query.source_scene : null)
const target = computed(() => {
  const raw = route.query.explore_return
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      if (parsed.name === 'explore' && String(parsed.query?.scene) === scene.value) return parsed
    } catch { /* Use the validated scene below. */ }
  }
  return { name: 'explore', query: { scene: scene.value } }
})
</script>
<template><RouterLink v-if="scene" :to="target" data-testid="explore-return">{{ zh("← Back to Explore Scene") }} {{ zh(scene) }}</RouterLink></template>
