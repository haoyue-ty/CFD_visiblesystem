import { createRouter, createWebHistory } from 'vue-router'
import EntryPage from './pages/EntryPage.vue'
import HomePage from './pages/HomePage.vue'
import LabPage from './pages/LabPage.vue'
import ExperimentPage from './pages/ExperimentPage.vue'
import EvidencePage from './pages/EvidencePage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'entry', component: EntryPage },
    { path: '/home', name: 'home', component: HomePage },
    { path: '/lab', name: 'lab', component: LabPage },
    { path: '/lab/experiments/:experiment_id', name: 'experiment', component: ExperimentPage, props: true },
    { path: '/evidence/:evidence_id', name: 'evidence', component: EvidencePage, props: true },
  ],
})
