<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { api } from '../services/api'
import type { components } from '../types/generated/api'
import { factText } from '../data/evidence'
import { zh, tabLabels } from '../presentation/zh-CN'
const props = defineProps<{ experimentId: string }>()
const metadata = ref<components['schemas']['Experiment']>()
const error = ref('')
const protocol = computed(() => metadata.value?.available_configs[0]?.protocol)
let abort: AbortController | undefined
watch(() => props.experimentId, async id => {
  abort?.abort(); const request = new AbortController(); abort = request
  metadata.value = undefined; error.value = ''
  try {
    const response = await api.GET('/api/v1/experiments/{experiment_id}', { params: { path: { experiment_id: id } }, signal: request.signal })
    if (request.signal.aborted) return
    if (response.data && 'data' in response.data) metadata.value = response.data.data
    else error.value = response.error?.error.message ?? '算例信息暂不可用。'
  } catch (e) { if (!request.signal.aborted) error.value = e instanceof Error ? e.message : '算例信息暂不可用。' }
}, { immediate: true })
onUnmounted(() => abort?.abort())
</script>
<template>
  <section class="case-info" data-testid="historical-case-info">
    <details class="sp-panel"><summary><span class="sp-badge sp-badge--history">历史数据回放</span> 算例信息与运行能力</summary>
      <p v-if="error" role="alert">{{ zh(error) }}</p><p v-else-if="!metadata" role="status">正在加载算例信息…</p>
      <dl v-else class="sp-kv">
        <dt>算例名称</dt><dd>{{ zh(metadata.name) }}</dd><dt>问题简介</dt><dd>{{ zh(metadata.description) }}</dd>
        <dt>物理模型</dt><dd>{{ zh(metadata.scientific_family) }}<template v-if="protocol"> · {{ factText(protocol.boundary_scope) }}</template></dd>
        <dt>网格和方法</dt><dd v-if="protocol"><span v-if="protocol.grid.state === 'KNOWN'">{{ protocol.grid.value.dimensions.map(d => `${d.axis}=${d.size}`).join(' × ') }}</span><span v-else>{{ factText(protocol.grid) }}</span> · {{ factText(protocol.method_name) }} · {{ factText(protocol.reconstruction) }} · {{ factText(protocol.integrator) }}</dd><dd v-else>元数据未记录，请在对应证据中核查。</dd>
        <dt>支持的参数</dt><dd>仅切换已有配置：{{ metadata.available_configs.map(c => c.id).join('、') || '未登记' }}。<details v-for="config in metadata.available_configs" :key="config.id"><summary>{{ config.id }} 参数记录</summary><ul><li v-for="parameter in config.parameters" :key="parameter.name">{{ parameter.name }}：{{ factText(parameter.value) }}</li></ul></details></dd>
        <dt>可用结果</dt><dd>{{ metadata.capabilities.filter(c => c.tab_policy.visible_for_family).map(c => tabLabels[c.tab_policy.tab_id] ?? c.tab_policy.tab_id).join('、') }}；实际可用性按配置与科学资产分别核查。</dd>
        <dt>数据来源类型</dt><dd>历史科研数据回放，各结果保留自己的来源和验证状态。</dd>
        <dt>当前运行能力</dt><dd>本页只读回放，不执行实时计算。<RouterLink v-if="experimentId === 'case8'" to="/experiments/new">Case 8 新计算请进入创建页并核查服务状态 →</RouterLink><span v-else>该算例尚未开放实时求解。</span></dd>
      </dl>
    </details>
  </section>
</template>
<style scoped>
.case-info { max-width: var(--sp-page-width); margin: 24px auto 0; padding-inline: var(--sp-page-gutter); }
summary { cursor: pointer; color: var(--sp-primary); font-size: 14px; }.sp-badge { margin-right: 8px; }dd details { margin-top: 8px; }ul { padding-left: 20px; }
</style>
