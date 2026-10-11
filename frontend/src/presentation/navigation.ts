export const primaryNavigation = [
  { id: 'home', label: '首页', path: '/home', icon: 'dashboard' },
  { id: 'create', label: '新建计算', path: '/experiments/new', icon: 'plus' },
  { id: 'workspace', label: '运行任务', path: '/workspace', icon: 'activity' },
  { id: 'lab', label: '算例库', path: '/lab', icon: 'layers' },
  { id: 'help', label: '帮助', path: '/help', icon: 'book' },
] as const

export type NavigationSection = typeof primaryNavigation[number]['id']
export function navigationSection(path: string): NavigationSection {
  if (/^\/(workspace|runs|sweeps)(\/|$)/.test(path)) return 'workspace'
  if (/^\/experiments\/new(\/|$)/.test(path)) return 'create'
  if (/^\/lab(\/|$)/.test(path) || path === '/cross-flow') return 'lab'
  if (/^\/(help|explore|evidence)(\/|$)/.test(path)) return 'help'
  return 'home'
}
