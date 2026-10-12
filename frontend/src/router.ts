import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './pages/HomePage.vue'
import EntryPage from './pages/EntryPage.vue'
import ResearchDetailsPage from './pages/ResearchDetailsPage.vue'
import AuthPage from './pages/AuthPage.vue'
import { authState, loadAuthSession } from './data/auth'
import HelpPage from './pages/HelpPage.vue'
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
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, top: 20 }
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'entry', component: EntryPage },
    { path: '/research', name: 'research-details', component: ResearchDetailsPage },
    { path: '/login', name: 'login', component: AuthPage },
    { path: '/register', name: 'register', component: AuthPage },
    { path: '/home', name: 'home', component: HomePage, meta: { requiresAuth: true } },
    { path: '/help', name: 'help', component: HelpPage },
    { path: '/experiments/new', name: 'experiment-builder', component: ExperimentBuilderPage, meta: { requiresAuth: true } },
    { path: '/workspace', name: 'run-list', component: RunListPage, meta: { requiresAuth: true } },
    { path: '/workspace/compare', name: 'run-comparison', component: RunComparisonPage, meta: { requiresAuth: true } },
    { path: '/workspace/sweeps', name: 'parameter-sweeps', component: ParameterSweepPage, meta: { requiresAuth: true } },
    { path: '/sweeps/:sweepId', name: 'parameter-sweep', component: ParameterSweepPage, meta: { requiresAuth: true } },
    { path: '/runs/:runId', name: 'run-workspace', component: RunWorkspacePage, meta: { requiresAuth: true } },
    { path: '/runs/:runId/evidence', name: 'run-evidence', component: RunEvidencePage, meta: { requiresAuth: true } },
    { path: '/runs/:runId/report', name: 'run-report', component: RunReportPage, meta: { requiresAuth: true } },
    { path: '/lab', name: 'lab', component: LabPage },
    { path: '/lab/mechanism', name: 'mechanism', component: MechanismPage },
    { path: '/explore', name: 'explore', component: ExplorePage },
    { path: '/cross-flow', alias: '/lab/compare/case8-cylinder', name: 'cross-flow', component: CrossFlowPage },
    { path: '/lab/experiments/:experiment_id', name: 'experiment', component: ExperimentPage, props: true },
    { path: '/evidence', name: 'evidence-center', component: EvidenceCenterPage },
    { path: '/evidence/:evidence_id', name: 'evidence', component: EvidencePage, props: true },
  ],
})

router.beforeEach(async to => {
  if (!to.meta.requiresAuth) return true
  try {
    await loadAuthSession(true)
    if (!authState.enabled || authState.user) return true
  } catch { /* A service failure must not grant access. */ }
  return { name: 'login', query: { redirect: to.fullPath } }
})

router.afterEach(to => {
  if (to.name === 'run-comparison') { document.title = '运行对比 · ShockPath'; return }
  if (to.name === 'parameter-sweeps' || to.name === 'parameter-sweep') { document.title = '参数扫描 · ShockPath'; return }
  if (to.name === 'run-report') { document.title = '实验报告 · ShockPath'; return }
  if (to.name === 'run-evidence') { document.title = '本次运行证据 · ShockPath'; return }
  const titles: Record<string, string> = { entry: '开始实验', login: '登录', register: '注册', 'research-details': '论文与求解器优势', home: '首页', help: '帮助', explore: '引导探索', lab: '算例库', mechanism: '跨模态耗散机制', 'cross-flow': '跨流动对比', 'evidence-center': '证据中心', evidence: '证据详情' }
  const title = to.name === 'run-list' ? '运行任务' : to.name === 'run-workspace' ? '运行详情' : to.name === 'experiment-builder' ? '新建计算' : to.name === 'experiment' ? experimentLabels[String(to.params.experiment_id)] ?? '算例详情' : titles[String(to.name)]
  document.title = title ? `${title} · ShockPath` : 'ShockPath · 交互式 CFD 求解与智能数值分析系统'
})
