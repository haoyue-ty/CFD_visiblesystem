import { test, expect } from '@playwright/test'
import { factValue } from '../src/data/apiProvider'

test('recorded zero remains zero', () => expect(factValue({ state: 'KNOWN', value: 0 })).toBe(0))
for (const state of ['UNKNOWN', 'MISSING', 'NOT_APPLICABLE'] as const) {
  test(`${state} is never projected to zero`, () => expect(factValue({ state, reason: 'Not recorded' })).toBeNull())
}
test('recorded physical time keeps its full precision', () => {
  const time = 0.01598326359832636
  expect(factValue({ state: 'KNOWN', value: time })).toBe(time)
})
