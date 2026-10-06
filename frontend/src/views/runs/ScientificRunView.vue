<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SnapshotViewer from '../../scientific/SnapshotViewer.vue'
import FaceAllocationView from '../../scientific/FaceAllocationView.vue'
import EntropyChart from '../../scientific/EntropyChart.vue'
import MetricsPanel from '../../scientific/MetricsPanel.vue'
import RunAIView from './RunAIView.vue'
import type { AIView } from '../../data/v2/ai'
import type { AllocationArrayView, MetricCollectionView } from '../../data/domain'
import { loadScientificResult, loadSnapshots, loadRunField, loadRunFaces, loadViewContext, type FieldName, type Region } from '../../data/v2/runs'

const props = defineProps<{ runId: string }>()
const route = useRoute(), router = useRouter()
const result = ref<Awaited<ReturnType<typeof loadScientificResult>>>()
const snapshots = ref<Awaited<ReturnType<typeof loadSnapshots>>>([])
const field = ref<Awaited<ReturnType<typeof loadRunField>>>()
const faces = ref<Awaited<ReturnType<typeof loadRunFaces>>>([])
const context = ref<Awaited<ReturnType<typeof loadViewContext>>>()
const error = ref(''), loading = ref(false), playing = ref(false)
const channel = ref<'bg' | 'aa' | 'at'>('at')
const regionEnabled = ref(false)
const region = ref<Region>({ x_min: 0, x_max: 1, y_min: 0, y_max: 1 })
let session = 0, selection = 0
let timer: ReturnType<typeof setTimeout> | undefined
const selectedName = computed(() => result.value?.fields.find(f => f.field_id === route.query.field)?.field_id ?? 'density')
const selectedIndex = computed(() => {
  const index = snapshots.value.findIndex(s => s.snapshot_id === route.query.snapshot)
  return index < 0 ? snapshots.value.length - 1 : index
})
const snapshot = computed(() => snapshots.value[selectedIndex.value])
const aiView = computed<AIView | undefined>(() => context.value ? {
  snapshot_id: context.value.snapshot_id, field: context.value.field,
  x_min: context.value.region?.x_min ?? null, x_max: context.value.region?.x_max ?? null,
  y_min: context.value.region?.y_min ?? null, y_max: context.value.region?.y_max ?? null,
} : undefined)
const fieldMeta = computed(() => field.value ? {
  field_id: `${props.runId}:${field.value.snapshot_id}:${field.value.field_id}`, label: field.value.label,
  unit_label: field.value.unit, shape: field.value.shape, axes: field.value.axes,
  extent: { x: field.value.extent_x as [number, number], y: field.value.extent_y as [number, number] },
} : null)
const entropy = computed(() => ({ total_point_count: result.value?.entropy.rows.length ?? 0,
  series: ['bg', 'aa', 'at'].map(c => ({ series_id: `run.E_${c}`, label: `E_${c}`,
    points: (result.value?.entropy.rows ?? []).map((row, i) => ({ step_index: i + 1, physical_time: row.time_end!, value: row[`E_${c}`]! })) })),
}))
const metrics = computed<MetricCollectionView>(() => ({ experiment_id: props.runId, config_id: result.value?.identity.config_hash ?? '',
  items: (result.value?.metrics ?? []).map(m => ({ metric_id: m.metric_id, display_label: m.label, definition_id: m.metric_id,
    value: m.value, unit: { id: m.unit, quantity: m.metric_id, label: m.unit, system: m.unit === 'dimensionless' ? 'DIMENSIONLESS' : 'MODEL', si_mapping: null }, definition_text: m.definition,
    detector_scope: `${m.detector}; ${m.window}; ${m.normalization}; ${m.applicable_conditions}`,
    time_scope_label: `终态 t=${m.time}`, resolution_limit: m.resolution_limit, evidence_refs: [m.evidence_id],
    availability: m.availability === 'AVAILABLE' ? 'AVAILABLE' : 'MISSING', unavailable_reason: m.reason })),
}))
function asFace(a: (typeof faces.value)[number]): AllocationArrayView {
  return { ...a, unit_label: a.unit }
}
const instant = computed(() => faces.value.filter(a => a.channel === channel.value))
const cumulative = computed(() => result.value?.allocation.arrays?.filter(a => a.channel === channel.value) ?? [])
function pause() { playing.value = false; clearTimeout(timer) }
async function choose(index: number, name = selectedName.value) {
  const s = snapshots.value[index]
  if (!s) return
  await router.replace({ query: { ...route.query, snapshot: s.snapshot_id, field: name } })
}
async function updateSelection() {
  const s = snapshot.value
  if (!s) return
  const current = ++selection, currentSession = session
  field.value = undefined; faces.value = []; context.value = undefined; loading.value = true; error.value = ''
  try {
    const chosenRegion = route.query.region ? JSON.parse(String(route.query.region)) as Region : undefined
    const [f, a, c] = await Promise.allSettled([loadRunField(props.runId, s.snapshot_id, selectedName.value),
      loadRunFaces(props.runId, s.snapshot_id), loadViewContext(props.runId, s.snapshot_id, selectedName.value, chosenRegion)])
    if (current !== selection || currentSession !== session) return
    if (f.status === 'fulfilled') field.value = f.value
    if (a.status === 'fulfilled') faces.value = a.value
    if (c.status === 'fulfilled') context.value = c.value
    const failures = [f, a, c].filter(value => value.status === 'rejected')
    if (failures.length) { error.value = failures.map(value => value.reason instanceof Error ? value.reason.message : '结果加载失败。').join(' '); pause() }
  } catch (e) { if (current === selection && currentSession === session) { error.value = e instanceof Error ? e.message : '结果加载失败。'; pause() } }
  finally { if (current === selection && currentSession === session) loading.value = false }
}
async function initialize() {
  const current = ++session; ++selection; pause(); result.value = undefined; field.value = undefined; snapshots.value = []; error.value = ''
  try {
    const [r, s] = await Promise.all([loadScientificResult(props.runId), loadSnapshots(props.runId)])
    if (current !== session) return
    result.value = r; snapshots.value = s
    if (route.query.region) { region.value = JSON.parse(String(route.query.region)); regionEnabled.value = true }
    else { regionEnabled.value = false }
    await updateSelection()
  } catch (e) { if (current === session) error.value = e instanceof Error ? e.message : '结果加载失败。' }
}
async function applyRegion() {
  pause()
  await router.replace({ query: { ...route.query, region: regionEnabled.value ? JSON.stringify(region.value) : undefined } })
}
async function playNext() {
  if (!playing.value) return
  if (loading.value) { timer = setTimeout(playNext, 250); return }
  if (selectedIndex.value >= snapshots.value.length - 1) { pause(); return }
  await choose(selectedIndex.value + 1)
  if (playing.value) timer = setTimeout(playNext, 1000)
}
async function togglePlay() {
  if (playing.value) { pause(); return }
  if (selectedIndex.value >= snapshots.value.length - 1) await choose(0)
  playing.value = true; timer = setTimeout(playNext, 1000)
}
watch(() => props.runId, initialize, { immediate: true })
watch(() => [route.query.snapshot, route.query.field, route.query.region], updateSelection)
onUnmounted(() => { ++session; ++selection; pause() })
</script>

<template>
  <section class="science" data-testid="scientific-result">
    <p v-if="error" role="alert" data-testid="scientific-error">{{ error }} <button @click="initialize">重试结果</button></p>
    <p v-if="!result && !error" role="status">正在加载科学结果…</p>
    <div v-if="result" class="science-layout"><div class="science-main">
      <div class="panel"><h2>本次科学结果</h2>
        <RouterLink :to="`/runs/${runId}/evidence`" data-testid="run-evidence-link">查看本次运行证据</RouterLink>
        <p>本次新建 V2 计算 · {{ result.identity.verification }} · 未继承历史冻结状态</p>
        <p class="hash">结果 SHA-256：{{ result.result_hash }}</p>
      </div>
      <section class="panel" data-testid="final-density"><h2>真实流场快照</h2>
        <div class="controls"><label>变量 <select aria-label="科学变量" :value="selectedName" @change="pause(); choose(selectedIndex, ($event.target as HTMLSelectElement).value as FieldName)">
          <option v-for="f in result.fields" :key="f.field_id" :value="f.field_id">{{ f.label }}</option></select></label>
          <label>快照 <select aria-label="真实快照" :value="selectedIndex" @change="pause(); choose(Number(($event.target as HTMLSelectElement).value))">
            <option v-for="(s, i) in snapshots" :key="s.snapshot_id" :value="i">step={{ s.step }} · t={{ s.time.toPrecision(6) }}</option></select></label>
          <button :disabled="selectedIndex <= 0" @click="pause(); choose(selectedIndex - 1)">上一帧</button>
          <button :disabled="selectedIndex >= snapshots.length - 1" @click="pause(); choose(selectedIndex + 1)">下一帧</button>
          <button :disabled="snapshots.length < 2" @click="togglePlay">{{ playing ? '暂停' : '播放' }}</button>
        </div>
        <p v-if="loading" role="status">正在加载所选真实快照…</p>
        <template v-if="field && fieldMeta"><SnapshotViewer :field="fieldMeta" :values="field.values" />
          <p data-testid="snapshot-time">step={{ snapshot?.step }} · t={{ field.time }} · {{ field.shape.join(' × ') }} · {{ field.unit }}</p>
          <p>范围 {{ field.minimum.toPrecision(6) }}–{{ field.maximum.toPrecision(6) }}；色标按当前帧范围。</p>
          <p class="hint">{{ field.definition }}</p><p class="hash">快照 SHA-256：{{ field.source_sha256 }}</p>
        </template>
        <p class="hint">只播放已保存的真实帧，不生成中间帧；变量和快照选择保存在当前链接。</p>
      </section>
      <section class="panel"><h2>区域统计</h2>
        <label><input v-model="regionEnabled" type="checkbox" />选择矩形区域</label>
        <form class="controls" @submit.prevent="applyRegion">
          <template v-if="regionEnabled"><label v-for="key in (['x_min', 'x_max', 'y_min', 'y_max'] as const)" :key="key">{{ key }} <input v-model.number="region[key]" :aria-label="key" type="number" step="any" required /></label></template>
          <button type="submit">应用区域</button>
        </form>
        <p v-if="context" data-testid="region-statistics">{{ context.availability === 'AVAILABLE' ? `${context.selected_count} 个真实 cell center · 最小 ${context.minimum} · 最大 ${context.maximum} · 均值 ${context.mean}（${context.unit}）` : context.reason }}</p>
        <p class="hint">边界内的 cell center（含边界）直接统计；不插值、不按矩形面积加权。</p>
      </section>
      <section class="panel"><h2>全轨迹累计标量熵 E</h2><EntropyChart :history="entropy" :selectable="false" />
        <p>{{ result.entropy.cumulative_rule }} · RK 权重 {{ result.entropy.rk_weights.join(', ') }}</p>
        <p>{{ result.entropy.face_measure_rule }} · {{ result.entropy.spatial_scope }}</p>
      </section>
      <section class="panel"><h2>终态宏观指标</h2><MetricsPanel :collection="metrics" /></section>
      <section class="panel"><h2>原生 face 诊断</h2><label>熵通道 <select v-model="channel" aria-label="熵通道"><option value="bg">bg</option><option value="aa">aa</option><option value="at">at</option></select></label>
        <h3>瞬时 Pi（所选快照）</h3><div class="faces"><div v-for="a in instant" :key="a.array_id"><FaceAllocationView :array="asFace(a)" /><p class="hint">t={{ a.time_end }} · {{ a.unit }} · face measure={{ a.face_measure }}</p></div></div>
        <h3>累计空间分配（完整运行区间）</h3>
        <p v-if="result.allocation.availability === 'UNAVAILABLE'" data-testid="allocation-unavailable">{{ result.allocation.reason }}</p>
        <div v-else class="faces"><div v-for="a in cumulative" :key="a.array_id"><FaceAllocationView :array="asFace(a)" /><p class="hint">t={{ a.time_start }}–{{ a.time_end }} · {{ a.unit }} · face measure={{ a.face_measure }}</p></div></div>
        <p class="hint">{{ result.allocation.definition }}</p><p v-if="result.allocation.scalar_totals">空间积分：{{ result.allocation.scalar_totals }} · 与标量 E 最大绝对误差 {{ result.allocation.max_scalar_abs_error }}</p>
      </section>
      <section class="panel"><h2>适用范围与局限</h2><ul><li v-for="item in result.limitations" :key="item">{{ item }}</li></ul></section>
    </div><RunAIView :run-id="runId" :view="aiView" /></div>
  </section>
</template>

<style scoped>
.science-main { min-width: 0; }@media(min-width:1200px) { .science-layout { display: grid; grid-template-columns: minmax(0, 1fr) 22rem; gap: 1rem; } }
.panel { padding: 1.5rem; border: 1px solid #dce4eb; border-radius: 8px; margin: 1rem 0; min-width: 0; }h2 { font-size: 1.1rem; }h3 { font-size: 1rem; }p,li { line-height: 1.7; }
.hash { overflow-wrap: anywhere; font-size: .8rem; }.hint { color: #617184; font-size: .8rem; }.controls { display: flex; flex-wrap: wrap; gap: .6rem; margin: .8rem 0; align-items: center; }p,li { overflow-wrap: anywhere; }
:deep(.mp__head) { flex-wrap: wrap; }:deep(.mp__meta) { grid-template-columns: 9rem minmax(0, 1fr); }:deep(.mp__meta dd) { overflow-wrap: anywhere; }
button,select,input { font: inherit; max-width: 100%; border: 1px solid #bdccda; border-radius: 5px; background: white; padding: .45rem; }input[type=number] { width: 6rem; }button:disabled { opacity: .5; }.faces { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }a { color: #214f75; }
@media(max-width:780px) { .panel { padding: 1rem; }.faces { grid-template-columns: 1fr; }:deep(.mp__meta) { grid-template-columns: 1fr; } }
</style>
