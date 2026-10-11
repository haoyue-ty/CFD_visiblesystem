<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppNavigation from './components/AppNavigation.vue'
import AppIcon from './components/AppIcon.vue'
import { navigationSection, primaryNavigation } from './presentation/navigation'
import EvidenceQuickView from './views/evidence/EvidenceQuickView.vue'
import { quickView } from './views/evidence/quickView'
const route = useRoute()
const isEntry = computed(() => route.name === 'entry')
const collapsed = ref(false)
const mobileOpen = ref(false)
const navToggle = ref<HTMLButtonElement | null>(null)
const section = computed(() => primaryNavigation.find(item => item.id === navigationSection(route.path))?.label ?? '首页')
watch(() => route.fullPath, () => { mobileOpen.value = false })
watch(mobileOpen, async open => {
  await nextTick()
  if (open) document.querySelector<HTMLButtonElement>('.appbar__close')?.focus()
  else navToggle.value?.focus()
})
</script>

<template>
  <div :inert="Boolean(quickView)" class="app-shell" :class="{ 'app-shell--entry': isEntry, 'app-shell--collapsed': collapsed }" @keydown.esc="mobileOpen = false">
    <template v-if="!isEntry">
      <AppNavigation :collapsed="collapsed" :mobile-open="mobileOpen" @toggle="collapsed = !collapsed" @close="mobileOpen = false" />
      <button v-if="mobileOpen" class="sidebar-backdrop" aria-label="关闭导航" @click="mobileOpen = false" />
    </template>
    <div class="app-content" :inert="mobileOpen">
      <header v-if="!isEntry" class="workspace-topbar">
        <div class="workspace-topbar__left"><button ref="navToggle" class="icon-button workspace-topbar__menu" aria-label="打开导航" :aria-expanded="mobileOpen" aria-controls="system-sidebar" @click="mobileOpen = !mobileOpen"><AppIcon name="menu" /></button><span>{{ section }}</span></div>
        <span class="workspace-topbar__caption">CFD 数值实验工作台</span>
      </header>
      <div id="main-content" tabindex="-1"><RouterView /></div>
    </div>
  </div>
  <EvidenceQuickView />
</template>
