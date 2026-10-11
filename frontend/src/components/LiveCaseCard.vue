<script setup lang="ts">
import { computed, ref } from 'vue'
import type { LiveCase } from '../data/v2/experiments'
const props = defineProps<{ liveCase: LiveCase }>()
const selected = ref(props.liveCase.templates[0]?.template_id ?? '')
const template = computed(() => props.liveCase.templates.find(t => t.template_id === selected.value) ?? props.liveCase.templates[0])
const parameters = computed(() => props.liveCase.capabilities.filter(c => c.scope === 'INPUT' && c.support === 'CANDIDATE'))
</script>
<template>
  <article class="sp-panel live-case" :data-testid="`live-case-${liveCase.case_id}`">
    <div class="sp-section-heading"><h3>{{ liveCase.label }}</h3><span class="sp-badge">实时求解</span></div>
    <p class="sp-muted">为强激波横向扰动创建独立运行，观察流场演化与熵耗散路径。结果由本次真实 Solver 输出。</p>
    <details data-testid="live-case-description"><summary>算例说明与支持参数</summary>
      <dl v-if="template" class="sp-kv">
        <dt>物理模型</dt><dd>可压缩 Euler · Mach={{ template.config.physics.mach }} · γ={{ template.config.physics.gamma }}</dd>
        <dt>网格</dt><dd>{{ liveCase.grid_pairs.map(pair => pair.join(' × ')).join(' / ') }}</dd>
        <dt>数值方法</dt><dd>{{ template.config.method.method_id }} · 一阶有限体积 · SSP-RK3</dd>
        <dt>支持的参数</dt><dd><ul><li v-for="parameter in parameters" :key="parameter.field_path">{{ parameter.label }}：{{ parameter.candidate_values.join(' / ') }}</li></ul></dd>
        <dt>可用结果</dt><dd>{{ liveCase.capabilities.filter(c => c.scope === 'OUTPUT').map(c => c.label).join('、') }}，以及本次运行证据与 HTML 报告。</dd>
        <dt>数据来源</dt><dd>本次 V2 实时计算，每次主动求解生成独立 Run。</dd>
        <dt>运行能力</dt><dd>{{ liveCase.execution_available ? '后端已开放真实求解' : '运行服务未启动' }}</dd>
      </dl>
      <ul class="sp-muted"><li v-for="note in liveCase.limitations" :key="note">{{ note }}</li></ul>
    </details>
    <label class="live-case__template">起始模板<select v-model="selected" aria-label="实时算例模板"><option v-for="item in liveCase.templates" :key="item.template_id" :value="item.template_id">{{ item.label }}</option></select></label>
    <RouterLink v-if="template && liveCase.execution_available" :to="{ path: '/experiments/new', query: { template: template.template_id } }" class="sp-button sp-button--primary">进入新建计算 →</RouterLink>
    <p class="sp-muted">选择模板不会启动计算；进入创建页后仍需验证、确认并主动启动求解。</p>
  </article>
</template>
<style scoped>
h3 { margin: 0; }.live-case details { margin: 16px 0; }summary { color: var(--sp-primary); cursor: pointer; }
.live-case__template { display: grid; gap: 8px; margin: 20px 0 16px; max-width: 480px; font-size: 14px; }select { padding: 10px; border: 1px solid var(--sp-border); border-radius: 12px; background: white; width: 100%; }
ul { margin: 0; padding-left: 18px; }
</style>
