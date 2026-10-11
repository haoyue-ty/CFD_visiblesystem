<script setup lang="ts">
import { computed } from 'vue'
import { Activity, ArrowRight, ArrowUp, BookOpen, ChartNoAxesCombined, CirclePlus, FileText, House, Layers, Menu, PanelLeftClose, PanelLeftOpen, Sparkles, X, CircleCheck, CircleHelp, SlidersHorizontal, FlaskConical } from '@lucide/vue'
const props = defineProps<{ name: string }>()
const icons = { dashboard: House, plus: CirclePlus, activity: Activity, layers: Layers, book: BookOpen, arrow: ArrowRight, up: ArrowUp, chart: ChartNoAxesCombined, file: FileText, spark: Sparkles, menu: Menu, collapse: PanelLeftClose, expand: PanelLeftOpen, close: X, check: CircleCheck, help: CircleHelp, settings: SlidersHorizontal, flask: FlaskConical }
const icon = computed(() => icons[props.name as keyof typeof icons] ?? ArrowRight)
</script>
<template><component :is="icon" class="sp-icon" :size="20" :stroke-width="1.7" aria-hidden="true" focusable="false" /></template>
