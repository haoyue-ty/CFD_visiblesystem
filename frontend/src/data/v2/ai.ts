import { api } from '../../services/api'
import type { components } from '../../types/generated/api'
import { ExperimentApiError } from './experiments'

export type AIAnalysis = components['schemas']['AIAnalysis']
export type AIClaim = components['schemas']['AIClaim']
export type AIView = components['schemas']['Input_AIChatRequest']['view']
export async function interpretRun(run_id: string) {
  const { data, error } = await api.POST('/api/v2/ai/runs/{run_id}/interpret', { params: { path: { run_id } } })
  if (!data) throw new ExperimentApiError(error?.error.message ?? '解读请求失败，请重试。', [], error?.error.code)
  return data.data
}
export async function askRun(run_id: string, message: string, view: AIView) {
  const { data, error } = await api.POST('/api/v2/ai/chat', { body: { run_id, message, view } })
  if (!data) throw new ExperimentApiError(error?.error.message ?? '问答请求失败，请重试。', [], error?.error.code)
  return data.data
}
