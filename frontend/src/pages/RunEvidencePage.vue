<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { loadRunEvidence } from '../data/v2/runs'
const route = useRoute()
const evidence = ref<Awaited<ReturnType<typeof loadRunEvidence>>>()
const error = ref('')
let generation = 0
async function load() {
  const current = ++generation; error.value = ''; evidence.value = undefined
  try { const value = await loadRunEvidence(String(route.params.runId)); if (current === generation) evidence.value = value }
  catch (e) { if (current === generation) error.value = e instanceof Error ? e.message : '运行证据加载失败。' }
}
watch(() => route.params.runId, load, { immediate: true })
</script>
<template>
  <main class="evidence" data-testid="run-evidence">
    <RouterLink :to="`/runs/${route.params.runId}`">← 本次科学结果</RouterLink><h1>本次运行证据</h1>
    <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <p v-else-if="!evidence" role="status">正在校验运行证据…</p>
    <template v-if="evidence">
      <section><h2>科学身份</h2><p>{{ evidence.evidence_id }}</p><p>来源：{{ evidence.identity.data_origin }} · {{ evidence.identity.verification }} · 未冻结</p>
        <p>分类：{{ evidence.identity.classification }}</p><p>配置 SHA-256：{{ evidence.identity.config_hash }}</p><p>结果 SHA-256：{{ evidence.result_hash }}</p>
      </section>
      <section><h2>验证范围</h2><ul><li v-for="s in evidence.supports" :key="s">{{ s }}</li></ul><h3>不支持的结论</h3><ul><li v-for="s in evidence.does_not_support" :key="s">{{ s }}</li></ul></section>
      <section><h2>输入与有效配置</h2><details><summary>归一化配置</summary><pre>{{ JSON.stringify(evidence.config, null, 2) }}</pre></details><details><summary>实际 Solver 配置</summary><pre>{{ JSON.stringify(evidence.effective_config, null, 2) }}</pre></details></section>
      <section><h2>方法、源码与后处理</h2>
        <p>{{ evidence.provenance.method_id }} · 方法 SHA-256：{{ evidence.provenance.method_sha256 }}</p>
        <p>依赖清单 {{ evidence.provenance.source_manifest_revision }} · {{ evidence.provenance.source_manifest_sha256 }}</p>
        <p>后处理 {{ evidence.provenance.postprocess_version }} · {{ evidence.provenance.postprocess_sha256 }}</p>
        <p>Solver 原始摘要：{{ evidence.provenance.solver_result_sha256 }}</p><p>有效配置：{{ evidence.provenance.effective_config_sha256 }}</p>
        <details><summary>科学源依赖</summary><table><tbody><tr v-for="a in evidence.provenance.dependencies" :key="a.path"><td>{{ a.path }}</td><td>{{ a.sha256 }}</td></tr></tbody></table></details>
        <details><summary>软件包装与后处理文件</summary><table><tbody><tr v-for="a in evidence.provenance.software" :key="a.path"><td>{{ a.path }}</td><td>{{ a.sha256 }}</td></tr></tbody></table></details>
      </section>
      <section><h2>本 Run 输出哈希</h2><table><thead><tr><th>受控相对路径</th><th>SHA-256</th></tr></thead><tbody><tr v-for="a in evidence.outputs" :key="a.path"><td>{{ a.path }}</td><td>{{ a.sha256 }}</td></tr></tbody></table></section>
      <section><h2>局限</h2><ul><li v-for="s in evidence.limitations" :key="s">{{ s }}</li></ul></section>
    </template>
  </main>
</template>
<style scoped>
.evidence { max-width: 1100px; margin: auto; padding: 2rem 1rem; color: #24384c; }section { padding: 1.2rem; margin: 1rem 0; border: 1px solid #dce4eb; border-radius: 8px; }p,td { overflow-wrap: anywhere; }p,li { line-height: 1.7; }h2 { font-size: 1.1rem; }h3 { font-size: 1rem; }pre { white-space: pre-wrap; overflow-wrap: anywhere; font-size: .8rem; }table { width: 100%; table-layout: fixed; text-align: left; font-size: .8rem; }td,th { padding: .5rem; border-bottom: 1px solid #dce4eb; }a { color: #214f75; }
</style>
