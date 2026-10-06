import { api } from '../../services/api'
import type { components } from '../../types/generated/api'

export type LiveCase = Awaited<ReturnType<typeof loadCases>>['cases'][number]
export type LiveConfig = LiveCase['templates'][number]['config']
export type Validated = Awaited<ReturnType<typeof validateConfig>>
export type Draft = Awaited<ReturnType<typeof parseNaturalLanguage>>
export type Submission = components['schemas']['Input_ExperimentSubmission']
export type FieldIssue = components['schemas']['V2FieldIssue']

export class ExperimentApiError extends Error {
  constructor(message: string, public details: FieldIssue[] = [], public code = 'NETWORK_ERROR') { super(message) }
}

function failure(error: components['schemas']['V2FailedEnvelope'] | undefined): never {
  throw new ExperimentApiError(error?.error.message ?? '请求失败，请重试。', error?.error.details ?? [], error?.error.code)
}

export async function loadCases() {
  try {
    const { data, error } = await api.GET('/api/v2/cases')
    if (!data) failure(error)
    return data.data
  } catch (error) {
    if (error instanceof ExperimentApiError) throw error
    throw new ExperimentApiError('无法连接实验配置服务，请检查后端并重试。')
  }
}

export async function validateConfig(config: LiveConfig, submission: Submission) {
  try {
    const { data, error } = await api.POST('/api/v2/experiments/validate', { body: { config, submission } })
    if (!data) failure(error)
    return data.data
  } catch (error) {
    if (error instanceof ExperimentApiError) throw error
    throw new ExperimentApiError('配置校验连接失败，请重试。')
  }
}

export async function parseNaturalLanguage(text: string, capability_revision: string) {
  try {
    const { data, error } = await api.POST('/api/v2/experiments/parse-natural-language', { body: { text, capability_revision } })
    if (!data) failure(error)
    return data.data
  } catch (error) {
    if (error instanceof ExperimentApiError) throw error
    throw new ExperimentApiError('自然语言服务连接失败，请重试或使用专业参数。')
  }
}
