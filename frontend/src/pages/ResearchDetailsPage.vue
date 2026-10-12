<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
const route = useRoute()

const innovations = [
  {
    number: '01', title: '双通道参数化，让耗散调节有明确方向', label: '耗散可调',
    description: '通过 q_aa 与 q_at 分别参数化声学耗散和声学触发的切向耗散。在固定界面状态下，两条参数方向可独立辨识，为研究激波分辨率与横向响应提供明确的调节路径。',
  },
  {
    number: '02', title: '分离触发与输出，解释跨模态作用', label: '机制可辨',
    description: '声学与法向跳跃构成触发门控，切向模态内容决定实际切向输出。切向跳跃不参与门控；在切向速度相等的严格一维状态下，跨模态切向通道自然失活。',
  },
  {
    number: '03', title: '以熵稳定结构约束耗散设计', label: '理论有据',
    description: '将熵守恒中心通量与半正定耗散算子结合。在可容许状态及非负参数条件下，背景、声学与切向通道各自具有非负的耗散熵产，使路径调节具有可验证的理论基础。',
  },
  {
    number: '04', title: '连接预算、分配与响应，让结果可核查', label: '证据可追溯',
    description: '求解器记录各通道的瞬时与累计熵耗散，ShockPath 进一步展示空间分配、频谱和流动指标，帮助分析耗散用了多少、作用在哪里，以及对应怎样的流动响应。',
  },
]
</script>

<template>
  <main class="research" data-page="research-details" aria-labelledby="research-heading">
    <header class="research__intro">
      <h1 id="research-heading">论文与 CFD 求解器的优势：<span>让数值耗散可调、可辨、可追溯。</span></h1>
      <p>相较于仅关注整体耗散强度和最终流场的求解方式，本研究在熵稳定框架下区分耗散路径，将参数、触发机制和实际作用联系起来，支持更细致的调节与归因。</p>
    </header>

    <section class="research__innovations" aria-labelledby="innovation-heading">
      <div class="research__section-heading"><p>RESEARCH / INNOVATION</p><h2 id="innovation-heading">论文的四个创新点</h2></div>
      <ol class="research__list">
        <li v-for="item in innovations" :key="item.number">
          <span class="research__number" aria-hidden="true">{{ item.number }}</span>
          <div><p class="research__label">{{ item.label }}</p><h3>{{ item.title }}</h3><p class="research__description">{{ item.description }}</p></div>
        </li>
      </ol>
    </section>

    <aside class="research__context" aria-label="实验结论的适用范围">
      <p><strong>如何理解这些优势</strong>路径预算、空间分配与宏观响应是不同层面的信息。参数对实际流动的影响依赖具体算例与指标，不能直接推断为所有流动都更稳定或所有模态都更强阻尼。</p>
      <p>熵稳定依据对应半离散结构；全离散熵残差作为数值诊断，并通过时间步细化检验。</p>
      <div class="research__evidence-links"><RouterLink to="/lab/mechanism">查看机制解释<AppIcon name="arrow" /></RouterLink><RouterLink to="/evidence">查看实验证据<AppIcon name="arrow" /></RouterLink></div>
    </aside>

    <footer class="research__footer">
      <RouterLink :to="{ name: 'entry', query: route.query }" class="research__back"><AppIcon name="arrow" />返回开始页</RouterLink>
      <RouterLink :to="{ name: 'home', query: route.query }" class="sp-button sp-button--primary" data-testid="details-start-experiment">开始实验<AppIcon name="arrow" /></RouterLink>
    </footer>
  </main>
</template>

<style scoped>
#app main.research { max-width: 1040px; padding: 64px clamp(24px, 5vw, 72px) 40px; }
.research__intro h1 { margin: 0; color: #2c4668; font-size: clamp(22px, 2.3vw, 30px); line-height: 1.6; }
.research__intro h1 span { display: block; color: #315ecb; font-size: clamp(25px, 3vw, 40px); text-wrap: balance; }
.research__intro > p { max-width: 760px; margin: 24px 0 0; color: #536780; font-size: 15px; line-height: 1.9; }
.research__innovations { margin-top: 48px; }
.research__section-heading { padding-bottom: 20px; border-bottom: 1px solid var(--sp-border); }
.research__section-heading > p { margin: 0 0 8px; color: #536780; font-size: 10px; letter-spacing: 2px; }
.research__section-heading h2 { margin: 0; font-size: 21px; }
.research__list { padding: 0; margin: 0; list-style: none; }
.research__list li { display: grid; grid-template-columns: 48px minmax(0, 1fr); gap: 24px; padding: 28px 0; border-bottom: 1px solid var(--sp-border); }
.research__number { color: #416de4; font-size: 26px; font-weight: 500; font-variant-numeric: tabular-nums; line-height: 1.4; }
.research__label { margin: 0 0 6px; color: #315ecb; font-size: 12px; }
.research__list h3 { margin: 0; font-size: 18px; }
.research__description { margin: 12px 0 0; color: #536780; font-size: 14px; line-height: 1.9; }
.research__context { margin-top: 32px; padding: 24px; background: #f3f6fc; border-left: 3px solid #81bbe0; border-radius: 0 12px 12px 0; }
.research__context p { margin: 0; font-size: 13px; color: #536780; line-height: 1.9; }
.research__context p + p { margin-top: 12px; }
.research__context strong { display: block; color: #2c4668; margin-bottom: 8px; font-size: 14px; font-weight: 600; }
.research__evidence-links { display: flex; flex-wrap: wrap; gap: 8px 28px; margin-top: 12px; }
.research__evidence-links a { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; font-size: 13px; }
.research__evidence-links .sp-icon { width: 16px; height: 16px; }
.research__footer { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-top: 40px; padding-top: 24px; border-top: 1px solid var(--sp-border); }
.research__back { display: inline-flex; align-items: center; gap: 10px; min-height: 44px; font-size: 14px; text-decoration: none; color: #536780; }
.research__back:hover { color: var(--sp-primary); }
.research__back .sp-icon { transform: rotate(180deg); width: 18px; }
@media (max-width: 600px) {
  #app main.research { padding: 32px 20px; }
  .research__intro h1 { font-size: 19px; }
  .research__intro h1 span { font-size: 25px; }
  .research__intro > p { font-size: 14px; }
  .research__innovations { margin-top: 32px; }
  .research__list li { grid-template-columns: 32px minmax(0, 1fr); gap: 12px; padding: 24px 0; }
  .research__number { font-size: 22px; }
  .research__list h3 { font-size: 16px; }
  .research__context { padding: 20px; }
}
</style>
