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
import { experimentLabels } from './presentation/zh-CN'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'entry', component: EntryPage },
    { path: '/home', name: 'home', component: HomePage },
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
  const titles: Record<string, string> = { home: '首页', explore: '引导探索', lab: '数字实验室', mechanism: '跨模态耗散机制', 'cross-flow': '跨流动对比', 'evidence-center': '证据中心', evidence: '证据详情' }
  const title = to.name === 'experiment' ? experimentLabels[String(to.params.experiment_id)] ?? '实验详情' : titles[String(to.name)]
  document.title = title ? `${title} · ShockPath` : 'ShockPath · 耗散路径数字实验与可视分析平台'
})
