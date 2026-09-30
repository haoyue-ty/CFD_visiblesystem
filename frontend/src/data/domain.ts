/**
 * Typed frontend domain contracts for the Window 3 Case8 functional slice.
 *
 * These types are the boundary that pages consume. They are deliberately
 * decoupled from `types/generated/api.d.ts` (the OpenAPI artifact) AND from any
 * concrete provider (mock / real API). A page must never import a mock module
 * or call a transport directly; it talks to `DataProvider` only.
 *
 * NOTE ON CONTRACT GAP: the frozen API contract (docs/06_API_CONTRACT.md)
 * defines operations C801..C808, but the bootstrap OpenAPI artifact
 * (config/openapi.json / types/generated/api.d.ts) currently exposes only
 * SYS01 and DOC01. The transport-shaped DTOs below therefore mirror the
 * *documented* frozen contract shapes (FieldSnapshot, ScalarSeries,
 * SnapshotAlignment, Metric, EvidenceRecord, ...) without depending on the
 * generated artifact. When integration replaces the mock provider with a real
 * API provider, only the provider implementation changes.
 */

export type DataOrigin =
  | 'FROZEN_PRODUCTION'
  | 'VERIFIED_PRODUCTION'
  | 'VERIFIED_POSTPROCESS'
  | 'DIAGNOSTIC_RERUN'
  | 'MOCK'
  | 'SCHEMATIC'
  | 'LIVE_DEMO'

export type VerificationStatus =
  | 'FROZEN_VERIFIED'
  | 'VERIFIED_NOT_FROZEN'
  | 'DERIVED_VERIFIED'
  | 'AVAILABLE_UNVERIFIED'
  | 'PARTIAL'
  | 'MISSING'
  | 'LEGACY'
  | 'SUPERSEDED'
  | 'NOT_APPLICABLE'

/** Scientific capability of a task (NOT delivery status, NOT verification). */
export type CapabilityStatus = 'SUPPORTED' | 'PARTIAL' | 'MISSING' | 'UNSUPPORTED'
/** Software delivery progress (PLANNED vs IMPLEMENTED). */
export type DeliveryStatus = 'PLANNED' | 'IMPLEMENTED'
/** Interface loading state. */
export type LoadState = 'LOADING' | 'READY' | 'PARTIAL' | 'MISSING' | 'UNSUPPORTED' | 'ERROR'

export interface UnitSpec {
  id: string
  system: 'MODEL' | 'DIMENSIONLESS' | 'UNKNOWN'
  quantity: string
  label: string
  si_mapping: string | null
}

export interface VerificationTag {
  status: VerificationStatus
  basis: string[]
  evidence_refs: string[]
}

export interface Limitation {
  id: string
  code: string
  description: string
  severity: 'INFO' | 'WARNING' | 'BLOCKING'
}

/** Common scientific header carried by every result-bearing payload. */
export interface ResultHeader {
  result_id: string
  experiment_id: string
  config_id: string
  semantic_id: string
  data_origin: DataOrigin
  availability: 'AVAILABLE' | 'PARTIAL'
  unit: UnitSpec
  verification: VerificationTag
  evidence_refs: string[]
  limitations: Limitation[]
}

export interface ProjectView {
  project_id: string
  name: string
  tagline: string
  scientific_question: string
  mechanism_chain: string[]
  registry_revision: string
  data_revision: string
}

/** Delivery-level catalog entry (Lab / Home experiment list). */
export interface ExperimentCatalogEntry {
  experiment_id: string
  name: string
  scientific_family: string
  summary: string
  delivery_status: DeliveryStatus
  /** Only meaningful once implemented; PLANNED entries carry null. */
  availability_note: string | null
  implementable_route: string | null
}

export interface Case8Config {
  config_id: 'A_u' | 'B_u' | 'C_u' | 'D_u'
  name: string
  q_aa: number
  q_at: number
}

export interface ExperimentOverview {
  experiment_id: string
  name: string
  description: string
  delivery_status: DeliveryStatus
  configurations: Case8Config[]
  /** Default config on entry per IA 9.1 (D_u Overview). */
  default_config: string
  snapshot_count: number
  scalar_step_count: number
  protocol: {
    method_name: string | null
    integrator: string | null
    reconstruction: string | null
    final_time: number | null
    grid: string | null
  }
  limitation: Limitation | null
}

/** A snapshot metadata row (no array values yet). */
export interface SnapshotMeta {
  snapshot_index: number
  snapshot_id: string
  step_index: number
  physical_time: number
  fields: FieldMeta[]
}

export interface FieldMeta {
  field_id: string
  label: string
  unit_label: string
  shape: [number, number]
  axes: [string, string]
  extent: { x: [number, number]; y: [number, number] }
  verification_status: VerificationStatus
  result: ResultHeader
}

/** Fetched field: metadata plus real flat values in C order (row-major, y then x). */
export interface FieldData {
  meta: FieldMeta
  values: number[]
  data_origin: DataOrigin
}

/** One accepted-step scalar point. */
export interface ScalarPointView {
  point_index: number
  /** canonical completed accepted step, 1-based */
  step_index: number
  /** source_step_index, 0-based */
  source_step_index: number
  physical_time: number
  value: number
}

export interface ScalarSeriesView {
  series_id: string
  label: string
  aggregation: 'NONE' | 'CUMULATIVE' | 'STEP_INCREMENT' | 'STAGE_AGGREGATE'
  unit: UnitSpec
  definition_id: string
  points: ScalarPointView[]
  data_origin: DataOrigin
  verification: VerificationTag
  result: ResultHeader
}

export interface EntropyHistoryView {
  experiment_id: string
  config_id: string
  series: ScalarSeriesView[]
  /** Total accepted-step count for the scalar timeline. */
  total_point_count: number
  limitations: Limitation[]
}

export interface SnapshotAlignmentView {
  experiment_id: string
  config_id: string
  selection_policy: 'NEAREST_RECORDED' | 'PINNED'
  selected_scalar_step: number
  selected_scalar_time: number
  displayed_snapshot_id: string
  displayed_snapshot_index: number
  displayed_snapshot_time: number
  signed_time_delta: number
}

export interface MetricView {
  metric_id: string
  display_label: string
  value: number | null
  unit: UnitSpec
  definition_id: string
  definition_text: string
  detector_scope: string
  time_scope_label: string
  resolution_limit: number | null
  evidence_refs: string[]
  availability: 'AVAILABLE' | 'PARTIAL' | 'MISSING' | 'UNSUPPORTED' | 'ERROR'
  unavailable_reason: string | null
}

export interface MetricCollectionView {
  experiment_id: string
  config_id: string
  items: MetricView[]
}

export interface EvidenceSummaryView {
  evidence_id: string
  title: string
  result_ids: string[]
  verification: VerificationTag
  source_drift: boolean | null
}

export interface SourceAssetView {
  asset_id: string
  source_display: string
  role: string
  recorded_hash: string | null
  current_hash: string | null
  drift: boolean | null
  verification: VerificationTag
}

export interface EvidenceDetailView {
  evidence_id: string
  schema_version: string
  supports: string
  does_not_support: string
  experiment_id: string | null
  config_id: string | null
  config_parameters: { name: string; value: string }[]
  method_name: string | null
  method_hash: string | null
  recorded_source_hash: string | null
  current_source_hash: string | null
  data_hash: string | null
  verification: VerificationTag
  source_drift: boolean | null
  source_assets: SourceAssetView[]
  related_result_ids: string[]
  limitations: Limitation[]
  freeze_id: string | null
  data_origin: DataOrigin
}

export type ProviderKind = 'MOCK' | 'API'

/** Every provider response is a tagged load state; never a bare value. */
export type Loaded<T> = {
  state: LoadState
  data: T | null
  /** Present when state is MISSING / UNSUPPORTED / ERROR. */
  reason: string | null
  /** Human-readable provider origin, shown as a visible badge in the UI. */
  origin: DataOrigin
}
