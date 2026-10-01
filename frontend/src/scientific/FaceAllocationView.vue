<script setup lang="ts">
/**
 * FaceAllocationView — Case8 D_u FACE_FIELD renderer.
 *
 * SCIENTIFIC RULE: this component renders NATIVE FACE fields. Each orientation
 * (x-normal, y-normal) is drawn as its OWN figure with its own shape and its own
 * coordinate convention. They are never summed, averaged or resampled into a
 * single cell field — that projection is exactly the mistake this view exists to
 * prevent. The x and y face arrays have different shapes ([32,129] vs [32,128])
 * and different sample coordinates, so a single combined image would be a
 * different scientific object.
 *
 * Rendering is a direct value→colour mapping of the recorded array in C order,
 * with no interpolation. Face samples sit ON the domain edge for x-faces and ON
 * the cell edge for y-faces; the caption states the sample location so a reader
 * cannot mistake the face raster for a cell raster.
 */
import { onMounted, ref, watch } from 'vue'
import type { AllocationArrayView } from '../data/domain'

const props = defineProps<{
  array: AllocationArrayView
  /** Mask values for this orientation, if recorded (C order, same shape). */
  mask?: boolean[]
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
  const span = max - min || 1
  const img = ctx.createImageData(nx, ny)
  for (let i = 0; i < ny * nx; i += 1) {
    const [r, g, b] = colormap((values[i] - min) / span)
    const o = i * 4
    img.data[o] = r
    img.data[o + 1] = g
    img.data[o + 2] = b
    // Masked-out samples are shown dimmed, never recoloured as if in-window.
    img.data[o + 3] = props.mask && props.mask[i] === false ? 70 : 255
  }
  ctx.putImageData(img, 0, 0)

  // Overlay the face sample grid so the raster is visibly a FACE raster.
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
watch(() => [props.array.array_id, props.array.values, props.mask], draw)
</script>

<template>
  <figure class="fav" :data-array-id="array.array_id">
    <figcaption class="fav__cap">
      <span class="fav__title">{{ array.label }}</span>
      <span class="fav__loc">{{ array.location_type }}</span>
    </figcaption>
    <canvas ref="canvas" class="fav__canvas" data-testid="face-allocation-canvas" :aria-label="`${array.label} native face field, recorded values only`"></canvas>
    <p class="fav__meta">
      Shape {{ array.shape.join(' × ') }} · axes {{ array.axes.join(',') }} · samples on the
      <strong>{{ array.location_type === 'CARTESIAN_X_FACE' ? 'x-normal face plane' : 'y-normal face plane' }}</strong> ·
      rendered from recorded values only (no interpolation)
    </p>
  </figure>
</template>

<style scoped>
.fav { margin: 0; }
.fav__cap { display: flex; gap: 0.4rem; align-items: baseline; font-size: 0.85rem; font-weight: 600; }
.fav__loc { font-size: 0.7rem; font-weight: 500; color: #555; background: #eef2f7; border: 1px solid #ccd6e0; border-radius: 3px; padding: 0 0.3rem; }
.fav__canvas { width: 100%; max-width: 34rem; image-rendering: pixelated; border: 1px solid #ccc; background: #fafafa; }
.fav__meta { font-size: 0.72rem; color: #777; margin: 0.15rem 0 0; }
</style>
