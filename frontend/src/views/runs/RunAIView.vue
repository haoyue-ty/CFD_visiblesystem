<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { askRun, interpretRun, type AIAnalysis, type AIView } from '../../data/v2/ai'
import AIClaimView from './AIClaimView.vue'
const props = defineProps<{ runId: string; view?: AIView }>()
const interpretation = ref<AIAnalysis>(), answer = ref<AIAnalysis>()
const interpreting = ref(false), asking = ref(false), interpretError = ref(''), chatError = ref(''), message = ref('')
const answeredMessage = ref('')
let generation = 0, chatGeneration = 0
async function interpret() {
  if (interpreting.value) return
  const current = generation
  interpreting.value = true; interpretError.value = ''
  try { const data = await interpretRun(props.runId); if (current === generation) interpretation.value = data }
  catch (e) { if (current === generation) interpretError.value = e instanceof Error ? e.message : 'AI 解读暂不可用。' }
  finally { if (current === generation) interpreting.value = false }
}
async function ask(question = message.value) {
  if (asking.value || !props.view || !question.trim()) return
  const current = generation, selection = chatGeneration
  asking.value = true; chatError.value = ''; answer.value = undefined; answeredMessage.value = question
  try { const data = await askRun(props.runId, question, { ...props.view }); if (current === generation && selection === chatGeneration) answer.value = data }
  catch (e) { if (current === generation && selection === chatGeneration) chatError.value = e instanceof Error ? e.message : 'AI 问答暂不可用。' }
  finally { if (current === generation && selection === chatGeneration) asking.value = false }
}
watch(() => props.runId, () => {
  ++generation; ++chatGeneration; interpretation.value = undefined; answer.value = undefined
  interpreting.value = false; asking.value = false; interpretError.value = ''; chatError.value = ''; message.value = ''; interpret()
}, { immediate: true })
watch(() => props.view, () => { ++chatGeneration; answer.value = undefined; asking.value = false; chatError.value = ''; answeredMessage.value = '' }, { deep: true })
onUnmounted(() => { ++generation; ++chatGeneration })
</script>
<template>
  <aside class="ai-panel" data-testid="run-ai">
    <section><h2>AI 结果解读</h2>
      <p class="hint">解释本次计算；数值和证据由后端提供。</p>
      <p v-if="interpreting" role="status">正在生成结果解读…</p>
      <p v-if="interpretError" role="alert" data-testid="ai-interpret-error">{{ interpretError }}</p>
      <button v-if="interpretError" :disabled="interpreting" @click="interpret">重试 AI 解读</button>
      <template v-if="interpretation?.interpretation">
        <p class="hint" data-testid="ai-cache-status">{{ interpretation.cached ? '已加载缓存解读' : '本次生成的解读' }} · {{ interpretation.model }}</p>
        <AIClaimView :claim="interpretation.interpretation.summary" :analysis="interpretation" />
        <h3>主要发现</h3><AIClaimView v-for="(claim, i) in interpretation.interpretation.key_findings" :key="`finding-${i}`" :claim="claim" :analysis="interpretation" />
        <h3>结果观察</h3><AIClaimView v-for="(claim, i) in interpretation.interpretation.observations" :key="`obs-${i}`" :claim="claim" :analysis="interpretation" />
        <h3>解读局限</h3><ul><li v-for="item in interpretation.interpretation.limitations" :key="item">{{ item }}</li></ul>
        <button v-for="question in interpretation.interpretation.suggested_questions" :key="question" :disabled="asking || !view" @click="message = question; ask(question)">{{ question }}</button>
      </template>
    </section>
    <section><h2>上下文科研助手</h2>
      <p v-if="view" class="hint" data-testid="ai-current-view">{{ view.field }} · {{ view.snapshot_id }} · {{ view.x_min != null ? '已选择矩形区域' : '全域' }}</p>
      <p v-else class="hint">等待有效快照与区域统计后可提问。</p>
      <form @submit.prevent="ask()"><label for="science-question">科研问题</label>
        <textarea id="science-question" v-model="message" maxlength="2000" rows="3" placeholder="例如：这次熵预算能说明方法更稳定吗？" />
        <button type="submit" :disabled="asking || !view || !message.trim()">{{ asking ? '正在回答…' : '提问' }}</button>
      </form>
      <p v-if="chatError" role="alert" data-testid="ai-chat-error">{{ chatError }} <button :disabled="asking || !view" @click="ask()">重试问答</button></p>
      <template v-if="answer?.assistant"><p>{{ answeredMessage }}</p>
        <AIClaimView v-for="(claim, i) in answer.assistant.answer" :key="i" :claim="claim" :analysis="answer" />
        <ul><li v-for="item in answer.assistant.limitations" :key="item">{{ item }}</li></ul>
        <p class="hint">回答绑定 t={{ answer.current_view?.time }} 的真实区域统计；切换视图后可重新提问。</p>
      </template>
    </section>
    <details v-if="interpretation"><summary>科学边界与版本</summary><ul><li v-for="item in interpretation.limitations" :key="item">{{ item }}</li></ul>
      <p class="hash">result={{ interpretation.result_hash }} · prompt={{ interpretation.prompt_version }} · context={{ interpretation.context_hash }}</p></details>
    <p class="hint">AI 不可用时，已有流场、熵预算、指标与证据仍可使用。</p>
  </aside>
</template>
<style scoped>
.ai-panel { border: 1px solid #dce4eb; border-radius: 8px; padding: 1.2rem; margin: 1rem 0; min-width: 0; align-self: start; }section + section { border-top: 1px solid #dce4eb; margin-top: 1rem; padding-top: 1rem; }h2 { font-size: 1.1rem; }h3 { font-size: .9rem; }.hint { color: #617184; font-size: .8rem; }p,li { line-height: 1.65; overflow-wrap: anywhere; }ul { padding-left: 1rem; }textarea { display: block; box-sizing: border-box; width: 100%; resize: vertical; margin: .5rem 0; }button,textarea { font: inherit; border: 1px solid #bdccda; border-radius: 5px; background: white; padding: .45rem; max-width: 100%; }button { margin: .25rem .25rem .25rem 0; }button:disabled { opacity: .5; }.hash { overflow-wrap: anywhere; font-size: .75rem; }
@media(min-width:1200px) { .ai-panel { position: sticky; top: 1rem; max-height: calc(100vh - 2rem); overflow: auto; } }
</style>
