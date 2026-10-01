/** Real API transport; all scientific DTOs come from generated OpenAPI types. */
import { api } from '../services/api'
import type { components } from '../types/generated/api'
import type { DataProvider } from './provider'
import type { FieldMeta, Loaded, MetricView, UnitSpec, ResultHeader, EvidenceDetailView } from './domain'

type S = components['schemas']
type Fact<T> = (Omit<Extract<S['UnitSpec']['si_mapping'], { state: 'KNOWN' }>, 'value'> & { value: T }) | S['UnresolvedFact']
export function factValue<T>(fact: Fact<T>): T | null { return fact.state === 'KNOWN' ? fact.value : null }
function requiredFact<T>(fact: Fact<T>): T {
  if (fact.state !== 'KNOWN') throw new Error(`Recorded value unavailable: ${fact.reason}`)
  return fact.value
}
const unit = (value: S['UnitSpec']): UnitSpec => ({ ...value, si_mapping: factValue(value.si_mapping) })
function header(result: S['ScientificResult']): ResultHeader {
  if (['MOCK', 'SCHEMATIC', 'LIVE_DEMO'].includes(result.data_origin)) throw new Error('Real API returned a non-production result')
  return { ...result, unit: unit(result.unit), evidence_refs: result.provenance.evidence_refs }
}
function fieldMeta(field: S['FieldDescriptor']): FieldMeta {
  const extent = (axis: string): [number, number] => {
    const item = field.domain.extent.find(item => item.axis === axis)
    if (!item) throw new Error(`Recorded ${axis} extent unavailable`)
    return [item.lower, item.upper]
  }
  return { field_id: field.field_id, label: field.label, unit_label: field.result.unit.label,
    shape: field.array_ref.descriptor.shape, axes: field.array_ref.descriptor.axes,
    extent: { x: extent('x'), y: extent('y') }, verification_status: field.result.verification.status,
    result: header(field.result) }
}
function snapshot(row: S['FieldSnapshot']) {
  return { snapshot_index: row.snapshot_index, snapshot_id: row.snapshot_id,
    step_index: row.step_index, physical_time: row.physical_time, fields: row.fields.map(fieldMeta) }
}
class ApiFailure extends Error {
  constructor(public readonly state: 'MISSING' | 'UNSUPPORTED' | 'ERROR', message: string) { super(message) }
}
async function body<T>(request: Promise<{ data?: unknown; error?: unknown; response: Response }>): Promise<T> {
  const response = await request
  const envelope = (response.data ?? response.error) as { availability?: string; data?: T; error?: S['ErrorBody'] }
  if (!response.response.ok || !envelope || !('data' in envelope)) {
    const state = envelope?.availability === 'MISSING' ? 'MISSING' : envelope?.availability === 'UNSUPPORTED' ? 'UNSUPPORTED' : 'ERROR'
    throw new ApiFailure(state, envelope?.error?.message ?? `API request failed (${response.response.status})`)
  }
  return envelope.data as T
}
async function load<T>(task: () => Promise<T>): Promise<Loaded<T>> {
  try { return { state: 'READY', data: await task(), reason: null, origin: 'VERIFIED_PRODUCTION' } }
  catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    return { state: error instanceof ApiFailure ? error.state : 'ERROR', data: null,
      reason: String(error instanceof Error ? error.message : error), origin: 'VERIFIED_PRODUCTION' }
  }
}
async function evidence(id: string, signal?: AbortSignal): Promise<S['EvidenceRecord']> {
  return body(api.GET('/api/v1/evidence/{evidence_id}', { params: { path: { evidence_id: id } }, signal }))
}
function evidenceView(record: S['EvidenceRecord'], config: S['ExperimentConfig'] | null): EvidenceDetailView {
  return { evidence_id: record.evidence_id, schema_version: record.schema_version,
    supports: record.definitions.map(item => item.definition).join('; ') || 'Recorded source provenance',
    does_not_support: ['Only the referenced recorded results are supported', ...record.limitations.map(item => item.description)].join('; '),
    experiment_id: factValue(record.experiment_id), config_id: factValue(record.config_id),
    config_parameters: (config?.parameters ?? []).map(item => ({ name: item.name, value: factValue(item.value)?.toString() ?? 'UNKNOWN' })),
    method_name: factValue(record.method_name), method_hash: factValue(record.method_hash),
    recorded_source_hash: factValue(record.recorded_source_hash), current_source_hash: factValue(record.current_source_hash),
    data_hash: factValue(record.data_hash), verification: record.verification, source_drift: factValue(record.source_drift),
    source_assets: record.source_assets.map(item => ({ asset_id: item.asset_id, source_display: item.source_display,
      role: item.role, recorded_hash: factValue(item.recorded_data_hash), current_hash: factValue(item.current_data_hash),
      drift: factValue(item.data_drift), verification: item.verification })),
    related_result_ids: record.result_ids, limitations: record.limitations,
    freeze_id: factValue(record.freeze_reference)?.freeze_id ?? null,
    data_origin: record.result_contexts[0]?.data_origin ?? 'VERIFIED_PRODUCTION' }
}

export function createApiProvider(): DataProvider {
  return {
    kind: 'API', originLabel: 'REAL API',
    getProject: signal => load(async () => {
      const project = await body<S['ProjectInfo']>(api.GET('/api/v1/system', { signal }))
      return { project_id: project.project_id, name: project.name, tagline: 'Recorded scientific replay',
        scientific_question: 'What triggers numerical dissipation and how does it affect the flow?',
        mechanism_chain: ['Trigger', 'Dissipation', 'Flow response'],
        registry_revision: project.registry_revision, data_revision: project.data_revision }
    }),
    listExperiments: signal => load(async () => {
      const catalog = await body<S['ExperimentList']>(api.GET('/api/v1/experiments', { signal }))
      return catalog.items.map(item => ({ experiment_id: item.id, name: item.name,
        scientific_family: item.scientific_family, summary: item.description, delivery_status: item.delivery_status,
        availability_note: item.delivery_status === 'IMPLEMENTED' ? 'Recorded real data' : null,
        implementable_route: item.delivery_status === 'IMPLEMENTED' ? `/lab/experiments/${item.id}` : null }))
    }),
    getExperimentOverview: (experimentId, signal) => load(async () => {
      const experiment = await body<S['Experiment']>(api.GET('/api/v1/experiments/{experiment_id}', { params: { path: { experiment_id: experimentId } }, signal }))
      const config = experiment.available_configs[0]
      if (!config) throw new Error('Registered configuration metadata unavailable')
      const [frames, history] = await Promise.all([
        body<S['SnapshotIndex']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/snapshots', { params: { path: { config_id: config.id } }, signal })),
        body<S['EntropyHistory']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/entropy-history', { params: { path: { config_id: config.id }, query: { series: ['E_at_cumulative'], limit: 1 } }, signal })),
      ])
      const grid = factValue(config.protocol.grid)
      return { experiment_id: experiment.id, name: experiment.name, description: experiment.description,
        delivery_status: experiment.delivery_status,
        configurations: experiment.available_configs.map(item => ({ config_id: item.id as 'A_u' | 'B_u' | 'C_u' | 'D_u', name: item.name,
          q_aa: requiredFact(item.parameters.find(item => item.name === 'q_aa')!.value) as number,
          q_at: requiredFact(item.parameters.find(item => item.name === 'q_at')!.value) as number })),
        default_config: 'D_u', snapshot_count: frames.snapshot_count, scalar_step_count: history.series[0].total_point_count,
        protocol: { method_name: factValue(config.protocol.method_name), integrator: factValue(config.protocol.integrator),
          reconstruction: factValue(config.protocol.reconstruction), final_time: factValue(config.protocol.final_time),
          grid: grid?.dimensions.map(item => `${item.size} (${item.axis})`).join(' × ') ?? null },
        limitation: experiment.limitations[0] ?? null }
    }),
    listSnapshots: (configId, signal) => load(async () => {
      const index = await body<S['SnapshotIndex']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/snapshots', { params: { path: { config_id: configId } }, signal }))
      return index.items.map(snapshot)
    }),
    getSnapshotField: (selector, signal) => load(async () => {
      const response = await body<S['FieldResponse']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/snapshots/{snapshot_index}/fields/{field_id}', {
        params: { path: { config_id: selector.configId, snapshot_index: selector.snapshotIndex, field_id: selector.fieldId } }, signal }))
      const ref = response.field.array_ref
      const array = await body<S['ScientificArray']>(api.GET('/api/v1/results/{result_id}/arrays/{array_id}', { params: { path: { result_id: ref.result_id, array_id: ref.descriptor.array_id } }, signal }))
      if (array.result.result_id !== ref.result_id || array.values.some(value => typeof value !== 'number')) throw new Error('Array identity/type mismatch')
      return { meta: fieldMeta(response.field), values: array.values as number[], data_origin: header(array.result).data_origin }
    }),
    getEntropyHistory: (configId, signal) => load(async () => {
      const history = await body<S['EntropyHistory']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/entropy-history', {
        params: { path: { config_id: configId }, query: { series: ['E_bg_cumulative', 'E_aa_cumulative', 'E_at_cumulative'], limit: 2000 } }, signal }))
      return { experiment_id: history.experiment_id, config_id: history.config_id, limitations: history.limitations,
        total_point_count: history.series[0].total_point_count,
        series: history.series.map(series => ({ series_id: series.series_id, label: series.label, aggregation: series.aggregation,
          unit: unit(series.result.unit), definition_id: series.definition_id, data_origin: header(series.result).data_origin,
          verification: series.result.verification, result: header(series.result),
          points: series.points.map(point => ({ point_index: point.point_index, step_index: requiredFact(point.step_index),
            source_step_index: requiredFact(point.source_step_index), physical_time: requiredFact(point.physical_time), value: requiredFact(point.value) })) })) }
    }),
    getSnapshotAlignment: (configId, step, policy, pinnedIndex, signal) => load(() => body<S['SnapshotAlignment']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/snapshot-alignment', {
      params: { path: { config_id: configId }, query: { scalar_step: step, policy, ...(policy === 'PINNED' ? { snapshot_index: pinnedIndex } : {}) } }, signal }))),
    getMetrics: (configId, signal) => load(async () => {
      const collection = await body<S['MetricCollection']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/metrics', { params: { path: { config_id: configId } }, signal }))
      const definitions = (await evidence(collection.evidence_refs[0], signal)).definitions
      const items: MetricView[] = collection.items.map((slot, index) => {
        if (!('value' in slot)) return { metric_id: slot.error.target.identity.state === 'KNOWN' ? slot.error.target.identity.value : `unavailable-${index}`,
          display_label: 'Unavailable metric', value: null, unit: { id: 'unknown', system: 'UNKNOWN', quantity: 'unknown', label: 'UNKNOWN', si_mapping: null },
          definition_id: 'unknown', definition_text: 'Unavailable', detector_scope: 'UNKNOWN', time_scope_label: 'UNKNOWN',
          resolution_limit: null, evidence_refs: slot.error.evidence_refs, availability: slot.availability, unavailable_reason: slot.error.message }
        const metric = slot.value
        const definition = definitions.find(item => item.id === metric.definition_id)
        const value = factValue(metric.value)
        return { metric_id: metric.metric_id, display_label: metric.display_label, value, unit: unit(metric.result.unit),
          definition_id: metric.definition_id, definition_text: definition?.definition ?? 'Definition unavailable',
          detector_scope: `${factValue(metric.detector)?.definition ?? 'UNKNOWN'}; ${definition?.spatial_rule ?? metric.result.scope.description}`,
          time_scope_label: `${metric.time_scope.sampling}; ${metric.time_scope.accumulation}; snapshot ${factValue(metric.time_scope.snapshot_index) ?? 'UNKNOWN'}; t=${factValue(metric.time_scope.physical_time) ?? 'UNKNOWN'}`,
          resolution_limit: factValue(metric.resolution_limit), evidence_refs: metric.result.provenance.evidence_refs,
          availability: value === null ? 'MISSING' : slot.availability,
          unavailable_reason: metric.value.state === 'KNOWN' ? null : metric.value.reason }
      })
      return { experiment_id: collection.experiment_id, config_id: collection.config_id, items }
    }),
    listEvidenceForConfig: (configId, signal) => load(async () => {
      const [frames, history, metrics] = await Promise.all([
        body<S['SnapshotIndex']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/snapshots', { params: { path: { config_id: configId } }, signal })),
        body<S['EntropyHistory']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/entropy-history', { params: { path: { config_id: configId }, query: { limit: 1 } }, signal })),
        body<S['MetricCollection']>(api.GET('/api/v1/experiments/case8/configs/{config_id}/metrics', { params: { path: { config_id: configId } }, signal })),
      ])
      const ids = [...new Set([...frames.items.flatMap(item => item.result.provenance.evidence_refs), ...history.evidence_refs, ...metrics.evidence_refs])]
      return Promise.all(ids.map(async id => { const item = await evidence(id, signal)
        return { evidence_id: item.evidence_id, title: item.evidence_id, result_ids: item.result_ids,
          verification: item.verification, source_drift: factValue(item.source_drift) } }))
    }),
    getEvidence: (evidenceId, signal) => load(async () => {
      const record = await evidence(evidenceId, signal)
      const configId = factValue(record.config_id)
      const configs = configId ? await body<S['ConfigList']>(api.GET('/api/v1/experiments/{experiment_id}/configs', { params: { path: { experiment_id: 'case8' } }, signal })) : null
      return evidenceView(record, configs?.items.find(item => item.id === configId) ?? null)
    }),
  }
}
