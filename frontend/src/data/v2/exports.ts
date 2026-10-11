import { api } from '../../services/api'
import type { components } from '../../types/generated/api'
import { ExperimentApiError } from './experiments'

export type ExportKind = 'raw' | 'visualization' | 'report'
export type ReportFormat = 'zip' | 'html' | 'pdf'
export type ExportStatus = components['schemas']['RunExports']
export type ExportMetadata = components['schemas']['ExportMetadata']

export async function loadExports(run_id: string, signal?: AbortSignal) {
  const { data, error } = await api.GET('/api/v2/runs/{run_id}/exports', { params: { path: { run_id } }, signal })
  if (!data) throw new ExperimentApiError(error?.error.message ?? '导出服务不可用，请重试。', [], error?.error.code)
  return data.data
}

export async function generateExport(run_id: string, kind: ExportKind, format: ReportFormat, signal?: AbortSignal) {
  const { data, error } = await api.POST('/api/v2/runs/{run_id}/exports/{kind}', {
    params: { path: { run_id, kind }, query: { format } }, signal,
  })
  if (!data) throw new ExperimentApiError(error?.error.message ?? '导出生成失败，请重试。', [], error?.error.code)
  return data.data
}

export async function downloadExport(runId: string, kind: ExportKind, format: ReportFormat, signal?: AbortSignal) {
  let response: Response
  try {
    response = await fetch(`/api/v2/runs/${encodeURIComponent(runId)}/exports/${kind}/download?format=${format}`, { signal })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new Error('文件下载失败，连接已中断；可重试下载。')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => undefined)
    throw new Error(`文件下载失败：${data?.error?.message ?? '服务暂不可用，请重试。'}`)
  }
  const expected = { zip: 'application/zip', html: 'text/html', pdf: 'application/pdf' }[format]
  if (response.headers.get('Content-Type')?.split(';')[0] !== expected) throw new Error('文件下载失败：服务返回了错误的文件格式。')
  let blob: Blob
  try { blob = await response.blob() }
  catch (error) { if (signal?.aborted) throw error; throw new Error('文件下载失败：传输中断，请重试。') }
  const length = response.headers.get('Content-Length')
  if (!blob.size || (length !== null && blob.size !== Number(length))) throw new Error('文件下载失败：文件为空或未完整传输。')
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError')
  const names = { raw: 'raw_data.zip', visualization: 'flow_field.zip', report: 'experiment_report.zip' }
  const filename = format === 'zip' ? `ShockPath_${runId}_${names[kind]}` : `ShockPath_${runId}_report.${format}`
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url; link.download = filename
  document.body.append(link); link.click(); link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}
