<script setup lang="ts">
/**
 * CellAllocationView — Gate CELL_FIELD renderer.
 *
 * SCIENTIFIC RULE: this component renders a CELL field. Its samples are cell
 * CENTRES, and each recorded value already contains the spatial measure (the
 * Gate rule is sum(cells) with no extra dx/dy/dt). It is therefore NOT a
 * downsampled face field and NOT interchangeable with FaceAllocationView.
 *
 * This component deliberately does not share a renderer with the face view:
 * the two representations have different sample coordinates, different arrays
 * and a different measure contract, so sharing code would invite exactly the
 * "same scientific object" confusion the window forbids.
 */
import { onMounted, ref, watch } from 'vue'
import type { AllocationArrayView } from '../data/domain'

const props = defineProps<{
  array: AllocationArrayView
  mask?: boolean[]
  colourExtent?: [number, number]
}>()

const canvas = ref<HTMLCanvasElement | null>(null)

function colormap(t: number): [number, number, number] {
  const c = Math.max(0, Math.min(1, t))
  if (c < 0.5) {
    const k = c / 0.5
    return [Math.round(30 + k * 225), Math.round(60 + k * 195), Math.round(160 + k * 95)]
  }
  const k = (c - 0.5) / 0.5
  return [Math.round(255), Math.round(255 - k * 205), Math.round(255 - k * 235)]
}

function draw() {
  const el = canvas.value
  if (!el) return
  const ctx = el.getContext('2d')
  if (!ctx) return
  const [ny, nx] = props.array.shape
  const values = props.array.values
  if (values.length !== ny * nx) return

  el.width = nx
  el.height = ny
  ctx.clearRect(0, 0, nx, ny)

  let min = Infinity
  let max = -Infinity
  for (const v of values) {
    if (v < min) min = v
    if (v > max) max = v
  }
  if (props.colourExtent) [min, max] = props.colourExtent
  const span = max - min || 1
  const img = ctx.createImageData(nx, ny)
  for (let i = 0; i < ny * nx; i += 1) {
    const [r, g, b] = colormap((values[i] - min) / span)
    const o = i * 4
    img.data[o] = r
    img.data[o + 1] = g
    img.data[o + 2] = b
    img.data[o + 3] = props.mask && props.mask[i] === false ? 70 : 255
  }
  ctx.putImageData(img, 0, 0)

  // Cell-centre grid: drawn ON cell boundaries so the raster reads as cells.
  if (nx <= 160) {
    ctx.strokeStyle = 'rgba(0,0,0,0.18)'
    ctx.lineWidth = 0.02
    for (let i = 0; i <= nx; i += 1) {
      ctx.beginPath()
      ctx.moveTo(i, 0)
      ctx.lineTo(i, ny)
      ctx.stroke()
    }
  }
}

onMounted(draw)
watch(() => [props.array.array_id, props.array.values, props.mask, props.colourExtent], draw)
</script>

<template>
  <figure class="cav" :data-array-id="array.array_id" :data-colour-min="colourExtent?.[0]" :data-colour-max="colourExtent?.[1]">
    <figcaption class="cav__cap">
      <span class="cav__title">{{ array.label }}</span>
      <span class="cav__loc">{{ array.location_type }}</span>
    </figcaption>
    <canvas ref="canvas" class="cav__canvas" data-testid="cell-allocation-canvas" :aria-label="`${array.label} cell field, recorded values only`"></canvas>
    <p class="cav__meta">
      Shape {{ array.shape.join(' × ') }} · axes {{ array.axes.join(',') }} · samples at
      <strong>cell centres</strong> · spatial measure already included in each value ·
      rendered from recorded values only (no interpolation)
    </p>
  </figure>
</template>

<style scoped>
.cav { margin: 0; }
.cav__cap { display: flex; gap: 0.4rem; align-items: baseline; font-size: 0.85rem; font-weight: 600; }
.cav__loc { font-size: 0.7rem; font-weight: 500; color: #2d5a3d; background: #eaf5ee; border: 1px solid #b6d9c4; border-radius: 3px; padding: 0 0.3rem; }
.cav__canvas { width: 100%; max-width: 34rem; image-rendering: pixelated; border: 1px solid #ccc; background: #fafafa; }
.cav__meta { font-size: 0.72rem; color: #777; margin: 0.15rem 0 0; }
</style>
