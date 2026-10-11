<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const active = computed(() => route.path.startsWith('/workspace/compare') ? 'compare' : /^\/(workspace\/sweeps|sweeps)(\/|$)/.test(route.path) ? 'sweeps' : 'runs')
const sections = [
  { id: 'runs', path: '/workspace', label: '全部任务' },
  { id: 'compare', path: '/workspace/compare', label: '运行对比' },
  { id: 'sweeps', path: '/workspace/sweeps', label: '参数扫描' },
]
</script>
<template><nav class="sp-subnav" aria-label="运行任务分区"><RouterLink v-for="item in sections" :key="item.id" :to="item.path" :aria-current="active === item.id ? 'page' : undefined">{{ item.label }}</RouterLink></nav></template>
