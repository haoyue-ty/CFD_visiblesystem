<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { compareRuns, type Comparison } from '../data/v2/comparison'
import { loadRuns, type RunRecord, type FieldName } from '../data/v2/runs'
import ComparisonField from '../views/runs/ComparisonField.vue'
import EntropyChart from '../scientific/EntropyChart.vue'
const route = useRoute()
const runs = ref<RunRecord[]>([]), a = ref(String(route.query.a ?? '')), b = ref(String(route.query.b ?? ''))
const field = ref<FieldName>('density'), time = ref(''), result = ref<Comparison>(), error = ref(''), busy = ref(false)
const offset = ref(0), total = ref(0)
let generation = 0
watch([a, b], () => { generation++; result.value = undefined; time.value = '' })
onUnmounted(() => { generation++ })
const entropy = computed(() => ({ total_point_count: Math.max(result.value?.a.entropy.rows.length ?? 0, result.value?.b.entropy.rows.length ?? 0),
  series: result.value ? ['a','b'].flatMap(side => ['bg','aa','at'].map(channel => ({ series_id: `${side}.E_${channel}`, label: `${side.toUpperCase()} E_${channel}`,
    points: result.value![side as 'a' | 'b'].entropy.rows.map((row, i) => ({ step_index: i+1, physical_time: row.time_end!, value: row[`E_${channel}`]! })) }))) : [] }))
async function more() {
  try { const list = await loadRuns(offset.value, 'COMPLETED'); runs.value.push(...list.runs); offset.value += list.runs.length; total.value = list.total }
  catch (e) { error.value = e instanceof Error ? e.message : '加载失败' }
}
async function compare(reset = false) {
  const current = ++generation
  busy.value = true; error.value = ''; if (reset) { time.value = ''; result.value = undefined }
  try { const response = await compareRuns({ run_a: a.value, run_b: b.value, field: field.value, snapshot_time: time.value === '' ? null : Number(time.value) }); if (current === generation) result.value = response }
  catch (e) { if (current === generation) { result.value = undefined; error.value = e instanceof Error ? e.message : '比较失败' } }
  finally { busy.value = false }
}
onMounted(async () => { await more(); if (a.value && b.value) await compare(true) })
</script>
<template>
  <main class="p7" data-page="run-comparison"><p class="eyebrow">SHOCKPATH · RUN A/B</p><h1>运行对比</h1>
    <p>先核查实验条件，再并列观察同一变量、同一真实时间。系数差异是比较因素。</p>
    <RouterLink to="/workspace">返回工作台</RouterLink>
    <form @submit.prevent="compare(true)"><label v-for="side in ['A', 'B']" :key="side">Run {{ side }}
      <input :disabled="busy" :value="side === 'A' ? a : b" @input="side === 'A' ? a = ($event.target as HTMLInputElement).value : b = ($event.target as HTMLInputElement).value" list="completed-runs" :aria-label="`Run ${side}`" required placeholder="选择或粘贴 Run ID" /></label>
      <datalist id="completed-runs"><option v-for="run in runs" :key="run.run_id" :value="run.run_id">q_aa={{ run.experiment.normalized_config.method.q_aa }} q_at={{ run.experiment.normalized_config.method.q_at }}</option></datalist>
      <button :disabled="busy">核查并对比</button><button type="button" v-if="offset < total" @click="more">加载更多运行</button></form>
    <p v-if="busy" role="status">核查来源和结果…</p><p v-if="error" role="alert">{{ error }}</p>
    <section v-if="result"><h2 data-testid="comparison-conditions">{{ result.same_conditions ? '同条件比较' : '非同条件比较' }}</h2>
      <p v-if="!result.same_conditions">实验条件或科学定义存在差异；仅并列观察，指标差值不可用。</p>
      <div class="table"><table><thead><tr><th>协议差异</th><th>A</th><th>B</th><th>影响条件</th></tr></thead><tbody>
        <tr v-for="diff in result.differences" :key="diff.field"><th>{{ diff.field }}</th><td>{{ diff.a }}</td><td>{{ diff.b }}</td><td>{{ diff.affects_conditions ? '是' : '否' }}</td></tr>
        <tr v-if="!result.differences.length"><td colspan="4">协议一致</td></tr></tbody></table></div>
      <div class="toolbar"><label>变量 <select :disabled="busy" v-model="field" aria-label="对比变量" @change="compare()">
        <option value="density">密度</option><option value="pressure">压力</option><option value="mach">Mach</option><option value="velocity_x">x 速度</option><option value="velocity_y">y 速度</option><option value="speed">速度大小</option></select></label>
        <label>共同快照时间 <select :disabled="busy" v-model="time" aria-label="共同快照时间" @change="compare()"><option value="">最后共同时间</option><option v-for="t in result.common_snapshot_times" :key="t" :value="String(t)">{{ t }}</option></select></label></div>
      <p v-if="result.field_reason">{{ result.field_reason }}</p>
      <p v-else data-testid="comparison-color">统一色标：{{ result.color_min }} → {{ result.color_max }} · t={{ result.snapshot_time }}</p>
      <div v-if="!result.field_reason" class="color-scale" aria-label="共同色标由蓝色低值到红色高值"></div>
      <div v-if="result.field_a && result.field_b && result.color_min !== null && result.color_max !== null" class="fields">
        <div><h3>A <RouterLink :to="'/runs/'+a">运行详情</RouterLink></h3><ComparisonField :field="result.field_a" :minimum="result.color_min" :maximum="result.color_max" /></div>
        <div><h3>B <RouterLink :to="'/runs/'+b">运行详情</RouterLink></h3><ComparisonField :field="result.field_b" :minimum="result.color_min" :maximum="result.color_max" /></div></div>
      <h2>终态宏观指标</h2><p>A：t={{ result.a.runtime.final_time }}；B：t={{ result.b.runtime.final_time }}。切换流场快照不会改变终态指标。</p>
      <div class="table"><table><thead><tr><th>指标 / 定义</th><th>A</th><th>B</th><th>B − A</th></tr></thead><tbody><tr v-for="m in result.metrics" :key="m.metric_id">
        <th>{{ m.label }} · {{ m.unit }}<small>{{ m.definition }}</small></th><td>{{ m.a ?? '不可用' }}</td><td>{{ m.b ?? '不可用' }}</td><td>{{ m.b_minus_a ?? m.reason }}</td></tr></tbody></table></div>
      <h2>全域累计熵预算</h2><p>各自真实接受步的 E_bg / E_aa / E_at；横轴为模型时间，纵轴为 {{ result.a.entropy.unit }}。非同条件时仅供并列观察。</p>
      <EntropyChart :history="entropy" :selectable="false" physical-time />
      <p v-for="note in result.limitations" :key="note" class="hint">{{ note }}</p>
    </section>
  </main>
</template>
<style scoped src="../views/runs/p7.css"></style>
