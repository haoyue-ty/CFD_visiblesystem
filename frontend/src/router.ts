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
