<script setup lang="ts">
import { statusLabels } from '../data/v2/runs'
const concepts = [
  ['CFD', '计算流体力学：用离散方程在网格上求解流动，分析场量随时间的演化。'],
  ['Solver', '实际执行数值计算的求解器。本系统用独立进程运行已登记的 Case 8 Solver。'],
  ['Mach', '流速与当地声速之比。当前新建 Case 8 的入流 Mach 固定为 6。'],
  ['CFL', '与波速、网格和时间步长相关的无量纲数。当前 Case 8 固定 CFL=0.05，并沿用初态确定的固定步长策略。'],
  ['网格', '把计算域划分为单元。当前实时 Case 8 登记 64×16 和 128×32 两种网格组合。'],
  ['q_aa', '声学耗散路径的系数。当前可选 3.96、13.2，具体设置需要后端能力验证。'],
  ['q_at', '声学触发到切向输出的跨模态耗散路径系数。当前可选 0、0.396；正熵产不等于所有模态统一增强阻尼。'],
]
const descriptions: Record<string, string> = {
  QUEUED: '配置已提交，等待前面的任务结束。', STARTING: '正在创建并校验独立求解进程。',
  RUNNING: '真实 Solver 正在计算，进度来自已接受步和实际物理时间。',
  POSTPROCESSING: '求解结束，正在进行确定性后处理及结果校验。',
  COMPLETED: '计算与后处理完成，可查看科学结果并生成报告。',
  FAILED: '求解或校验失败，查看任务日志与失败原因。', CANCELLED: '任务已取消，局部输出不会作为完成结果。',
}
</script>
<template>
  <main data-page="help">
    <header><p class="sp-eyebrow">SHOCKPATH · 帮助</p><h1>开始你的数值实验</h1><p class="sp-intro">从创建计算到导出报告，了解工作流程、常见概念与结果的适用边界。</p></header>
    <section class="sp-section" aria-labelledby="help-start"><div class="sp-section-heading"><h2 id="help-start">三步快速入门</h2></div>
      <ol class="help-steps"><li class="sp-panel"><span class="sp-badge">01</span><h3>新建 CFD 计算</h3><p>选择模板、专业参数或自然语言输入。验证配置，核对参数与协议差异，再确认并点击“启动求解”。</p><RouterLink to="/experiments/new" class="sp-button sp-button--primary">新建计算 →</RouterLink></li>
        <li class="sp-panel"><span class="sp-badge">02</span><h3>等待真实 Solver 运行</h3><p>在运行任务里观察步数、物理时间、日志与熵诊断。任务串行执行，刷新页面后仍可继续查看。</p><RouterLink to="/workspace" class="sp-button">查看运行任务 →</RouterLink></li>
        <li class="sp-panel"><span class="sp-badge">03</span><h3>查看、分析并导出结果</h3><p>完成后在同一工作区查看流场、指标、熵预算、空间分配和 AI 解读，进入实验报告并保存 HTML。</p><p class="sp-muted">科学证据与报告入口位于已完成任务的详情页。</p></li></ol>
    </section>
    <section class="sp-section sp-panel" aria-labelledby="help-concepts"><h2 id="help-concepts">常见概念</h2><dl class="sp-kv"><template v-for="[name, description] in concepts" :key="name"><dt>{{ name }}</dt><dd>{{ description }}</dd></template></dl></section>
    <section class="sp-section sp-panel" aria-labelledby="help-states"><h2 id="help-states">运行状态说明</h2><dl class="sp-kv"><template v-for="(label, status) in statusLabels" :key="status"><dt>{{ label }}<small>{{ status }}</small></dt><dd>{{ descriptions[status] }}</dd></template></dl></section>
    <section class="sp-section" aria-labelledby="help-tutorials"><div class="sp-section-heading"><h2 id="help-tutorials">科研教程</h2><span class="sp-muted" data-testid="explore-status">已交付 · 7 幕引导</span></div>
      <div class="help-tutorials"><RouterLink :to="{ path: '/explore', query: { scene: '1' } }" class="sp-panel" data-testid="help-start-explore"><h3>七幕引导探索 →</h3><p>沿着冻结数据，理解预算、触发、空间分配和流动响应。</p></RouterLink>
        <RouterLink to="/lab/mechanism" class="sp-panel"><h3>跨模态耗散机制 →</h3><p>区分触发信息、输出子空间与宏观响应。</p></RouterLink>
        <RouterLink to="/evidence" class="sp-panel" data-testid="help-open-evidence"><h3>科学证据中心 →</h3><p>追溯方法、参数、数据来源、验证状态与已知缺口。</p></RouterLink></div>
    </section>
    <section class="sp-section sp-panel" aria-labelledby="help-trust"><h2 id="help-trust">如何理解结果可信性</h2>
      <h3>实时计算与历史回放</h3><p>新建计算会提交独立 Run，执行真实 Solver 并保存本次输出。算例库的“历史数据回放”只读取已有科研记录；切换图表不会启动新的计算。</p>
      <h3>配置匹配与科学复现</h3><p>论文标准配置匹配（LIVE_PAPER_PROFILE）说明参数与登记协议一致。科学复现需要另行核查数值结果、来源哈希、指标定义与验证范围，配置匹配本身不能证明复现成功。</p>
      <h3>AI 解读与数值计算</h3><p>AI 依据真实数据提供解释，不能修改 CFD 结果。AI 不可用时，模板、专业参数、真实求解、科学证据和确定性报告仍可使用。</p>
      <h3>运行对比的适用范围</h3><p>A/B 对比保留后端科学可比性检查。物理条件或指标定义不同时，只能并列观察；跨流动对比为描述性比较，不能据此做严格性能排名。</p>
    </section>
  </main>
</template>
<style scoped>
.help-steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; padding: 0; list-style: none; }
.help-steps p, .help-tutorials p { font-size: 14px; color: var(--sp-muted); }
.help-tutorials { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.help-tutorials a { text-decoration: none; }.help-tutorials a:hover { border-color: var(--sp-primary); }.help-tutorials h3 { color: var(--sp-primary); margin-top: 0; }
small { display: block; font-size: 10px; }
@media (max-width: 768px) { .help-steps, .help-tutorials { grid-template-columns: 1fr; } }
</style>
