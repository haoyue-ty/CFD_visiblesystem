<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppNavigation from './components/AppNavigation.vue'
import AppIcon from './components/AppIcon.vue'
import AuthControls from './components/AuthControls.vue'
import { loadAuthSession } from './data/auth'
import { navigationSection, primaryNavigation } from './presentation/navigation'
import EvidenceQuickView from './views/evidence/EvidenceQuickView.vue'
import { quickView } from './views/evidence/quickView'
const route = useRoute()
const router = useRouter()
const isEntry = computed(() => ['entry', 'research-details', 'login', 'register'].includes(String(route.name)))
function sessionExpired() { if (route.meta.requiresAuth) void router.replace({ name: 'login', query: { redirect: route.fullPath } }) }
onMounted(() => { void loadAuthSession().catch(() => {}); window.addEventListener('shockpath:auth-expired', sessionExpired) })
onUnmounted(() => window.removeEventListener('shockpath:auth-expired', sessionExpired))
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
        <AuthControls />
      </header>
      <div id="main-content" tabindex="-1"><RouterView /></div>
    </div>
  </div>
  <EvidenceQuickView />
</template>
