/** Phase 8 API-only facade. No generated scientific data or fallback provider. */
import { api } from '../services/api'
import type { components } from '../types/generated/api'
import type { Loaded } from './domain'

export type Science = components['schemas']
export type Sector = Science['SectorAllocation']
export type Region = Science['RegionAllocation']
export type Definitions = Science['ScientificDefinition'][]
export type AllocationBundle = {
  overview: Science['CylinderAllocationOverview']; definitions: Definitions
  edges: number[]; channels: { channel: string; values: number[] }[]
}
type CompleteSeries = Omit<Science['ScalarSeries'], 'page'> & { source_pages: Science['PageWindow'][] }
export type HistoryBundle = { history: Omit<Science['EntropyHistory'], 'series'> & { series: CompleteSeries[] }; definitions: Definitions }
export type MetricsBundle = { collection: Science['MetricCollection']; definitions: Definitions }
export type FieldBundle = { field: Science['FieldDescriptor']; values: number[]; definitions: Definitions }

export function known<T>(fact: { state: string; value?: T }): T | null {
  return fact.state === 'KNOWN' ? fact.value ?? null : null
}
export function slotValue<T>(slot: { availability: string; value?: T }): T | null {
  return ['AVAILABLE', 'PARTIAL'].includes(slot.availability) ? slot.value ?? null : null
}
class Failure extends Error {
  constructor(public state: 'ERROR' | 'MISSING' | 'UNSUPPORTED', message: string) { super(message) }
}
async function body<T>(request: Promise<{ data?: unknown; error?: unknown; response: Response }>): Promise<T> {
  const response = await request
  const envelope = (response.data ?? response.error) as { data?: T; availability?: string; error?: Science['ErrorBody'] }
  if (!response.response.ok || !envelope?.data) {
    throw new Failure(envelope?.availability === 'MISSING' ? 'MISSING' : envelope?.availability === 'UNSUPPORTED' ? 'UNSUPPORTED' : 'ERROR',
      envelope?.error?.message ?? `API request failed (${response.response.status})`)
  }
  // Check every scientific child, including composite children and array owners.
  const visit = (node: unknown): void => {
    if (!node || typeof node !== 'object') return
    if ('data_origin' in node && ['MOCK', 'SCHEMATIC', 'LIVE_DEMO'].includes(String(node.data_origin))) throw new Error('API returned non-production science')
    Object.values(node).forEach(visit)
  }
  visit(envelope.data)
  return envelope.data
}
async function load<T>(task: () => Promise<T>): Promise<Loaded<T>> {
  try { return { state: 'READY', data: await task(), reason: null, origin: 'VERIFIED_PRODUCTION' } }
  catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    return { state: error instanceof Failure ? error.state : 'ERROR', data: null, reason: (error as Error).message, origin: 'VERIFIED_PRODUCTION' }
  }
}
async function definitions(ids: string[], signal?: AbortSignal): Promise<Definitions> {
  const records = await Promise.all([...new Set(ids)].filter(id => id.startsWith('ev.')).map(evidence_id =>
    body<Science['EvidenceRecord']>(api.GET('/api/v1/evidence/{evidence_id}', { params: { path: { evidence_id } }, signal }))))
  return [...new Map(records.flatMap(record => record.definitions).map(item => [item.id, item])).values()]
}
function identity(result: Science['ScientificResult'], config: string, experiment = 'cylinder') {
  if (result.config_id !== config || result.experiment_id !== experiment) throw new Error('Scientific result identity mismatch')
}
async function array(ref: Science['ArrayRef'], signal?: AbortSignal): Promise<number[]> {
  const value = await body<Science['ScientificArray']>(api.GET('/api/v1/results/{result_id}/arrays/{array_id}', {
    params: { path: { result_id: ref.result_id, array_id: ref.descriptor.array_id } }, signal }))
  if (value.result.result_id !== ref.result_id || JSON.stringify(value.descriptor) !== JSON.stringify(ref.descriptor)
    || value.values.length !== ref.descriptor.element_count || value.values.some(v => typeof v !== 'number' || !Number.isFinite(v))) {
    throw new Error('Scientific array identity/descriptor mismatch')
  }
  return value.values as number[]
}
export const cylinderService = {
  snapshots: (config_id: string, signal?: AbortSignal) => load(async () => {
    const index = await body<Science['SnapshotIndex']>(api.GET('/api/v1/experiments/cylinder/configs/{config_id}/snapshots', { params: { path: { config_id } }, signal }))
    if (index.config_id !== config_id || index.experiment_id !== 'cylinder' || index.snapshot_count !== 5 || index.items.length !== 5
      || index.items.some((s, i) => s.snapshot_index !== i + 1)) throw new Error('Cylinder recorded snapshot index mismatch')
    index.items.forEach(s => { identity(s.result, config_id); s.fields.forEach(f => identity(f.result, config_id)) })
    return index
  }),
  field: (config_id: string, snapshot_index: number, field_id: string, signal?: AbortSignal) => load<FieldBundle>(async () => {
    const response = await body<Science['FieldResponse']>(api.GET('/api/v1/experiments/cylinder/configs/{config_id}/snapshots/{snapshot_index}/fields/{field_id}', {
      params: { path: { config_id, snapshot_index, field_id } }, signal }))
    identity(response.field.result, config_id)
    if (response.snapshot.snapshot_index !== snapshot_index || response.field.field_id !== field_id
      || response.field.result.time.accumulation !== 'NONE') throw new Error('Instantaneous field context mismatch')
    const [values, defs] = await Promise.all([array(response.field.array_ref, signal), definitions(response.field.result.provenance.evidence_refs, signal)])
    return { field: response.field, values, definitions: defs }
  }),
  history: (config_id: string, signal?: AbortSignal) => load<HistoryBundle>(async () => {
    const page = (offset: number) => body<Science['EntropyHistory']>(api.GET('/api/v1/experiments/cylinder/configs/{config_id}/entropy-history', {
      params: { path: { config_id }, query: { series: ['E_bg_cumulative', 'E_aa_cumulative', 'E_at_cumulative', 'E_total_cumulative'], offset, limit: 5000 } }, signal }))
    const first = await page(0)
    if (first.series.length !== 4 || first.series.some(s => s.total_point_count !== 9757)) throw new Error('Cylinder scalar history count mismatch')
    const second = await page(5000)
    if (first.config_id !== config_id || second.config_id !== config_id || second.series.length !== first.series.length) throw new Error('History identity mismatch')
    const complete: CompleteSeries[] = []
    for (const series of first.series) {
      identity(series.result, config_id)
      const tail = second.series.find(s => s.series_id === series.series_id)
      if (!tail || tail.result.result_id !== series.result.result_id || tail.definition_id !== series.definition_id
        || tail.total_point_count !== 9757 || tail.page.offset !== 5000 || tail.page.has_more) throw new Error('Scalar page context mismatch')
      const points = [...series.points, ...tail.points]
      if (points.length !== 9757 || points.some((p, i) => p.point_index !== i || known(p.step_index) !== i + 1
        || known(p.source_step_index) !== i || known(p.physical_time) === null || known(p.value) === null)) throw new Error('Scalar record continuity mismatch')
      const { page: sourcePage, ...context } = series
      complete.push({ ...context, points, source_pages: [sourcePage, tail.page] })
    }
    return { history: { ...first, series: complete }, definitions: await definitions(first.evidence_refs, signal) }
  }),
  allocation: (config_id: string, signal?: AbortSignal) => load<AllocationBundle>(async () => {
    const overview = await body<Science['CylinderAllocationOverview']>(api.GET('/api/v1/experiments/cylinder/configs/{config_id}/allocation', { params: { path: { config_id } }, signal }))
    if (overview.config_id !== config_id || overview.cumulative_2d.availability !== 'MISSING') throw new Error('Cylinder allocation capability mismatch')
    const sectors = slotValue(overview.sectors)
    const band = slotValue(overview.front_band)
    if (sectors) identity(sectors.result, config_id)
    if (band) identity(band.result, config_id)
    if (sectors && (sectors.representation_type !== 'ANGULAR_SECTORS' || sectors.sector_count !== 16)) throw new Error('Expected 16 native angular sectors')
    if (band && band.representation_type !== 'REGION_SCALAR') throw new Error('Expected front-band REGION_SCALAR')
    const native = sectors?.representation_type === 'ANGULAR_SECTORS' ? sectors : null
    const [edges, channels, defs] = await Promise.all([
      native ? array(native.bin_edges, signal) : Promise.resolve([]),
      native ? Promise.all(native.channel_arrays.map(async c => ({ channel: c.channel, values: await array(c.array_ref, signal) }))) : Promise.resolve([]),
      definitions(overview.evidence_refs, signal),
    ])
    return { overview, edges, channels, definitions: defs }
  }),
  metrics: (config_id: string, signal?: AbortSignal) => load<MetricsBundle>(async () => {
    const collection = await body<Science['MetricCollection']>(api.GET('/api/v1/experiments/cylinder/configs/{config_id}/metrics', { params: { path: { config_id } }, signal }))
    if (collection.config_id !== config_id || collection.experiment_id !== 'cylinder') throw new Error('Metric collection identity mismatch')
    return { collection, definitions: await definitions(collection.evidence_refs, signal) }
  }),
  comparison: (case8_config: string, cylinder_config: string, signal?: AbortSignal) => load(async () => {
    const comparison = await body<Science['CrossFlowComparison']>(api.GET('/api/v1/comparisons/case8-cylinder', { params: { query: { case8_config, cylinder_config } }, signal }))
    if (comparison.left.config_id !== case8_config || comparison.right.config_id !== cylinder_config
      || comparison.left.experiment_id !== 'case8' || comparison.right.experiment_id !== 'cylinder'
      || comparison.ranking_policy !== 'NO_UNIFIED_RANKING') throw new Error('Comparison identity/policy mismatch')
    const refs = [comparison.left, comparison.right].flatMap(side => [slotValue(side.metrics), slotValue(side.budget)].flatMap(c => c?.evidence_refs ?? []))
    return { comparison, definitions: await definitions(refs, signal) }
  }),
}
