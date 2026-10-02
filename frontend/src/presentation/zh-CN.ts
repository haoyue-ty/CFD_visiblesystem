import copy from './zh-CN.json' with { type: 'json' }

/** Exact presentation lookup only. Unknown identifiers, formulas and values pass through. */
export function zh(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  const text = String(value), key = text.replace(/\s+/g, ' ').trim()
  const labels = copy as Record<string, string>
  const lookup = (term: string) => Object.hasOwn(labels, term) ? labels[term] : undefined
  if (lookup(key)) return lookup(key)!
  const endpoint = key.match(/^Corrected Case8 ([ABCD]_u) recorded endpoint$/)
  if (endpoint) return `Case 8 ${endpoint[1]} 已校正的记录端点`
  const budget = key.match(/^Case8 ([ABCD]_u) accepted-step entropy budget history$/)
  if (budget) return `Case 8 ${budget[1]} 已接受步熵预算历史`
  const returnScene = key.match(/^Back to Explore S([23])$/)
  if (returnScene) return `返回引导探索第 ${returnScene[1]} 幕`
  const modeLabel = key.match(/^mode (\d+)( · .+)$/)
  if (modeLabel) return `模态 ${modeLabel[1]}${modeLabel[2]}`
  // Separators are presentation prose boundaries, not word substitution.
  return text.split(/( · | — |; ?|；|: )/).map(part => lookup(part.trim()) ?? part).join('')
}
export const availabilityLabels: Record<string, string> = { AVAILABLE: '可用', SUPPORTED: '支持', PARTIAL: '部分可用', MISSING: '缺失', UNSUPPORTED: '不支持', ERROR: '加载失败', READY: '已加载', LOADING: '正在加载…' }
export const factLabels: Record<string, string> = { KNOWN: '已知', UNKNOWN: '未知', MISSING: '缺失', NOT_APPLICABLE: '不适用' }
export const verificationLabels: Record<string, string> = { FROZEN_ACCEPTED: '已冻结验收', VERIFIED: '已验证', VERIFIED_NOT_FROZEN: '已验证 · 未冻结', DIAGNOSTIC_RERUN: '诊断性重运行', PARTIAL: '部分验证', MISSING: '缺失', HISTORY: '历史记录', SUPERSEDED: '已被替代', UNKNOWN: '未知', FROZEN_VERIFIED: '已冻结验收', DERIVED_VERIFIED: '已验证（派生）', AVAILABLE_UNVERIFIED: '可读取 · 验证未知', LEGACY: '历史版本', NOT_APPLICABLE: '不适用' }
export const evidenceSectionLabels: Record<string, string> = { CURRENT: '当前证据', GAPS: '数据缺口', HISTORY: '历史记录' }
export const originLabels: Record<string, string> = { FROZEN_PRODUCTION: '冻结生产数据', VERIFIED_PRODUCTION: '已验证生产数据', DIAGNOSTIC_RERUN: '诊断性重运行', SCHEMATIC: '机制示意', MOCK: 'MOCK · 模拟数据' }
export const tabLabels: Record<string, string> = { overview: '概览', flow: '流场', entropy: '熵耗散', allocation: '空间分配', sectors: '扇区分配', metrics: '指标', summary: '汇总', spectrum: '频谱', spectral: '频谱', modes: '模态', validation: '验证', 'semi-discrete': '半离散', 'fully-discrete': '全离散', evidence: '证据', refinement: '时间加密' }
export const experimentLabels: Record<string, string> = { case8: 'Case 8', cylinder: 'Mach 3 圆柱绕流', gate: '门控消融实验', 'entropy-closure': '熵预算闭合', spectrum: '横向模态频谱', 'modal-validation': '模态验证', mechanism: '跨模态耗散机制' }
export const sceneCopy: Record<number, { title: string; description: string; conclusion: string }> = {
  1: { title: '耗散有多少？', description: '首先量化不同耗散路径在整个计算过程中的累计贡献。', conclusion: '预算可以测量，但耗散量的大小本身不足以解释最终效果。' },
  2: { title: '是什么触发了它？它作用在哪里？', description: '区分触发信息、输出子空间和实际空间作用位置。', conclusion: '触发 ≠ 输出：触发信息、输出子空间与空间作用位置需要分别理解。' },
  3: { title: '触发 ≠ 输出', description: '声学信息可以触发跨模态路径，但触发位置与最终耗散输出并不是同一个概念。', conclusion: '严格一维下，声学触发可以存在，但切向接收内容为零，因此跨模态切向输出为零。' },
  4: { title: '相近预算 ≠ 相同空间分配', description: '即使累计耗散预算接近，不同门控方式仍可能将耗散分配到不同的空间位置。', conclusion: '相近预算 ≠ 相同空间分配' },
  5: { title: '正熵产 ≠ 所有模态统一增强阻尼', description: '熵稳定保证数学熵产非负，但并不意味着所有横向 Fourier 模态都朝同一方向变化。', conclusion: '正熵产 ≠ 所有模态统一增强阻尼' },
  6: { title: '相同路径 ≠ 相同宏观响应', description: '相同的跨模态耗散路径，在不同流动结构中可以形成不同的空间分配与宏观响应。', conclusion: '路径预算 ≠ 空间分配 ≠ 宏观响应' },
  7: { title: '每个结论，都有证据可追溯', description: '真实求解器 · 冻结证据 · 方法哈希。每个正式科学结论都可以追溯到对应方法、配置、数据来源、哈希、处理过程和适用边界。', conclusion: '结论以可追溯证据为依据，并受到科学适用边界的约束。' },
}

/** Copy chart options, translating display fields only; never touch data or coordinate arrays. */
export function chartCopy<T>(option: T): T {
  function visit(value: unknown, key = ''): unknown {
    if (['data', 'points', 'dimensions', 'source'].includes(key)) return value
    if (typeof value === 'string' && ['name', 'text', 'subtext'].includes(key)) return zh(value)
    if (Array.isArray(value)) return value.map(item => visit(item))
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, visit(v, k)]))
    return value
  }
  return visit(option) as T
}
