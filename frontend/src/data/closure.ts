/** CLO01–05 only. Preserve canonical values, pages, clocks and definitions. */
import { api } from '../services/api'
import type { components } from '../types/generated/api'
import type { Loaded } from './domain'
export { known, slotValue } from './cylinder'
import { known } from './cylinder'
export type Science = components['schemas']
export type ClosureRun = Science['EntropyClosureRun']
export type HistoryBundle = { history: Science['ClosureHistory']; definitions: Science['ScientificDefinition'][] }
export type Refinement = Science['RefinementSummary']
export const PAGE_SIZE = 1000
class Failure extends Error {
  constructor(public state: 'ERROR' | 'MISSING' | 'UNSUPPORTED', message: string) { super(message) }
}
async function body<T>(request: Promise<{ data?: unknown; error?: unknown; response: Response }>): Promise<T> {
  const response = await request
  const envelope = (response.data ?? response.error) as { data?: T; availability?: string; error?: Science['ErrorBody'] }
  if (!response.response.ok || !envelope?.data) throw new Failure(
    envelope?.availability === 'MISSING' ? 'MISSING' : envelope?.availability === 'UNSUPPORTED' ? 'UNSUPPORTED' : 'ERROR',
    envelope?.error?.message ?? `API request failed (${response.response.status})`)
  const visit = (node: unknown): void => {
    if (!node || typeof node !== 'object') return
    if ('data_origin' in node && node.data_origin !== 'FROZEN_PRODUCTION' && node.data_origin !== 'VERIFIED_PRODUCTION') throw new Error('API returned non-production science')
    Object.values(node).forEach(visit)
  }
  visit(envelope.data)
  return envelope.data
}
async function load<T>(task: () => Promise<T>): Promise<Loaded<T>> {
  try { return { state: 'READY', data: await task(), reason: null, origin: 'FROZEN_PRODUCTION' } }
  catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    return { state: error instanceof Failure ? error.state : 'ERROR', data: null, reason: (error as Error).message, origin: 'FROZEN_PRODUCTION' }
  }
}
async function history(run: ClosureRun, granularity: 'PER_STAGE' | 'PER_STEP', offset: number, limit: number, signal?: AbortSignal) {
  const path = granularity === 'PER_STAGE'
    ? '/api/v1/experiments/entropy-closure/runs/{run_id}/stage-history'
    : '/api/v1/experiments/entropy-closure/runs/{run_id}/step-history'
  const value = await body<Science['ClosureHistory']>(api.GET(path, { params: { path: { run_id: run.run_id }, query: { offset, limit } }, signal }))
  const count = granularity === 'PER_STAGE' ? run.stage_point_count : run.step_point_count
  const refs = granularity === 'PER_STAGE' ? run.stage_series_refs : run.step_series_refs
  if (value.run_id !== run.run_id || value.granularity !== granularity || value.series.length !== refs.length) throw new Error('Closure history identity mismatch')
  for (const series of value.series) {
    if (!refs.includes(series.result.result_id) || series.result.experiment_id !== 'entropy-closure' || series.result.config_id !== run.run_id || series.result.time.sampling !== granularity
      || series.total_point_count !== count || series.page.total_count !== count || series.page.offset !== offset
      || series.page.returned_count !== series.points.length || series.points.length !== Math.min(limit, count - offset)
      || series.page.has_more !== (offset + series.points.length < count)) throw new Error('Closure page context mismatch')
    series.points.forEach((point, i) => {
      const ordinal = offset + i
      const step = granularity === 'PER_STAGE' ? Math.floor(ordinal / 3) + 1 : ordinal + 1
      if (point.point_index !== ordinal || known(point.step_index) !== step || known(point.source_step_index) !== step
        || known(point.value) === null || !Number.isFinite(known(point.value)) || known(point.physical_time) === null
        || (granularity === 'PER_STAGE' && (known(point.stage_index) !== ordinal % 3 || known(point.source_stage_index) !== ordinal % 3 + 1))) throw new Error('Closure record continuity mismatch')
    })
  }
  return value
}
export function runLabel(run: ClosureRun) { return run.config.name.replace(' CFL ', ' — CFL ') }
export const closureService = {
  runs: (signal?: AbortSignal) => load(async () => {
    const registry = await body<Science['ClosureRunRegistry']>(api.GET('/api/v1/experiments/entropy-closure/runs', { signal }))
    if (registry.experiment_id !== 'entropy-closure' || registry.runs.length !== 5 || new Set(registry.runs.map(r => r.run_id)).size !== 5
      || registry.runs.some(r => r.config.id !== r.run_id || r.config.experiment_id !== 'entropy-closure' || r.stage_point_count !== 3 * r.step_point_count)) throw new Error('Closure five-run registry mismatch')
    return registry
  }),
  history: (run: ClosureRun, granularity: 'PER_STAGE' | 'PER_STEP', offset: number, signal?: AbortSignal) => load<HistoryBundle>(async () => {
    const value = await history(run, granularity, offset, PAGE_SIZE, signal)
    const records = await Promise.all(value.evidence_refs.map(evidence_id => body<Science['EvidenceRecord']>(api.GET('/api/v1/evidence/{evidence_id}', { params: { path: { evidence_id } }, signal }))))
    const definitions = records.flatMap(r => r.definitions)
    if (value.series.some(s => !definitions.some(d => d.id === s.definition_id))) throw new Error('Closure definition unavailable')
    return { history: value, definitions }
  }),
  refinement: (signal?: AbortSignal) => load(async () => {
    const summary = await body<Refinement>(api.GET('/api/v1/experiments/entropy-closure/refinement', { signal }))
    if (summary.run_ids.length !== 4 || new Set(summary.run_ids).size !== 4 || summary.metrics_by_run.length !== 4
      || summary.metrics_by_run.some((r, i) => r.run_id !== summary.run_ids[i])) throw new Error('Closure four-point refinement identity mismatch')
    for (const run of summary.metrics_by_run) for (const field of ['R_total', 'dt_eff']) {
      const slot = run.metrics.find(s => 'value' in s && s.value.metric_id === field)
      if (!slot || !('value' in slot) || slot.value.result.config_id !== run.run_id
        || slot.value.result.experiment_id !== 'entropy-closure' || slot.value.result.time.sampling !== 'TERMINAL'
        || known(slot.value.value) === null || !Number.isFinite(known(slot.value.value))) throw new Error('Closure refinement terminal metric unavailable')
    }
    return summary
  }),
  evidence: (run: ClosureRun, signal?: AbortSignal) => load(async () => {
    const [stage, step] = await Promise.all([history(run, 'PER_STAGE', 0, 1, signal), history(run, 'PER_STEP', 0, 1, signal)])
    return { stage: stage.evidence_refs, step: step.evidence_refs }
  }),
}
