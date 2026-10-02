<script setup lang="ts">
import { zh } from '../presentation/zh-CN'

defineProps<{ label: string }>()
</script>
<template><section :aria-label="zh(label)">{{ zh(label) }} {{ zh("— Bootstrap") }}</section></template>
