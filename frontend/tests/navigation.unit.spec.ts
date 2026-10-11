import { test, expect } from '@playwright/test'
import { primaryNavigation, navigationSection } from '../src/presentation/navigation'
import { runProgress } from '../src/presentation/runs'

test('five primary destinations retain parents for every compatibility route', () => {
  expect(primaryNavigation.map(n => [n.label, n.path])).toEqual([
    ['首页', '/home'], ['新建计算', '/experiments/new'], ['运行任务', '/workspace'], ['算例库', '/lab'], ['帮助', '/help'],
  ])
  for (const path of ['/workspace', '/workspace/compare', '/workspace/sweeps', '/sweeps/real-id', '/runs/real-id', '/runs/real-id/report', '/runs/real-id/evidence']) expect(navigationSection(path)).toBe('workspace')
  for (const path of ['/lab', '/lab/mechanism', '/lab/experiments/case8', '/lab/compare/case8-cylinder', '/cross-flow']) expect(navigationSection(path)).toBe('lab')
  for (const path of ['/help', '/explore', '/evidence', '/evidence/ev.case8.D_u']) expect(navigationSection(path)).toBe('help')
  expect(navigationSection('/experiments/new')).toBe('create')
  expect(navigationSection('/')).toBe('home')
  expect(navigationSection('/home')).toBe('home')
})

test('progress is derived from recorded physical time and stays finite while queued', () => {
  expect(runProgress({ physical_time: .02, requested_final_time: .04 })).toBe(50)
  expect(runProgress({ physical_time: 0, requested_final_time: .04 })).toBe(0)
  expect(runProgress({ physical_time: .041, requested_final_time: .04 })).toBe(100)
  expect(runProgress({ physical_time: 0, requested_final_time: 0 })).toBe(0)
})
