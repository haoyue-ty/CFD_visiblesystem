<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import type { components } from '../../types/generated/api'
const props = defineProps<{ field: components['schemas']['ScientificField']; minimum: number; maximum: number }>()
const canvas = ref<HTMLCanvasElement>()
function draw() {
  if (!canvas.value) return
  const [ny, nx] = props.field.shape
  if (!nx || !ny) return
  canvas.value.width = nx; canvas.value.height = ny
  const ctx = canvas.value.getContext('2d')
  if (!ctx) return
  const pixels = ctx.createImageData(nx, ny)
  for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) {
    const value = props.field.values[y * nx + x] ?? 0
    const t = props.maximum > props.minimum ? Math.max(0, Math.min(1, (value - props.minimum) / (props.maximum - props.minimum))) : .5
    const i = ((ny - 1 - y) * nx + x) * 4
    pixels.data[i] = Math.round(30 + 220 * t); pixels.data[i + 1] = Math.round(65 + 140 * (1 - Math.abs(2*t-1)))
    pixels.data[i + 2] = Math.round(200 - 160 * t); pixels.data[i + 3] = 255
  }
  ctx.putImageData(pixels, 0, 0)
}
onMounted(draw); watch(() => [props.field, props.minimum, props.maximum], draw)
</script>
<template>
  <figure><canvas ref="canvas" role="img" :style="{ aspectRatio: String(((field.extent_x[1] ?? 1)-(field.extent_x[0] ?? 0))/((field.extent_y[1] ?? 1)-(field.extent_y[0] ?? 0))) }" :aria-label="`${field.label}，t=${field.time}，统一色标 ${minimum} 至 ${maximum}`" />
    <figcaption>{{ field.label }} · {{ field.unit }} · t={{ field.time }} · {{ field.shape[1] }}×{{ field.shape[0] }}<br>
      x={{ field.extent_x.join('…') }} · y={{ field.extent_y.join('…') }}（上方为 y 最大值）<br>
      {{ field.snapshot_id }} · source {{ field.source_sha256 }}</figcaption></figure>
</template>
<style scoped>
figure { margin: 0; min-width: 0; }canvas { width: 100%; box-sizing: border-box; image-rendering: pixelated; border: 1px solid #c5d2df; }
figcaption { font-size: .75rem; color: #607080; overflow-wrap: anywhere; line-height: 1.7; }
</style>
