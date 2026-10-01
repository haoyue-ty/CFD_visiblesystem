/** Real API transport; all scientific DTOs come from generated OpenAPI types. */
import { api } from '../services/api'
import type { components } from '../types/generated/api'
import type { AllocationSelector, DataProvider } from './provider'
import type {
  AllocationArrayView,
  AllocationMaskView,
  AllocationMetricView,
  AllocationSummaryView,
  AllocationView,
  FieldMeta,
  Loaded,
  MetricView,
  UnitSpec,
  ResultHeader,
  EvidenceDetailView,
} from './domain'

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

/**
 * Allocation error classifier.
 *
 * Explicitly disabled loaders report UNSUPPORTED; missing assets stay MISSING.
 * A source failure stays ERROR, without a synthetic field or provider fallback.
 */
function allocationFailure(envelope: { availability?: string; error?: S['ErrorBody'] } | undefined, status: number): ApiFailure {
  const availability = envelope?.availability
  const code = envelope?.error?.code
  const state: 'MISSING' | 'UNSUPPORTED' | 'ERROR' =
    availability === 'MISSING' || code === 'RESULT_NOT_FOUND' || code === 'NOT_FOUND' ? 'MISSING'
      : availability === 'UNSUPPORTED' || code === 'FEATURE_NOT_ENABLED' ? 'UNSUPPORTED'
        : 'ERROR'
  return new ApiFailure(state, envelope?.error?.message ?? `API request failed (${status})`)
}

/** Read an allocation envelope, mapping capability gaps onto honest states. */
async function allocationBody<T>(request: Promise<{ data?: unknown; error?: unknown; response: Response }>): Promise<T> {
  const response = await request
  const envelope = (response.data ?? response.error) as { availability?: string; data?: T; error?: S['ErrorBody'] }
  if (!response.response.ok || !envelope || !('data' in envelope)) {
    throw allocationFailure(envelope, response.response.status)
  }
  return envelope.data as T
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

/**
 * Canonical server MaskSpec and orientation counts; validate summary identity.
 */
function maskView(meta: S['AllocationMetadata'], summary: S['AllocationSummary']): AllocationMaskView {
  const mask = meta.masks?.[0]
  if (!mask || meta.mask_refs.length !== 1 || mask.id !== meta.mask_refs[0]
    || summary.mask_refs.length !== 1 || summary.mask_refs[0] !== mask.id) throw new Error('Allocation mask context mismatch')
  return {
    mask_id: mask.id,
    mask_type: mask.type,
    definition: mask.definition,
    counts: meta.mask_counts ?? [],
    evidence_refs: summary.evidence_refs,
    verification: meta.result.verification,
  }
}

/**
 * Allocation result identifier for a selector.
 *
 * Result identities are server-registered: `case8.D_u.allocation` and
 * `gate.<config>.allocation`. The frontend names the target, the server declares
 * the representation — the frontend never guesses it.
 */
function allocationResultId(selector: AllocationSelector): string {
  return selector.experimentId === 'case8' ? `case8.${selector.configId}.allocation` : `gate.${selector.configId}.allocation`
}

/** Read the `value` of an AVAILABLE / PARTIAL resource slot, else null. */
function slotValue<T>(slot: { availability: string; value?: T }): T | null {
  return slot.availability === 'AVAILABLE' || slot.availability === 'PARTIAL' ? (slot.value ?? null) : null
}

function validateAllocationSummary(meta: S['AllocationMetadata'], summary: S['AllocationSummary']) {
  if (JSON.stringify(meta.measure) !== JSON.stringify(summary.measure)) throw new Error('Allocation measure context mismatch')
  for (const [slot, fraction] of [[summary.total_budget, false], [summary.inside, true], [summary.outside, true]] as const) {
    const metric = slotValue(slot)
    if (!metric) continue
    const result = metric.result
    if (result.experiment_id !== meta.experiment_id || result.config_id !== meta.config_id
      || result.provenance.registry_revision !== meta.result.provenance.registry_revision
      || result.provenance.data_revision !== meta.result.provenance.data_revision
      || metric.time_scope.accumulation !== 'TRAJECTORY_INTEGRATED'
      || JSON.stringify(metric.time_scope.interval) !== JSON.stringify(meta.result.time.interval)
      || result.unit.id !== (fraction ? 'dimensionless_fraction' : 'model_integrated_entropy')
      || (!fraction && result.semantic_id !== 'E_at_cumulative')) throw new Error('Allocation scalar context mismatch')
  }
}

/** Map one summary Metric slot onto the allocation metric view. */
function allocationMetricView(m: S['Metric'] | null, label: string, fraction: boolean): AllocationMetricView {
  return {
    metric_id: m?.metric_id ?? `unavailable.${label}`,
    display_label: m?.display_label ?? label,
    value: m ? factValue(m.value) : null,
    unit_label: m ? m.result.unit.label : 'UNKNOWN',
    definition_id: m?.definition_id ?? 'unknown',
    fraction_format: fraction ? 'FRACTION' : null,
    evidence_refs: m?.result.provenance.evidence_refs ?? [],
  }
}

/**
 * Map the wire AllocationSummary + MeasureConvention onto the view.
 *
 * The measure rule is carried through verbatim — it is what distinguishes the
 * two representations, so it is never re-derived or simplified here.
 */
function summaryView(summary: S['AllocationSummary'], measure: S['MeasureConvention']): AllocationSummaryView {
  const budgetMetric = slotValue(summary.total_budget)
  const insideMetric = slotValue(summary.inside)
  const outsideMetric = summary.outside ? slotValue(summary.outside) : null
  const interval = budgetMetric ? factValue(budgetMetric.time_scope.interval) : null
  const accumulation = budgetMetric ? budgetMetric.time_scope.accumulation : null
  const sampling = budgetMetric ? budgetMetric.time_scope.sampling : null
  return {
    total_budget: allocationMetricView(budgetMetric, 'Integrated budget', false),
    inside: allocationMetricView(insideMetric, 'Inside window', true),
    outside: outsideMetric ? allocationMetricView(outsideMetric, 'Outside window', true) : null,
    integration_interval: interval ? `[${interval.start},${interval.end}]` : 'UNKNOWN',
    time_scope_label: sampling && accumulation ? `${sampling} / ${accumulation}` : measure.description,
    measure_definition: measure.includes_spatial_measure ? 'cell integrated' : 'face integrated',
    includes_time_weights: measure.includes_time_weights,
    includes_spatial_measure: measure.includes_spatial_measure,
    integral_rule: measure.integral_rule,
    measure_parameters: measure.measure_parameters
      .map(p => ({ name: p.name, value: factValue(p.value) }))
      .filter((p): p is { name: string; value: number } => typeof p.value === 'number'),
    evidence_refs: summary.evidence_refs,
  }
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
      const boundConfig = factValue(record.config)
      const configs = !boundConfig && configId && factValue(record.experiment_id) === 'case8'
        ? await body<S['ConfigList']>(api.GET('/api/v1/experiments/{experiment_id}/configs', { params: { path: { experiment_id: 'case8' } }, signal })) : null
      return evidenceView(record, boundConfig ?? configs?.items.find(item => item.id === configId) ?? null)
    }),

    // --- Phase 6B allocation -------------------------------------------------
    // ALLOC01 metadata declares the representation; ALLOC03 supplies the summary.
    // Integrated loaders retain each source's representation, revision and masks.
    describeAllocation: (selector, signal) => load(async () => {
      const resultId = allocationResultId(selector)
      const meta = await allocationBody<S['AllocationMetadata']>(
        api.GET('/api/v1/allocations/{result_id}/metadata', { params: { path: { result_id: resultId } }, signal }),
      )
      const summary = await allocationBody<S['AllocationSummary']>(
        api.GET('/api/v1/allocations/{result_id}/summary', { params: { path: { result_id: resultId } }, signal }),
      )
      const definition = meta.definition
      validateAllocationSummary(meta, summary)
      if (!definition || definition.semantic_id !== meta.semantic_id) throw new Error('Allocation definition context mismatch')
      header(meta.result)
      const common = {
        result_id: meta.result_id,
        experiment_id: meta.experiment_id,
        config_id: meta.config_id,
        semantic_id: meta.semantic_id,
        title: definition.title,
        definition: definition.definition,
        time_rule: definition.time_rule,
        spatial_rule: definition.spatial_rule,
        data_origin: meta.result.data_origin,
        verification: meta.result.verification,
        limitations: meta.result.limitations,
        evidence_refs: meta.evidence_refs,
        mask: maskView(meta, summary),
        summary: summaryView(summary, meta.measure),
      }
      const arrays: AllocationArrayView[] = await Promise.all(meta.array_refs.map(ref =>
        allocationBody<S['AllocationArrayResponse']>(
          api.GET('/api/v1/allocations/{result_id}/arrays/{array_id}', {
            params: { path: { result_id: meta.result_id, array_id: ref.descriptor.array_id } }, signal,
          }),
        ).then(array => {
          // Mirror the snapshot-array guard: a non-numeric payload is an error,
          // never a silently coerced field.
          const field = meta.fields?.find(f => f.array_ref.descriptor.array_id === ref.descriptor.array_id)
          if (!field || array.representation_type !== meta.representation_type
            || array.result.experiment_id !== meta.experiment_id || array.result.config_id !== meta.config_id
            || array.result.semantic_id !== meta.semantic_id
            || array.result.result_id !== ref.result_id
            || array.result.provenance.registry_revision !== meta.result.provenance.registry_revision
            || array.result.provenance.data_revision !== meta.result.provenance.data_revision
            || JSON.stringify(array.array_ref) !== JSON.stringify(ref)
            || array.values.length !== ref.descriptor.element_count
            || array.values.some(v => typeof v !== 'number' || !Number.isFinite(v))) throw new Error('Allocation array context mismatch')
          header(array.result)
          const location = field.domain.location_type
          if (location !== 'CARTESIAN_X_FACE' && location !== 'CARTESIAN_Y_FACE' && location !== 'CARTESIAN_CELL') {
            throw new Error('Unsupported allocation field location')
          }
          return {
            array_id: array.array_ref.descriptor.array_id,
            label: field.label,
            location_type: location,
            shape: array.array_ref.descriptor.shape,
            axes: array.array_ref.descriptor.axes,
            unit_label: array.result.unit.label,
            values: array.values as number[],
          }
        }),
      ))
      // The server declares the representation; the frontend narrows to it and
      // asserts the matching array cardinality the renderer requires.
      if (meta.representation_type === 'FACE_FIELD') {
        if (arrays.length !== 2 || arrays[0].location_type !== 'CARTESIAN_X_FACE'
          || arrays[1].location_type !== 'CARTESIAN_Y_FACE'
          || common.mask.mask_type !== 'CASE8_NATIVE_FACE_SHOCK_WINDOW'
          || meta.measure.includes_spatial_measure) throw new Error('FACE_FIELD requires exactly two native-face orientations')
        return {
          ...common, representation_type: 'FACE_FIELD', measure_definition: 'face integrated',
          coordinate_convention: meta.coordinate_convention,
          arrays: [arrays[0], arrays[1]],
        }
      }
      if (meta.representation_type !== 'CELL_FIELD' || arrays.length !== 1
        || arrays[0].location_type !== 'CARTESIAN_CELL' || common.mask.mask_type !== 'GATE_CELL_SHOCK_WINDOW'
        || !meta.measure.includes_spatial_measure) throw new Error('CELL_FIELD requires exactly one cell array')
      return {
        ...common, representation_type: 'CELL_FIELD', measure_definition: 'cell integrated',
        coordinate_convention: meta.coordinate_convention, arrays: [arrays[0]],
      }
    }),
    loadAllocationMask: (selector, signal) => load(async () => {
      const resultId = allocationResultId(selector)
      const meta = await allocationBody<S['AllocationMetadata']>(
        api.GET('/api/v1/allocations/{result_id}/metadata', { params: { path: { result_id: resultId } }, signal }),
      )
      const summary = await allocationBody<S['AllocationSummary']>(
        api.GET('/api/v1/allocations/{result_id}/summary', { params: { path: { result_id: resultId } }, signal }),
      )
      return maskView(meta, summary)
    }),
    loadAllocationSummary: (selector, signal) => load(async () => {
      const resultId = allocationResultId(selector)
      const meta = await allocationBody<S['AllocationMetadata']>(
        api.GET('/api/v1/allocations/{result_id}/metadata', { params: { path: { result_id: resultId } }, signal }),
      )
      const summary = await allocationBody<S['AllocationSummary']>(
        api.GET('/api/v1/allocations/{result_id}/summary', { params: { path: { result_id: resultId } }, signal }),
      )
      validateAllocationSummary(meta, summary)
      return summaryView(summary, meta.measure)
    }),
  }
}
