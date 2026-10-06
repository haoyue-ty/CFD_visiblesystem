import { api } from '../../services/api'
import type { components } from '../../types/generated/api'
import { ExperimentApiError, type LiveConfig, type Submission } from './experiments'

export type RunRecord = Awaited<ReturnType<typeof loadRun>>
export type RunDensity = Awaited<ReturnType<typeof loadDensity>>
export type RunStatus = RunRecord['status']
export const terminal = (status: RunStatus) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(status)
export const statusLabels: Record<RunStatus, string> = {
  QUEUED: '排队中', STARTING: '正在启动', RUNNING: '正在求解', POSTPROCESSING: '后处理',
  COMPLETED: '已完成', FAILED: '失败', CANCELLED: '已取消',
}
function fail(error: components['schemas']['V2FailedEnvelope'] | undefined): never {
  throw new ExperimentApiError(error?.error.message ?? '运行服务连接失败，请重试。', error?.error.details ?? [], error?.error.code)
}
export async function createRun(config: LiveConfig, submission: Submission, confirmed_config_hash: string, idempotency_key: string) {
  const { data, error } = await api.POST('/api/v2/runs', { body: { config, submission, confirmed_config_hash, idempotency_key } })
  if (!data) fail(error)
  return data.data
}
export async function loadRuns(offset = 0, status?: RunStatus) {
  const { data, error } = await api.GET('/api/v2/runs', { params: { query: { offset, limit: 20, status } } })
  if (!data) fail(error)
  return data.data
}
export async function loadRun(run_id: string) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}', { params: { path: { run_id } } })
  if (!data) fail(error)
  return data.data
}
export async function cancelRun(run_id: string) {
  const { data, error } = await api.POST('/api/v2/runs/{run_id}/cancel', { params: { path: { run_id } } })
  if (!data) fail(error)
  return data.data
}
export async function loadRunHistory(run_id: string, offset = 0) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/history', { params: { path: { run_id }, query: { offset, limit: 5 } } })
  if (!data) fail(error)
  return data.data
}
export async function loadDensity(run_id: string) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/snapshots', { params: { path: { run_id } } })
  if (!data) fail(error)
  const last = data.data.snapshots.at(-1)
  if (!last) throw new ExperimentApiError('终态快照不可用。')
  const response = await api.GET('/api/v2/runs/{run_id}/snapshot/{snapshot_id}', {
    params: { path: { run_id, snapshot_id: last.snapshot_id } },
  })
  if (!response.data) fail(response.error)
  return response.data.data
}

export async function loadScientificResult(run_id: string) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/result', { params: { path: { run_id } } })
  if (!data) fail(error)
  return data.data
}
export async function loadRunEvidence(run_id: string) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/evidence', { params: { path: { run_id } } })
  if (!data) fail(error)
  return data.data
}
export async function loadSnapshots(run_id: string) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/snapshots', { params: { path: { run_id } } })
  if (!data) fail(error)
  return data.data.snapshots
}
export type FieldName = components['schemas']['FieldDefinition']['field_id']
export async function loadRunField(run_id: string, snapshot_id: string, field: FieldName) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/snapshot/{snapshot_id}/field', {
    params: { path: { run_id, snapshot_id }, query: { field } },
  })
  if (!data) fail(error)
  return data.data
}
export async function loadRunFaces(run_id: string, snapshot_id: string) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/snapshot/{snapshot_id}/faces', { params: { path: { run_id, snapshot_id } } })
  if (!data) fail(error)
  return data.data
}
export type Region = { x_min: number; x_max: number; y_min: number; y_max: number }
export async function loadViewContext(run_id: string, snapshot_id: string, field: FieldName, region?: Region) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/snapshot/{snapshot_id}/view-context', {
    params: { path: { run_id, snapshot_id }, query: { field, ...region } },
  })
  if (!data) fail(error)
  return data.data
}
