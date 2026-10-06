import { createRouter, createWebHistory } from 'vue-router'
import EntryPage from './pages/EntryPage.vue'
import HomePage from './pages/HomePage.vue'
import LabPage from './pages/LabPage.vue'
import ExperimentPage from './pages/ExperimentDetailPage.vue'
import CrossFlowPage from './pages/CrossFlowPage.vue'
import EvidencePage from './pages/EvidencePage.vue'
import EvidenceCenterPage from './pages/EvidenceCenterPage.vue'
import MechanismPage from './pages/MechanismPage.vue'
import ExplorePage from './pages/ExplorePage.vue'
import ExperimentBuilderPage from './pages/ExperimentBuilderPage.vue'
import RunListPage from './pages/RunListPage.vue'
import RunWorkspacePage from './pages/RunWorkspacePage.vue'
import RunEvidencePage from './pages/RunEvidencePage.vue'
import RunReportPage from './pages/RunReportPage.vue'
import RunComparisonPage from './pages/RunComparisonPage.vue'
import ParameterSweepPage from './pages/ParameterSweepPage.vue'
import { experimentLabels } from './presentation/zh-CN'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'entry', component: EntryPage },
    { path: '/home', name: 'home', component: HomePage },
    { path: '/experiments/new', name: 'experiment-builder', component: ExperimentBuilderPage },
    { path: '/workspace', name: 'run-list', component: RunListPage },
    { path: '/workspace/compare', name: 'run-comparison', component: RunComparisonPage },
    { path: '/workspace/sweeps', name: 'parameter-sweeps', component: ParameterSweepPage },
    { path: '/sweeps/:sweepId', name: 'parameter-sweep', component: ParameterSweepPage },
    { path: '/runs/:runId', name: 'run-workspace', component: RunWorkspacePage },
    { path: '/runs/:runId/evidence', name: 'run-evidence', component: RunEvidencePage },
    { path: '/runs/:runId/report', name: 'run-report', component: RunReportPage },
    { path: '/lab', name: 'lab', component: LabPage },
    { path: '/lab/mechanism', name: 'mechanism', component: MechanismPage },
    { path: '/explore', name: 'explore', component: ExplorePage },
    { path: '/cross-flow', alias: '/lab/compare/case8-cylinder', name: 'cross-flow', component: CrossFlowPage },
    { path: '/lab/experiments/:experiment_id', name: 'experiment', component: ExperimentPage, props: true },
    { path: '/evidence', name: 'evidence-center', component: EvidenceCenterPage },
    { path: '/evidence/:evidence_id', name: 'evidence', component: EvidencePage, props: true },
  ],
})

router.afterEach(to => {
  if (to.name === 'run-comparison') { document.title = '运行对比 · ShockPath'; return }
  if (to.name === 'parameter-sweeps' || to.name === 'parameter-sweep') { document.title = '系数扫描 · ShockPath'; return }
  if (to.name === 'run-report') { document.title = '实验报告 · ShockPath'; return }
  if (to.name === 'run-evidence') { document.title = '本次运行证据 · ShockPath'; return }
  const titles: Record<string, string> = { home: '首页', explore: '引导探索', lab: '数字实验室', mechanism: '跨模态耗散机制', 'cross-flow': '跨流动对比', 'evidence-center': '证据中心', evidence: '证据详情' }
  const title = to.name === 'run-list' ? '实验工作台' : to.name === 'run-workspace' ? '运行详情' : to.name === 'experiment-builder' ? '新建实验' : to.name === 'experiment' ? experimentLabels[String(to.params.experiment_id)] ?? '实验详情' : titles[String(to.name)]
  document.title = title ? `${title} · ShockPath` : 'ShockPath · 耗散路径数字实验与可视分析平台'
})
