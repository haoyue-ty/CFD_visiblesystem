import { api } from '../../services/api'
import type { components } from '../../types/generated/api'
import { ExperimentApiError } from './experiments'
export type Comparison = Awaited<ReturnType<typeof compareRuns>>
export type Sweep = Awaited<ReturnType<typeof loadSweep>>
export type SweepInput = components['schemas']['Input_SweepRequest']
export type Preview = Awaited<ReturnType<typeof previewSweep>>
function fail(error?: components['schemas']['V2FailedEnvelope']): never {
  throw new ExperimentApiError(error?.error.message ?? '请求失败，请重试。', error?.error.details ?? [], error?.error.code)
}
export async function compareRuns(body: components['schemas']['Input_CompareRunsRequest']) {
  const { data, error } = await api.POST('/api/v2/comparisons', { body })
  if (!data) fail(error)
  return data.data
}
export async function previewSweep(body: SweepInput) {
  const { data, error } = await api.POST('/api/v2/sweeps/preview', { body })
  if (!data) fail(error)
  return data.data
}
export async function createSweep(body: SweepInput, confirmed_sweep_hash: string, idempotency_key: string) {
  const { data, error } = await api.POST('/api/v2/sweeps', { body: { ...body, confirmed_sweep_hash, idempotency_key } })
  if (!data) fail(error)
  return data.data
}
export async function loadSweep(sweep_id: string) {
  const { data, error } = await api.GET('/api/v2/sweeps/{sweep_id}', { params: { path: { sweep_id } } })
  if (!data) fail(error)
  return data.data
}
export async function loadSweeps(offset = 0) {
  const { data, error } = await api.GET('/api/v2/sweeps', { params: { query: { offset, limit: 20 } } })
  if (!data) fail(error)
  return data.data
}
export async function cancelSweep(sweep_id: string) {
  const { data, error } = await api.POST('/api/v2/sweeps/{sweep_id}/cancel', { params: { path: { sweep_id } } })
  if (!data) fail(error)
  return data.data
}
