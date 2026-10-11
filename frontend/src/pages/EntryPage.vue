<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <main class="entry" data-page="entry" aria-label="ShockPath 实验入口">
    <RouterLink :to="{ name: 'home', query: route.query, hash: route.hash }" class="entry__start" data-testid="start-experiment">开始实验</RouterLink>
  </main>
</template>

<style scoped>
#app main.entry { display: grid; place-items: center; min-height: 100svh; max-width: none; padding: 24px; background: #edf3fb url('/images/entry-atmosphere.webp') center / cover no-repeat; }
.entry__start { display: inline-flex; justify-content: center; align-items: center; min-width: 188px; min-height: 60px; padding: 16px 36px; border-radius: 999px; background: var(--sp-primary); color: white; font-size: 19px; font-weight: 500; letter-spacing: 2px; text-decoration: none; box-shadow: 0 8px 28px #4d6bfe26; transition: background .2s, transform .2s, box-shadow .2s; }
.entry__start:hover { background: var(--sp-primary-hover); transform: translateY(-2px); box-shadow: 0 12px 32px #4d6bfe35; }
.entry__start:active { transform: translateY(0); }
@media (max-width: 600px) { .entry__start { min-width: 172px; min-height: 56px; font-size: 18px; } }
</style>
