<script setup lang="ts">
import { zh } from '../presentation/zh-CN'

/**
 * SnapshotViewer — Canvas 2D renderer for one recorded field.
 *
 * HARD RULE (Window 3): render ONLY the recorded values. Never interpolate
 * intermediate frames, never smooth, never fabricate values that do not exist.
 * The array is plotted exactly as delivered (C order, y rows then x columns).
 *
 * Public props kept stable per README: `snapshot`, `field`, optional `array`.
 * In the Window 3 slice `snapshot`/`field` are the provider's mock view objects;
 * `array` may carry the fetched values.
 */
import { onMounted, ref, watch } from 'vue'
import type { FieldData, FieldMeta } from '../data/domain'

const props = defineProps<{
  field: Pick<FieldMeta, 'field_id' | 'label' | 'shape' | 'axes' | 'unit_label' | 'extent'> & { result?: Pick<FieldMeta['result'], 'config_id'> }
  values?: number[]
  /** Alias kept for the README-fixed `array` prop; same meaning as `values`. */
  array?: FieldData
}>()

const canvas = ref<HTMLCanvasElement | null>(null)

function resolveValues(): number[] | undefined {
  if (props.values) return props.values
  if (props.array) return props.array.values
  return undefined
}

function draw() {
  const el = canvas.value
  const values = resolveValues()
  if (!el || !values) return
  const ctx = el.getContext('2d')
  if (!ctx) return

  if (props.field.shape.length === 1) {
    // A recorded front is a row profile [y], not a synthetic 2D indicator.
    el.width = 400
    el.height = 200
    ctx.clearRect(0, 0, el.width, el.height)
    const min = props.field.extent.x[0]
    const span = props.field.extent.x[1] - min
    ctx.fillStyle = '#1a4f8a'
    values.forEach((value, row) => ctx.fillRect((value - min) / span * 398, row / (values.length - 1) * 198, 2, 2))
    return
  }
  const [ny, nx] = props.field.shape
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
    const v = values[i]
    const norm = (v - min) / span
    const [r, g, b] = colormap(norm)
    const o = i * 4
    img.data[o] = r
    img.data[o + 1] = g
    img.data[o + 2] = b
    img.data[o + 3] = 255
  }
  // Draw directly with no resampling: the canvas is nx × ny.
  ctx.putImageData(img, 0, 0)
}

/** Simple perceptually-reasonable blue→white→red ramp (no smoothing of data). */
function colormap(t: number): [number, number, number] {
  const c = Math.max(0, Math.min(1, t))
  if (c < 0.5) {
    const k = c / 0.5
    return [Math.round(30 + k * 225), Math.round(60 + k * 195), Math.round(160 + k * 95)]
  }
  const k = (c - 0.5) / 0.5
  return [Math.round(255), Math.round(255 - k * 205), Math.round(255 - k * 235)]
}

onMounted(draw)
watch(() => [props.field.field_id, props.field.result?.config_id, resolveValues()], draw)
</script>

<template>
  <figure class="sv">
    <figcaption class="sv__caption">
      <span class="sv__title">{{ zh(field.label) }}</span>
      <span class="sv__unit">({{ zh(field.unit_label) }})</span>
    </figcaption>
    <canvas ref="canvas" class="sv__canvas" data-testid="snapshot-canvas" :aria-label="`${zh(field.label)}场 · 仅已记录数值`"></canvas>
    <p class="sv__meta">
      {{ zh("Shape") }} {{ zh(field.shape.join(' × ')) }} {{ zh("· axes") }} {{ zh(field.axes.join(',')) }} {{ zh("· rendered from recorded values only (no interpolation)") }}
    </p>
  </figure>
</template>

<style scoped>
.sv { margin: 0; }
.sv__caption { font-size: 0.9rem; font-weight: 600; }
.sv__unit { font-weight: 400; color: #666; }
.sv__canvas { width: 100%; max-width: 40rem; image-rendering: pixelated; border: 1px solid #ccc; background: #fafafa; }
.sv__meta { font-size: 0.75rem; color: #777; }
</style>
