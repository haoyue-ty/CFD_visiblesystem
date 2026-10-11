<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { activeProvider } from '../data'
import { useCaseRegistry } from '../data/v2/useCaseRegistry'
import { primaryNavigation, navigationSection } from '../presentation/navigation'
import MockBadge from './MockBadge.vue'
import AppIcon from './AppIcon.vue'
import '../presentation/navigation.css'

const route = useRoute()
defineProps<{ collapsed: boolean; mobileOpen: boolean }>()
defineEmits<{ toggle: []; close: [] }>()
const registry = useCaseRegistry()
const active = computed(() => navigationSection(route.path))
const service = computed(() => {
  if (registry.isError.value || !registry.data.value) return { kind: 'unknown', label: '服务状态未知' }
  return registry.data.value.cases.some(c => c.execution_available)
    ? { kind: 'available', label: '求解服务可用' }
    : { kind: 'unavailable', label: '求解服务未启动' }
})
</script>
<template>
  <aside id="system-sidebar" class="appbar" :class="{ 'appbar--collapsed': collapsed, 'appbar--open': mobileOpen }" aria-label="工作空间侧栏">
    <a class="appbar__skip" href="#main-content">跳到页面内容</a>
    <div class="appbar__top">
      <RouterLink to="/home" class="appbar__brand" aria-label="ShockPath 首页">
        <AppIcon name="activity" />
        <span>ShockPath<span class="appbar__brand-caption">CFD 数值实验工作台</span></span>
      </RouterLink>
      <button class="icon-button appbar__collapse" :aria-label="collapsed ? '展开侧栏' : '收起侧栏'" @click="$emit('toggle')"><AppIcon :name="collapsed ? 'expand' : 'collapse'" /></button>
      <button class="icon-button appbar__close" aria-label="关闭侧栏" @click="$emit('close')"><AppIcon name="close" /></button>
    </div>
    <RouterLink to="/experiments/new" class="appbar__new" :aria-label="collapsed ? '开始新计算' : undefined" :title="collapsed ? '开始新计算' : undefined"><AppIcon name="plus" /><span>开始新计算</span></RouterLink>
    <p class="appbar__group-label">工作空间</p>
    <nav aria-label="系统导航" class="appbar__nav">
      <RouterLink v-for="item in primaryNavigation" :key="item.id" :to="item.path"
        class="appbar__item" :class="{ 'appbar__item--active': active === item.id }"
        :aria-current="active === item.id ? 'page' : undefined" :data-section="item.id" :title="collapsed ? item.label : undefined" :aria-label="item.label">
        <AppIcon :name="item.icon" /><span>{{ item.label }}</span>
      </RouterLink>
    </nav>
    <div class="appbar__bottom">
      <div class="appbar__env">
        <span class="appbar__service" :data-status="service.kind" data-testid="solver-service-status" role="status">
          <AppIcon :name="service.kind === 'available' ? 'check' : 'help'" /><span>{{ service.label }}</span>
        </span>
        <span v-if="activeProvider.kind === 'API'" class="appbar__source" data-testid="provider-kind">真实数据 API</span>
        <MockBadge v-else origin="MOCK" verification="NOT_APPLICABLE" compact />
      </div>
    <RouterLink to="/" class="appbar__exit" :aria-label="collapsed ? '返回开始页' : undefined" :title="collapsed ? '返回开始页' : undefined"><AppIcon name="arrow" /><span>返回开始页</span></RouterLink>
    </div>
  </aside>
</template>
