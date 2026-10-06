import { api } from '../../services/api'
import { ExperimentApiError } from './experiments'

export async function generateReport(run_id: string) {
  const { data, error } = await api.POST('/api/v2/reports/{run_id}', { params: { path: { run_id } } })
  if (!data) throw new ExperimentApiError(error?.error.message ?? '报告生成失败，请重试。')
  return data.data
}
export async function loadReport(run_id: string) {
  const { data, error } = await api.GET('/api/v2/reports/{run_id}', { params: { path: { run_id } } })
  if (!data) throw new ExperimentApiError(error?.error.message ?? '报告服务连接失败，请重试。')
  return data.data
}
export async function saveReport(run_id: string) {
  const response = await api.GET('/api/v2/reports/{run_id}/html', { params: { path: { run_id } }, parseAs: 'text' })
  if (!response.data) throw new ExperimentApiError('报告下载失败，请重新生成报告后重试。')
  const url = URL.createObjectURL(new Blob([response.data], { type: 'text/html;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url; link.download = `ShockPath-${run_id}.html`; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
