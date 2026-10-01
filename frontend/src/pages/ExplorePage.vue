<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contentService, type ScenePreset } from '../data/content'
import type { Loaded } from '../data/domain'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import MechanismView from '../views/mechanism/MechanismView.vue'
const route = useRoute()
const sceneId = computed(() => route.query.scene === undefined ? 2 : Number(route.query.scene))
const scene = ref<Loaded<ScenePreset> | null>(null)
let controller: AbortController | null = null
watch(sceneId, async id => {
  controller?.abort()
  const current = new AbortController()
  controller = current
  scene.value = null
  try {
    const result = await contentService.scene(id, current.signal)
    if (controller === current) scene.value = result
  } catch (error) { if ((error as Error).name !== 'AbortError') throw error }
}, { immediate: true })
onUnmounted(() => controller?.abort())
const workspace = computed(() => ({ name: 'mechanism', query: { ...route.query, source_scene: String(sceneId.value) } }))
</script>
<template>
  <main data-page="explore" class="explore-page">
    <h1>Explore</h1>
    <nav aria-label="Mechanism scenes"><RouterLink :to="{ name: 'explore', query: { scene: '2' } }">S2 · Trigger and output</RouterLink> · <RouterLink :to="{ name: 'explore', query: { scene: '3' } }">S3 · Trigger ≠ Output</RouterLink></nav>
    <LoadStateBlock :loaded="scene" target="Explore scene">
      <template v-if="scene?.data">
        <h2 data-testid="scene-title">S{{ scene.data.scene_id }} · {{ scene.data.title }}</h2>
        <p>{{ scene.data.conclusion }}</p>
        <template v-if="scene.data.view_kind === 'MECHANISM'">
          <RouterLink :to="workspace" data-testid="explore-open-mechanism">Open Mechanism Explorer workspace</RouterLink>
          <MechanismView :controls-enabled="scene.data.scene_id === 3" />
        </template>
        <p v-else>This window delivers Mechanism scenes S2/S3. This scene's interactive view is not delivered here.</p>
      </template>
    </LoadStateBlock>
  </main>
</template>
<style scoped>.explore-page { max-width: 90rem; padding: 1.5rem; margin: auto; }</style>
