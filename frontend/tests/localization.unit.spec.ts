import { test, expect } from '@playwright/test'
import { zh, chartCopy, availabilityLabels, factLabels, verificationLabels, sceneCopy } from '../src/presentation/zh-CN'

test('presentation preserves scientific identities, formulas, precision and recorded zero', () => {
  for (const value of ['ShockPath', 'cross_mode_ec_unified_v1', 'ev.case8.D_u.allocation', 'A_u', 'B_u', 'C_u', 'D_u',
    'q_at = 0.396', 'Re(λ)', 'Pi_at', 'a'.repeat(64), 'result_hashes.csv', 'constructor', '__proto__']) expect(zh(value)).toBe(value)
  expect(zh(0)).toBe('0')
  expect(zh(0.03483470441226932)).toBe('0.03483470441226932')
  expect(availabilityLabels.MISSING).toBe('缺失')
  expect(factLabels.UNKNOWN).toBe('未知')
  expect(verificationLabels.VERIFIED_NOT_FROZEN).toBe('已验证 · 未冻结')
  expect(zh('Back to Explore S3')).toBe('返回引导探索第 3 幕')
  expect(zh('mode 8 · q_at=0.396 · ε=0.0001')).toBe('模态 8 · q_at=0.396 · ε=0.0001')
})

test('chart localization copies labels without rewriting or mutating scientific data', () => {
  const data = Object.freeze([[0, 0], [1, null], [2, 0.396]])
  const option = Object.freeze({ title: { text: 'Integrated budget' }, xAxis: { name: 'Physical time' },
    series: [{ name: 'D_u', data }], dataset: { source: data } })
  const rendered = chartCopy(option)
  expect(rendered.title.text).toBe('累计预算')
  expect(rendered.xAxis.name).toBe('物理时间')
  expect(rendered.series[0]!.name).toBe('D_u')
  expect(rendered.series[0]!.data).toBe(data)
  expect(rendered.dataset.source).toBe(data)
  expect(option.title.text).toBe('Integrated budget')
})

test('seven scenes retain strict-1D zero-output and modal/comparison boundaries', () => {
  expect(Object.keys(sceneCopy)).toHaveLength(7)
  expect(sceneCopy[3]!.conclusion).toContain('声学触发可以存在')
  expect(sceneCopy[3]!.conclusion).toContain('切向接收内容为零')
  expect(sceneCopy[5]!.conclusion).toBe('正熵产 ≠ 所有模态统一增强阻尼')
  expect(sceneCopy[6]!.conclusion).toBe('路径预算 ≠ 空间分配 ≠ 宏观响应')
})
