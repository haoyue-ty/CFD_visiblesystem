<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createRun } from '../data/v2/runs'
import { ExperimentApiError, loadCases, parseNaturalLanguage, validateConfig,
  type Draft, type LiveCase, type LiveConfig, type Submission, type Validated } from '../data/v2/experiments'

type Mode = 'template' | 'form' | 'natural_language'
const mode = ref<Mode>('template')
const registry = ref<LiveCase | null>(null)
const aiAvailable = ref(false)
const config = ref<LiveConfig | null>(null)
const templateId = ref<string | null>(null)
const text = ref('')
const draft = ref<Draft | null>(null)
const validated = ref<Validated | null>(null)
const error = ref<ExperimentApiError | null>(null)
const loading = ref(true)
const busy = ref(false)
const accepted = ref(false)
const confirmed = ref(false)
const router = useRouter()
let revision = 0
const labels = { LIVE_FAST_RUN: '普通配置', LIVE_PAPER_PROFILE: '论文标准配置的新运行',
  PAPER_SCALE_CUSTOM: '论文模板 · 自定义参数', CUSTOM_RUN: '自定义实验' }
const fieldLabels: Record<string, string> = { 'grid.nx': 'Nx', 'grid.ny': 'Ny', 'time.cfl': 'CFL',
  'time.final_time': '终止时间 T', 'method.q_aa': 'q_aa', 'method.q_at': 'q_at' }
const editable = computed(() => registry.value?.capabilities.filter(c => c.scope === 'INPUT' && c.support === 'CANDIDATE') ?? [])
const selectedTemplate = computed(() => registry.value?.templates.find(t => t.template_id === templateId.value))

function invalidate() {
  revision++
  validated.value = null
  accepted.value = confirmed.value = false
  error.value = null
}
watch([config, mode, text, templateId], invalidate, { deep: true, flush: 'sync' })

function selectTemplate(id: string) {
  const template = registry.value?.templates.find(t => t.template_id === id)
  if (!template) return
  templateId.value = id
  config.value = JSON.parse(JSON.stringify(template.config)) as LiveConfig
  draft.value = null
}

function readField(path: string): number {
  const [group, key] = path.split('.') as [keyof LiveConfig, string]
  return (config.value?.[group] as Record<string, number> | undefined)?.[key] ?? 0
}
function setField(path: string, event: Event) {
  if (!config.value) return
  const [group, key] = path.split('.') as [keyof LiveConfig, string]
  const values = config.value[group] as unknown as Record<string, number>
  values[key] = Number((event.target as HTMLSelectElement).value)
  draft.value = null
}
function setGrid(event: Event) {
  if (!config.value) return
  const [nx, ny] = (event.target as HTMLSelectElement).value.split('x').map(Number)
  config.value.grid.nx = nx!
  config.value.grid.ny = ny!
  draft.value = null
}
function useCustom() {
  templateId.value = null
  if (config.value) config.value.profile = 'custom'
  draft.value = null
}
function submission(): Submission {
  return { input_mode: mode.value, template_id: templateId.value, capability_revision: registry.value!.capability_revision,
    natural_language_text: mode.value === 'natural_language' ? draft.value?.source_text ?? null : null,
    parser_version: mode.value === 'natural_language' ? draft.value?.parser_version ?? null : null }
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const result = await loadCases()
    registry.value = result.cases[0] ?? null
    aiAvailable.value = result.natural_language_available
    if (!registry.value) throw new ExperimentApiError('当前没有可创建的实验。')
    selectTemplate(registry.value.templates[0]!.template_id)
  } catch (e) { error.value = e as ExperimentApiError }
  finally { loading.value = false }
}

async function check(confirm = false) {
  if (!config.value || !registry.value || busy.value) return
  const current = revision
  const candidate = structuredClone(JSON.parse(JSON.stringify(config.value))) as LiveConfig
  const meta = submission()
  busy.value = true
  error.value = null
  try {
    const result = await validateConfig(candidate, meta)
    if (revision !== current) return
    validated.value = result
    confirmed.value = confirm
  } catch (e) { if (revision === current) error.value = e as ExperimentApiError }
  finally { busy.value = false }
}

async function parse() {
  if (!registry.value || busy.value || !text.value.trim()) return
  invalidate()
  draft.value = null
  const current = revision
  busy.value = true
  try {
    const result = await parseNaturalLanguage(text.value, registry.value.capability_revision)
    if (revision !== current) return
    // Set reactive inputs first: invalidation must not erase the new validation.
    config.value = result.config ? structuredClone(result.config) : null
    templateId.value = result.template_id
    draft.value = result
    validated.value = result.validated
  } catch (e) { if (revision === current) error.value = e as ExperimentApiError }
  finally { busy.value = false }
}

async function submit() {
  if (!confirmed.value || !validated.value || busy.value) return
  busy.value = true
  error.value = null
  const numerical = validated.value.normalized_config
  const meta = submission()
  const hash = validated.value.config_hash
  const fingerprint = JSON.stringify({ config: numerical, submission: meta, hash })
  const saved = sessionStorage.getItem('shockpath.pendingRun')
  let pending: { fingerprint: string; key: string } | null = null
  try { pending = saved ? JSON.parse(saved) : null } catch { /* stale local record */ }
  const key = pending?.fingerprint === fingerprint ? pending.key : crypto.randomUUID()
  sessionStorage.setItem('shockpath.pendingRun', JSON.stringify({ fingerprint, key }))
  try {
    const record = await createRun(numerical, meta, hash, key)
    sessionStorage.removeItem('shockpath.pendingRun')
    await router.push('/runs/' + record.run_id)
  } catch (e) { error.value = e instanceof ExperimentApiError ? e : new ExperimentApiError('提交连接失败，可用同一提交标识重试。') }
  finally { busy.value = false }
}

onMounted(load)
</script>

<template>
  <main class="builder" data-page="experiment-builder">
    <header class="builder__header">
      <p class="eyebrow">SHOCKPATH · 新建实验</p>
      <h1>配置你的 Case 8 实验</h1>
      <p>从模板、专业参数或自然语言开始，核对同一份后端验证的实验配置。</p>
      <p v-if="registry?.execution_available" class="notice" data-testid="execution-ready">后台运行服务在线。核对并确认配置后，提交真实 CFD；任务串行执行。</p>
      <p v-else class="notice" data-testid="execution-unavailable">后台运行服务尚未启动。本页可验证与确认配置，尚未启动 CFD。</p>
    </header>

    <p v-if="loading" role="status">正在加载实验能力与模板…</p>
    <div v-if="error" role="alert" class="error" data-testid="builder-error">
      <p>{{ error.message }}</p>
      <ul v-if="error.details.length"><li v-for="item in error.details" :key="item.field">{{ item.field }}：{{ item.reason }}</li></ul>
      <button v-if="!registry" @click="load">重新加载</button>
    </div>

    <template v-if="registry && !loading">
      <div class="modes" role="group" aria-label="创建入口">
        <button v-for="(label, key) in { template: '模板创建', form: '专业参数', natural_language: '自然语言' }"
          :key="key" :aria-pressed="mode === key" :disabled="busy" @click="mode = key as Mode; draft = null">{{ label }}</button>
      </div>
      <div class="builder__layout">
        <section class="panel" aria-label="配置输入">
          <h2>{{ registry.label }}</h2>
          <template v-if="mode !== 'natural_language'">
            <label class="field">起始模板
              <select aria-label="起始模板" :value="templateId ?? ''" :disabled="busy" @change="selectTemplate(($event.target as HTMLSelectElement).value)">
                <option v-if="!templateId" value="" disabled>直接自定义</option>
                <option v-for="item in registry.templates" :key="item.template_id" :value="item.template_id">{{ item.label }}</option>
              </select>
            </label>
            <p v-if="selectedTemplate?.benchmark_status === 'PENDING'" class="hint">64×16、CFL=0.05、T=0.04 为 fast 候选；待 benchmark。</p>
            <p v-if="selectedTemplate?.benchmark_status === 'PASSED'" class="hint">64×16、CFL=0.05、T=0.04 已通过 P2 重复 benchmark；实际耗时取决于机器与负载。</p>
            <p v-if="mode === 'template'" class="hint">模板包含完整初始条件、边界、时间推进与快照策略。可切换到专业参数调整。</p>
          </template>

          <template v-if="mode === 'form' && config">
            <button class="text-button" :disabled="busy" @click="useCustom">使用直接自定义配置</button>
            <label class="field">网格 Nx × Ny
              <select aria-label="网格" :value="`${config.grid.nx}x${config.grid.ny}`" :disabled="busy" @change="setGrid">
                <option v-for="pair in registry.grid_pairs" :key="pair.join('x')" :value="pair.join('x')">{{ pair[0] }} × {{ pair[1] }}</option>
              </select>
            </label>
            <label v-for="field in editable.filter(c => !c.field_path.startsWith('grid.'))" :key="field.field_path" class="field">
              {{ field.label }}
              <select :aria-label="field.label" :value="readField(field.field_path)" :disabled="busy" @change="setField(field.field_path, $event)">
                <option v-for="value in field.candidate_values" :key="String(value)" :value="String(value)">{{ value }}</option>
              </select>
            </label>
            <p class="hint">CFL=0.05、Mach=6、γ=1.4 固定。可编辑值仅限已登记并通过 P2 核查的候选。</p>
          </template>

          <template v-if="mode === 'natural_language'">
            <label class="field">实验要求
              <textarea v-model="text" aria-label="实验要求" maxlength="4000" rows="6" :disabled="busy"
                placeholder="例如：使用 Case 8 的 D_u 论文模板，把 q_at 改为 0。" />
            </label>
            <p v-if="!aiAvailable" class="notice">自然语言服务未配置密钥。可以继续使用模板或专业参数。</p>
            <button :disabled="busy || !text.trim() || !aiAvailable" @click="parse">{{ busy ? '正在生成草稿…' : '生成配置草稿' }}</button>
            <div v-if="draft" data-testid="natural-language-draft" class="draft">
              <p>AI 草稿 · 请核对原文与数字</p>
              <ul v-if="draft.unresolved_fields.length || draft.unsupported_fields.length">
                <li v-for="issue in draft.unresolved_fields" :key="`u-${issue.field}`">待澄清 · {{ issue.field }}：{{ issue.reason }}</li>
                <li v-for="issue in draft.unsupported_fields" :key="`s-${issue.field}`">未支持 · {{ issue.field }}：{{ issue.reason }}</li>
              </ul>
              <p v-for="warning in draft.warnings" :key="warning" class="hint">{{ warning }}</p>
              <p v-if="!draft.ready_for_confirmation">请补充要求后重新生成草稿，或切换专业参数明确配置。</p>
            </div>
          </template>

          <details class="protocol">
            <summary>固定协议与能力限制</summary>
            <p>一阶有限体积 · SSP-RK3（stage guards）· 初态波速确定固定步长</p>
            <p>单位计算域 [0,1]²；x 下界 pre-shock inflow，上界 outflow，y 周期。</p>
            <p>前沿起伏幅值 0.0125、4 个波长；切向速度种子因子 0.01、宽度 0.04。两者具有不同物理含义。</p>
            <p>快照沿用 0、0.2、0.4、0.6、0.8、1 的源 checkpoint fractions，实际步数待求解器计算。</p>
            <ul><li v-for="cap in registry.capabilities.filter(c => c.scope === 'INPUT' && c.support === 'UNSUPPORTED')" :key="cap.field_path">{{ cap.label }}：{{ cap.reason }}</li></ul>
          </details>
          <button v-if="mode !== 'natural_language'" class="primary" :disabled="busy || !config" @click="check()">{{ busy ? '正在验证…' : '验证配置' }}</button>
        </section>

        <section class="panel summary" aria-label="配置摘要" data-testid="config-summary">
          <h2>配置摘要</h2>
          <p v-if="!validated" class="hint">完成输入并验证后，在这里核对归一化配置、协议差异与配置哈希。</p>
          <template v-if="validated">
            <p class="classification" data-testid="classification">{{ labels[validated.classification] }}</p>
            <p class="hint">{{ templateId ? `模板来源：${templateId}` : '直接自定义' }}</p>
            <dl>
              <dt>网格</dt><dd>{{ validated.normalized_config.grid.nx }} × {{ validated.normalized_config.grid.ny }}</dd>
              <dt>时间</dt><dd>CFL={{ validated.normalized_config.time.cfl }} · T={{ validated.normalized_config.time.final_time }}</dd>
              <dt>耗散参数</dt><dd>q_aa={{ validated.normalized_config.method.q_aa }} · q_at={{ validated.normalized_config.method.q_at }}</dd>
              <dt>物理</dt><dd>Mach={{ validated.normalized_config.physics.mach }} · γ={{ validated.normalized_config.physics.gamma }}</dd>
              <dt>方法</dt><dd>cross_mode_ec_unified_v1 · 一阶 · SSP-RK3</dd>
            </dl>
            <table v-if="validated.protocol_diff.length" data-testid="protocol-diff">
              <caption>相对起始模板的数值协议差异</caption>
              <thead><tr><th>字段</th><th>模板值</th><th>当前值</th></tr></thead>
              <tbody><tr v-for="diff in validated.protocol_diff" :key="diff.field"><td>{{ fieldLabels[diff.field] ?? diff.field }}</td><td>{{ diff.expected }}</td><td>{{ diff.actual }}</td></tr></tbody>
            </table>
            <ul class="hint"><li v-for="warning in validated.warnings" :key="warning">{{ warning }}</li></ul>
            <details><summary>完整归一化配置</summary><pre>{{ JSON.stringify(validated.normalized_config, null, 2) }}</pre></details>
            <p class="hash">配置 SHA-256 <code data-testid="config-hash">{{ validated.config_hash }}</code></p>
            <label class="confirm"><input v-model="accepted" type="checkbox" :disabled="busy || confirmed" />我已核对配置与协议差异，同意按该配置进行真实计算。</label>
            <button class="primary" :disabled="!accepted || busy || confirmed" @click="check(true)">确认配置</button>
            <p v-if="confirmed" role="status" data-testid="config-confirmed">配置已确认；尚未创建 Run。修改参数后需要重新验证与确认。</p>
          </template>
          <button class="primary run-disabled" :disabled="!confirmed || busy || !validated?.execution_available" aria-describedby="run-reason" @click="submit">{{ busy && confirmed ? '正在提交…' : '启动求解' }}</button>
          <p id="run-reason" class="hint">提交时后端再次验证。确认配置不会启动计算；每次主动运行生成独立记录。</p>
        </section>
      </div>
    </template>
  </main>
</template>

<style scoped>
.builder { max-width: 1180px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; color: #24384c; }
.builder__header { max-width: 790px; margin-bottom: 1.6rem; }
.eyebrow { font-size: .75rem; letter-spacing: .12em; color: #476e93; }
h1 { font-size: 2rem; margin: .6rem 0; } h2 { font-size: 1.15rem; margin: 0 0 1.4rem; }
p, li { line-height: 1.7; }.notice { padding: .75rem 1rem; background: #fff6dd; border-left: 3px solid #b38935; font-size: .9rem; }
.builder__layout { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; align-items: start; }
.panel { background: #fff; border: 1px solid #dce4eb; border-radius: 10px; padding: 1.5rem; min-width: 0; }
.modes { display: flex; gap: .6rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
button, select, textarea { font: inherit; } button { border: 1px solid #bdccda; border-radius: 5px; background: #fff; color: #254b6c; padding: .55rem .9rem; cursor: pointer; }
button[aria-pressed="true"], .primary { background: #214f75; color: #fff; border-color: #214f75; }button:disabled { opacity: .55; cursor: default; }
.field { display: flex; flex-direction: column; gap: .4rem; margin: 1rem 0; font-size: .9rem; }
select, textarea { padding: .7rem; border: 1px solid #bdccda; border-radius: 5px; background: #fff; color: #24384c; max-width: 100%; }textarea { resize: vertical; }
.hint { color: #617184; font-size: .85rem; }.text-button { font-size: .8rem; }.protocol { margin: 1.3rem 0; font-size: .85rem; }
summary { cursor: pointer; color: #315e83; } .classification { font-weight: 600; color: #214f75; } dl { display: grid; grid-template-columns: 5rem 1fr; gap: .7rem; font-size: .9rem; }dt { color: #617184; }dd { margin: 0; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; margin: 1.4rem 0; text-align: left; }th,td { padding: .5rem; border-bottom: 1px solid #dce4eb; }caption { text-align: left; margin-bottom: .6rem; color: #617184; }
.hash { font-size: .75rem; }code { display: block; overflow-wrap: anywhere; margin-top: .4rem; }pre { font-size: .75rem; overflow: auto; max-height: 340px; padding: .75rem; background: #f4f7fa; }
.confirm { display: flex; gap: .5rem; align-items: start; font-size: .85rem; margin: 1.2rem 0; line-height: 1.6; }.run-disabled { margin-top: 1.3rem; }.error { color: #842d2d; background: #fff1f1; padding: 1rem; margin-bottom: 1rem; }
@media (max-width: 780px) { .builder__layout { grid-template-columns: 1fr; }.builder { padding: 1.5rem 1rem; } h1 { font-size: 1.6rem; } }
</style>
