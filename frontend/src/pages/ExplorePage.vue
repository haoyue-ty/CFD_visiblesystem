<script setup lang="ts">
import { zh, sceneCopy } from '../presentation/zh-CN'

import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import { contentService, type SceneList, type ScenePreset } from '../data/content'
import { createRequestGuard, type Loaded } from '../data'
import LoadStateBlock from '../components/LoadStateBlock.vue'
import MechanismView from '../views/mechanism/MechanismView.vue'
import EntropyTab from '../views/case8/EntropyTab.vue'
import GateComparisonView from '../views/case8/GateComparisonView.vue'
import SpectralTab from '../views/case8/SpectralTab.vue'
import CrossFlowView from '../views/crossflow/CrossFlowView.vue'
import EvidenceDetailView from '../views/evidence/EvidenceDetailView.vue'
import EvidenceLink from '../scientific/EvidenceLink.vue'
const route = useRoute(), router = useRouter()
const sceneId = computed(() => route.query.scene === undefined ? 1 : Number(route.query.scene))
const validScene = computed(() => typeof route.query.scene !== 'object' && Number.isInteger(sceneId.value) && sceneId.value >= 1 && sceneId.value <= 7)
const scenes = ref<Loaded<SceneList> | null>(null), scene = ref<Loaded<ScenePreset> | null>(null)
const listGuard = createRequestGuard(), sceneGuard = createRequestGuard()
async function loadList() {
  scenes.value = null
  const result = await listGuard.run(signal => contentService.scenes(signal))
  if (result?.data && (result.data.items.length !== 7 || result.data.items.some((s, i) => s.scene_id !== i + 1))) {
    scenes.value = { state: 'ERROR', data: null, origin: 'SCHEMATIC', reason: 'Expected seven registered Explore scenes' }
  } else if (result) scenes.value = result
}
void loadList()
watch([sceneId, validScene], async ([id]) => {
  sceneGuard.cancel(); scene.value = null
  if (!validScene.value) {
    scene.value = { state: 'ERROR', data: null, origin: 'SCHEMATIC', reason: 'Invalid scene. Choose a registered Scene 1…7.' }; return
  }
  const result = await sceneGuard.run(signal => contentService.scene(id, signal))
  if (result?.data && result.data.scene_id !== id) scene.value = { state: 'ERROR', data: null, origin: 'SCHEMATIC', reason: 'Scene identity mismatch' }
  else if (result) scene.value = result
}, { immediate: true })
onBeforeUnmount(() => { listGuard.cancel(); sceneGuard.cancel() })
function control(name: string) { return scene.value?.data?.allowed_controls.find(c => c.name === name)?.allowed_values ?? [] }
const config = computed(() => control('config').includes(String(route.query.config)) ? String(route.query.config) : control('config')[0] ?? '')
const evidenceId = computed(() => control('evidence_id').includes(String(route.query.evidence_id)) ? String(route.query.evidence_id) : control('evidence_id')[0] ?? '')
const spectralTargets = computed(() => scene.value?.data?.targets.map(t => t.config_id.state === 'KNOWN' ? t.config_id.value : '').filter(Boolean) ?? [])
const returnTo = computed(() => ({ name: 'explore', query: { ...route.query, scene: String(sceneId.value) } }))
function update(key: string, value: string) { void router.push({ query: { ...route.query, scene: String(sceneId.value), [key]: value } }) }
const labTarget = computed<RouteLocationRaw>(() => {
  const context = { source_scene: String(sceneId.value), explore_return: JSON.stringify(returnTo.value) }
  if ([2, 3].includes(sceneId.value)) return { name: 'mechanism', query: { ...route.query, ...context } }
  if (sceneId.value === 6) return { name: 'cross-flow', query: { ...context, case8_config: 'D_u', cylinder_config: 'D_u', tab: 'allocation' } }
  if (sceneId.value === 4) return { name: 'experiment', params: { experiment_id: 'gate' }, query: { ...context, config: 'Acoustic', tab: 'allocation' } }
  if (sceneId.value === 5) return { name: 'experiment', params: { experiment_id: 'spectrum' }, query: { ...context, config: spectralTargets.value[1], tab: 'spectral', spectral_q: spectralTargets.value[1], spectral_mode: '4' } }
  return { name: 'experiment', params: { experiment_id: 'case8' }, query: { ...context, config: sceneId.value === 1 ? config.value : 'D_u', tab: 'entropy' } }
})
const evidenceRefs = computed(() => scene.value?.data?.evidence_refs ?? [])
const mainConclusion = computed(() => sceneCopy[sceneId.value]?.conclusion)
</script>
<template>
  <main data-page="explore" class="explore-page">
    <h1>{{ zh("Explore / Guided Story") }}</h1>
    <p>{{ zh("Seven curated scenes · about 250 seconds at your own pace.") }}</p>
    <LoadStateBlock :loaded="scenes" :target="zh('Explore scene navigation')">
      <nav v-if="scenes?.data" :aria-label="zh('Scene navigation')" class="scene-nav">
        <RouterLink v-for="item in scenes.data.items" :key="item.scene_id" :to="{ name: 'explore', query: { scene: String(item.scene_id) } }" :aria-current="sceneId === item.scene_id ? 'step' : undefined" :data-testid="`scene-nav-${item.scene_id}`">{{ String(item.scene_id).padStart(2, '0') }} · {{ sceneCopy[item.scene_id]?.title }}</RouterLink>
      </nav>
    </LoadStateBlock>
    <button v-if="scenes?.state === 'ERROR'" @click="loadList">{{ zh("Retry scene navigation") }}</button>
    <LoadStateBlock :loaded="scene" :target="zh('Explore scene')">
      <template v-if="scene?.data && scenes?.data">
        <header>
          <p data-testid="scene-progress">第 {{ scene.data.scene_id }} 幕 / 共 7 幕</p>
          <h2 data-testid="scene-title">{{ String(scene.data.scene_id).padStart(2, '0') }} · {{ sceneCopy[sceneId]?.title }}</h2>
          <p>{{ sceneCopy[sceneId]?.description }}</p>
          <p class="conclusion" data-testid="scene-conclusion">{{ zh(mainConclusion) }}</p>
          <RouterLink :to="labTarget" data-testid="explore-open-lab">{{ zh("Open in Lab / Full Analysis") }}</RouterLink>
          <RouterLink v-if="[2, 3].includes(sceneId)" :to="labTarget" data-testid="explore-open-mechanism">{{ zh("Open Mechanism Explorer workspace") }}</RouterLink>
          <div data-testid="scene-evidence"><strong>{{ zh("Evidence") }}</strong> <EvidenceLink v-for="id in evidenceRefs" :key="id" :evidence-id="id" :return-to="returnTo" /></div>
        </header>
        <section class="scientific-content" :aria-label="zh('Scientific content area')" :key="sceneId">
          <template v-if="sceneId === 1">
            <label>{{ zh("Case8 configuration") }} <select data-testid="explore-entropy-config" :value="config" @change="update('config', ($event.target as HTMLSelectElement).value)"><option v-for="id in control('config')" :key="id" :value="id">{{ zh(id) }}</option></select></label>
            <EntropyTab :key="config" :config-id="config" guided />
          </template>
          <MechanismView v-else-if="[2, 3].includes(sceneId)" :controls-enabled="sceneId === 3" />
          <GateComparisonView v-else-if="sceneId === 4" />
          <SpectralTab v-else-if="sceneId === 5" :guided-targets="spectralTargets" />
          <CrossFlowView v-else-if="sceneId === 6" guided />
          <template v-else-if="sceneId === 7">
            <label>{{ zh("Story evidence") }} <select data-testid="explore-evidence-select" :value="evidenceId" @change="update('evidence_id', ($event.target as HTMLSelectElement).value)"><option v-for="id in control('evidence_id')" :key="id" :value="id">{{ zh(id) }}</option></select></label>
            <EvidenceLink :evidence-id="evidenceId" :return-to="returnTo" />
            <EvidenceDetailView :key="evidenceId" :evidence_id="evidenceId" embedded />
          </template>
        </section>
        <details><summary>{{ zh("Scene limitations") }}</summary><p v-for="lim in scene.data.limitations" :key="lim.id">{{ zh(lim.code) }} — {{ zh(lim.description) }}</p></details>
      </template>
    </LoadStateBlock>
    <footer class="scene-actions">
      <RouterLink v-if="validScene && sceneId > 1" :to="{ name: 'explore', query: { scene: String(sceneId - 1) } }" data-testid="scene-previous">{{ zh("Previous") }}</RouterLink><button v-else disabled>{{ zh("Previous") }}</button>
      <RouterLink v-if="validScene && sceneId < 7" :to="{ name: 'explore', query: { scene: String(sceneId + 1) } }" data-testid="scene-next">{{ zh("Next") }}</RouterLink><button v-else disabled>{{ zh("Next") }}</button>
      <RouterLink v-if="sceneId === 7 || !validScene" :to="{ name: 'explore', query: { scene: '1' } }">{{ zh("Restart at Scene 1") }}</RouterLink>
      <RouterLink v-if="sceneId === 7" :to="{ name: 'home' }">{{ zh("Home") }}</RouterLink>
    </footer>
  </main>
</template>
<style scoped>
.explore-page { max-width: 90rem; padding: 1.5rem; margin: auto; }
.scene-nav { display: flex; gap: .6rem; flex-wrap: wrap; }
.scene-nav a { border: 1px solid #ddd; padding: .5rem; font-size: .8rem; text-decoration: none; }
.scene-nav [aria-current="step"] { background: #eaf1fb; border-color: #1a4f8a; font-weight: bold; }
.conclusion { padding: .75rem; border-left: 3px solid #1a4f8a; background: #f2f6fb; }
header { margin: 1rem 0; } header > a, [data-testid="scene-evidence"] a { margin-right: .8rem; }
.scientific-content { border: 1px solid #ddd; padding: 1rem; margin: 1rem 0; overflow-x: auto; }
.scene-actions { display: flex; gap: 1rem; margin-top: 1rem; }
@media(max-width: 600px) { .explore-page { padding: .7rem; } .scientific-content { padding: .5rem; } }
</style>
