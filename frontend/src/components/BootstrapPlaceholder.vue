<script setup lang="ts">
defineProps<{ label: string }>()
</script>
<template><section :aria-label="label">{{ label }} — Bootstrap</section></template>
