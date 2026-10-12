import { expect, test } from '@playwright/test'
import { safeAuthRedirect } from '../src/data/auth'

test('login resumes only local workspace destinations', () => {
  for (const value of ['/home?layout=poster#recent-heading', '/experiments/new?template=case8.fast.D_u', '/runs/example/report', '/workspace/compare', '/sweeps/example']) expect(safeAuthRedirect(value)).toBe(value)
  for (const value of ['https://foreign.example', '//foreign.example', '/\\foreign.example', '/login', '/register', '/home\n', null, ['//foreign.example']]) expect(safeAuthRedirect(value)).toBe('/home')
})
