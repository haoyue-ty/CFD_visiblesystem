<script setup lang="ts">
import { zh } from '../../presentation/zh-CN'

import { onMounted, ref, watch } from 'vue'
import type { FieldBundle } from '../../data/cylinder'
import ResultContext from './ResultContext.vue'
const props = defineProps<{ bundle: FieldBundle }>()
const canvas = ref<HTMLCanvasElement | null>(null)
function draw() {
  const el = canvas.value
  const [rows, cols] = props.bundle.field.array_ref.descriptor.shape
  if (!el || props.bundle.values.length !== rows * cols) return
  el.width = cols; el.height = rows
  const ctx = el.getContext('2d')
  if (!ctx) return
  const min = Math.min(...props.bundle.values), max = Math.max(...props.bundle.values)
  const pixels = ctx.createImageData(cols, rows)
  props.bundle.values.forEach((value, i) => {
    const t = (value - min) / (max - min || 1)
    pixels.data.set([Math.round(255 * t), Math.round(255 * (1 - t)), 160, 255], i * 4)
  })
  ctx.putImageData(pixels, 0, 0)
}
onMounted(draw)
watch(() => props.bundle, draw)
</script>
<template>
  <figure>
    <figcaption>{{ zh(bundle.field.label) }} · {{ zh(bundle.field.domain.location_type) }} {{ zh("· instantaneous") }}</figcaption>
    <canvas ref="canvas" data-testid="instantaneous-field" role="img" :aria-label="zh(bundle.field.label) + ' · 已记录原生面样本'" />
    <p>{{ zh("Native index raster: rows=") }}{{ zh(bundle.field.array_ref.descriptor.axes[0]) }}{{ zh(", columns=") }}{{ zh(bundle.field.array_ref.descriptor.axes[1]) }} {{ zh("· shape") }} {{ zh(bundle.field.array_ref.descriptor.shape.join(' × ')) }}{{ zh(". Colour range:") }} {{ zh(Math.min(...bundle.values)) }} … {{ zh(Math.max(...bundle.values)) }} {{ zh(bundle.field.result.unit.label) }}{{ zh(". No Cartesian projection or interpolation.") }}</p>
    <ResultContext :result="bundle.field.result" :definitions="bundle.definitions" />
  </figure>
</template>
<style scoped>figure { margin: 0; } canvas { width: 100%; max-width: 42rem; image-rendering: pixelated; border: 1px solid #ddd; } p { font-size: .85rem; }</style>
