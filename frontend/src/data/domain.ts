/** UI projections of generated OpenAPI schemas; transport DTOs are never copied.
 * Unresolved Fact values stay null in the presentation model.
 */
import type { components } from '../types/generated/api'
type S = components['schemas']
type KnownValue<T> = T extends { state: 'KNOWN'; value: infer V } ? V : never
export type DataOrigin = S['ScientificResult']['data_origin']
export type VerificationStatus = S['Verification']['status']
export type CapabilityStatus = S['ExperimentCapability']['status']
export type DeliveryStatus = S['Experiment']['delivery_status']
export type LoadState = 'LOADING' | 'READY' | 'PARTIAL' | 'MISSING' | 'UNSUPPORTED' | 'ERROR'
export type UnitSpec = Omit<S['UnitSpec'], 'si_mapping'> & { si_mapping: KnownValue<S['UnitSpec']['si_mapping']> | null }
export type VerificationTag = Pick<S['Verification'], 'status' | 'basis' | 'evidence_refs'>
export type Limitation = Pick<S['ScientificLimitation'], 'id' | 'code' | 'description' | 'severity'>
export type ResultHeader = Pick<S['ScientificResult'], 'result_id' | 'experiment_id' | 'config_id' | 'semantic_id' | 'data_origin' | 'availability'> & {
  unit: UnitSpec; verification: VerificationTag; evidence_refs: S['ProvenanceRef']['evidence_refs']; limitations: Limitation[]
}
export type ProjectView = Pick<S['ProjectInfo'], 'project_id' | 'name' | 'registry_revision' | 'data_revision'> & {
  tagline: string; scientific_question: string; mechanism_chain: string[]
}
export type ExperimentCatalogEntry = Pick<S['Experiment'], 'name' | 'scientific_family' | 'delivery_status'> & {
  experiment_id: S['Experiment']['id']; summary: S['Experiment']['description']; availability_note: string | null; implementable_route: string | null
}
export type Case8Config = Pick<S['ExperimentConfig'], 'name'> & {
  config_id: 'A_u' | 'B_u' | 'C_u' | 'D_u'; q_aa: number; q_at: number
}
export type ExperimentOverview = Pick<S['Experiment'], 'name' | 'description' | 'delivery_status'> & {
  experiment_id: S['Experiment']['id']; configurations: Case8Config[]; default_config: S['ExperimentConfig']['id'];
  snapshot_count: S['SnapshotIndex']['snapshot_count']; scalar_step_count: S['ScalarSeries']['total_point_count'];
  protocol: { [K in 'method_name' | 'integrator' | 'reconstruction' | 'final_time']: KnownValue<S['ProtocolSpec'][K]> | null } & { grid: string | null };
  limitation: Limitation | null
}
export type SnapshotMeta = Pick<S['FieldSnapshot'], 'snapshot_index' | 'snapshot_id' | 'step_index' | 'physical_time'> & { fields: FieldMeta[] }
export type FieldMeta = Pick<S['FieldDescriptor'], 'field_id' | 'label'> & Pick<S['ArrayDescriptor'], 'shape' | 'axes'> & {
  unit_label: S['UnitSpec']['label']; extent: { x: [number, number]; y: [number, number] }; verification_status: VerificationStatus; result: ResultHeader
}
export type FieldData = { meta: FieldMeta; values: number[]; data_origin: DataOrigin }
export type ScalarPointView = Pick<S['ScalarPoint'], 'point_index'> & {
  [K in 'step_index' | 'source_step_index' | 'physical_time' | 'value']: KnownValue<S['ScalarPoint'][K]>
}
export type ScalarSeriesView = Pick<S['ScalarSeries'], 'series_id' | 'label' | 'aggregation' | 'definition_id'> & {
  unit: UnitSpec; points: ScalarPointView[]; data_origin: DataOrigin; verification: VerificationTag; result: ResultHeader
}
export type EntropyHistoryView = Pick<S['EntropyHistory'], 'experiment_id' | 'config_id'> & {
  series: ScalarSeriesView[]; total_point_count: S['ScalarSeries']['total_point_count']; limitations: Limitation[]
}
export type SnapshotAlignmentView = Omit<S['SnapshotAlignment'], 'limitations'>
export type MetricView = Pick<S['Metric'], 'metric_id' | 'display_label' | 'definition_id'> & {
  value: KnownValue<S['Metric']['value']> | null; unit: UnitSpec;
  definition_text: S['ScientificDefinition']['definition']; detector_scope: string; time_scope_label: string;
  resolution_limit: KnownValue<S['Metric']['resolution_limit']> | null; evidence_refs: S['ProvenanceRef']['evidence_refs'];
  availability: S['Experiment']['status']; unavailable_reason: string | null
}
export type MetricCollectionView = Pick<S['MetricCollection'], 'experiment_id' | 'config_id'> & { items: MetricView[] }
export type EvidenceSummaryView = Pick<S['EvidenceIndexItem'], 'evidence_id' | 'title' | 'result_ids'> & {
  verification: VerificationTag; source_drift: KnownValue<S['EvidenceRecord']['source_drift']> | null
}
export type SourceAssetView = Pick<S['SourceAsset'], 'asset_id' | 'source_display'> & {
  role: string; recorded_hash: KnownValue<S['SourceAsset']['recorded_data_hash']> | null;
  current_hash: KnownValue<S['SourceAsset']['current_data_hash']> | null;
  drift: KnownValue<S['SourceAsset']['data_drift']> | null; verification: VerificationTag
}
export type EvidenceDetailView = Pick<S['EvidenceRecord'], 'evidence_id' | 'schema_version'> & {
  [K in 'experiment_id' | 'config_id' | 'method_name' | 'method_hash' | 'recorded_source_hash' | 'current_source_hash' | 'data_hash' | 'source_drift']: KnownValue<S['EvidenceRecord'][K]> | null
} & {
  supports: string; does_not_support: string; config_parameters: { name: string; value: string }[];
  verification: VerificationTag; source_assets: SourceAssetView[]; related_result_ids: S['EvidenceRecord']['result_ids'];
  limitations: Limitation[]; freeze_id: S['FreezeReference']['freeze_id'] | null; data_origin: DataOrigin
}
export type ProviderKind = 'MOCK' | 'API'
export type Loaded<T> = { state: LoadState; data: T | null; reason: string | null; origin: DataOrigin }

// --- Phase 6B allocation ----------------------------------------------------
//
// Allocation is cumulative spatial entropy: a single number per face/cell that
// already contains the time/RK weights, plus an explicit spatial measure rule.
// The two accepted representations are DIFFERENT scientific objects:
//
//   FACE_FIELD  native x/y normal faces; spatial measure = dy*sum(x)+dx*sum(y)
//   CELL_FIELD  one cell field; spatial measure already baked in; = sum(cells)
//
// They are modelled as a discriminated union so a view cannot render one as the
// other, and so no generic "heatmap" projection is ever invented.

/** Internal capability vocabulary; ANGULAR_SECTOR maps to frozen ANGULAR_SECTORS. */
export type AllocationRepresentation = 'FACE_FIELD' | 'CELL_FIELD' | 'ANGULAR_SECTOR'
/** Human-facing measure rule the allocation values already embody. */
export type AllocationMeasureDefinition = 'face integrated' | 'cell integrated' | 'sector aggregated'

/** One allocation array (or one native-face orientation) with its own identity. */
export type AllocationArrayView = {
  /** Registered array id, e.g. pi_at_x_faces / pi_at_y_faces / pi_at_cells. */
  array_id: string
  label: string
  /** Face orientation for FACE_FIELD; null for CELL_FIELD. */
  location_type: 'CARTESIAN_X_FACE' | 'CARTESIAN_Y_FACE' | 'CARTESIAN_CELL'
  shape: number[]
  axes: string[]
  unit_label: string
  /** Values are always present; the mock/API both deliver recorded arrays only. */
  values: number[]
}

/** Mask identity, definition and per-orientation counts. Never shared between views. */
export type AllocationMaskView = {
  mask_id: string
  mask_type: S['MaskSpec']['type']
  definition: string
  /** Mask counts per mask array, e.g. native x/y faces report two separate counts. */
  counts: number[]
  evidence_refs: string[]
  verification: VerificationTag
}

/** Budget / inside / outside as returned by the summary; null when unresolved. */
export type AllocationMetricView = {
  metric_id: string
  display_label: string
  value: number | null
  unit_label: string
  definition_id: string
  /** FRACTION for inside/outside; null for the integrated budget. */
  fraction_format: 'FRACTION' | null
  evidence_refs: string[]
}

export type AllocationSummaryView = {
  total_budget: AllocationMetricView
  inside: AllocationMetricView
  outside: AllocationMetricView | null
  /** Integration interval, e.g. "[0,0.08]". Kept as a string: never re-derived. */
  integration_interval: string
  time_scope_label: string
  measure_definition: AllocationMeasureDefinition
  includes_time_weights: boolean
  includes_spatial_measure: boolean
  /** The explicit algebraic rule, e.g. "dy*sum(xfaces)+dx*sum(yfaces)". */
  integral_rule: string
  /** Numeric parameters of the rule (dx / dy), declared not inferred. */
  measure_parameters: { name: string; value: number }[]
  evidence_refs: string[]
}

/** The invariant part shared by both representations. */
export type AllocationCommonView = {
  result_id: string
  experiment_id: string
  config_id: string
  semantic_id: string
  title: string
  /** The ScientificDefinition text; the user-visible "definition" field. */
  definition: string
  time_rule: string
  spatial_rule: string
  data_origin: DataOrigin
  verification: VerificationTag
  limitations: Limitation[]
  evidence_refs: string[]
  mask: AllocationMaskView
  summary: AllocationSummaryView
}

/** Native face allocation — Case8 D_u. Keeps x/y orientations separate. */
export type FaceAllocationView = AllocationCommonView & {
  representation_type: 'FACE_FIELD'
  measure_definition: 'face integrated'
  coordinate_convention: string
  /** Exactly two orientations; they are never averaged into one cell field. */
  arrays: [AllocationArrayView, AllocationArrayView]
}

/** Cell allocation — Gate Acoustic / Pressure / Ungated. Single 32×128 field. */
export type CellAllocationView = AllocationCommonView & {
  representation_type: 'CELL_FIELD'
  measure_definition: 'cell integrated'
  coordinate_convention: string
  /** Exactly one cell field. */
  arrays: [AllocationArrayView]
}

export type AllocationView = FaceAllocationView | CellAllocationView
