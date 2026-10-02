import { test, expect } from '@playwright/test'
import { factText, knownValue, safeText, verificationLabels } from '../src/data/evidence'
import { returnContext } from '../src/views/evidence/returnContext'

test('recorded zero and false remain known; unknown facts carry reasons', () => {
  expect(factText({ state: 'KNOWN', value: 0 })).toBe('0')
  expect(knownValue({ state: 'KNOWN', value: false })).toBe(false)
  expect(factText({ state: 'UNKNOWN', reason: 'No freeze timestamp recorded' })).toBe('Unknown — No freeze timestamp recorded')
  expect(factText({ state: 'MISSING', reason: 'raw scan absent' })).toBe('MISSING — raw scan absent')
})
test('verification mapping retains every frozen status and distinguishes history and unfrozen evidence', () => {
  expect(Object.keys(verificationLabels)).toHaveLength(9)
  expect(new Set(Object.values(verificationLabels)).size).toBe(9)
  expect(verificationLabels.FROZEN_VERIFIED).toContain('FROZEN_ACCEPTED')
  expect(verificationLabels.VERIFIED_NOT_FROZEN).toBe('VERIFIED_NOT_FROZEN')
  expect(verificationLabels.SUPERSEDED).toContain('HISTORY')
  expect(verificationLabels.AVAILABLE_UNVERIFIED).toContain('UNKNOWN')
})
test('public provenance and error text strip locators while preserving controlled relative origins', () => {
  for (const value of ['D:\\science\\run.npz', 'D:/science/run.npz', 'file:///D:/science/run.npz', '\\\\server\\science\\run.npz', '/home/user/science/run.npz']) {
    expect(safeText(`Cannot read ${value}`)).toBe('Cannot read [source locator withheld]')
  }
  expect(safeText('solver/fluxes/cross_mode_ec_unified_v1.py')).toBe('solver/fluxes/cross_mode_ec_unified_v1.py')
})
for (const value of [null, '{broken', JSON.stringify({ name: 'https://evil.example' }), JSON.stringify({ name: 'lab', path: 'file:///D:/science' }), JSON.stringify({ name: 'experiment' }), JSON.stringify({ name: 'lab', query: { nested: {} } })]) {
  test(`unsafe return context rejected: ${value}`, () => expect(returnContext(value)).toBeNull())
}
test('result and center return contexts preserve exact selectors', () => {
  for (const value of [
    { name: 'experiment', params: { experiment_id: 'case8' }, query: { config: 'D_u', tab: 'allocation', spectral_mode: '8', spectral_q: 'spectrum.q-0.396' } },
    { name: 'explore', query: { scene: '6', case8_config: 'D_u', cylinder_config: 'B_u' } },
    { name: 'evidence-center', query: { section: 'HISTORY', offset: '20' } },
  ]) expect(returnContext(JSON.stringify(value))).toEqual(value)
})
