/**
 * DataProvider — the single abstraction through which every page reads data.
 *
 * Contract (Window 3 requirement):
 *   Page / View  ->  typed frontend data service  ->  current provider
 *
 * Providers may be MOCK now and REAL API after integration. Switching providers
 * must not require rewriting any page. Every method takes an `AbortSignal` so a
 * page can cancel stale requests when the user changes config / snapshot / tab.
 */
import type {
  AllocationMaskView,
  AllocationSummaryView,
  AllocationView,
  EigenmodeView,
  EntropyHistoryView,
  EvidenceDetailView,
  EvidenceSummaryView,
  ExperimentCatalogEntry,
  ExperimentOverview,
  FieldData,
  GrowthValidationView,
  Loaded,
  MetricCollectionView,
  ProjectView,
  SnapshotAlignmentView,
  SnapshotMeta,
  SpectrumCurveView,
  SpectrumDatasetView,
  SpectralArrayView,
  SpectralArrayRef,
  SpectralDatasetRef,
  ValidationRunRef,
} from './domain'

export interface SnapshotSelector {
  configId: string
  snapshotIndex: number
  fieldId: string
}

/**
 * Allocation target selector.
 *
 * `experimentId` is `case8` (FACE_FIELD, D_u only) or `gate` (CELL_FIELD, one of
 * Acoustic / Pressure / Ungated). Both are read through the same provider so a
 * page never branches on the transport.
 */
export interface AllocationSelector {
  experimentId: 'case8' | 'gate'
  configId: string
}

/**
 * Spectral selectors.
 *
 * `dataset_id` is one of the four registered q_at datasets. `modeIndex` is the
 * Fourier block (ell 0..16). `rank` is the eigenpair rank (0..31) and is a
 * DIFFERENT index space from the mode index; the two are never interchanged.
 */
export interface SpectralCurveSelector {
  datasetId: string
}
export interface SpectralModeSelector {
  datasetId: string
  modeIndex: number
}
export interface EigenmodeSelector {
  datasetId: string
  modeIndex: number
  side: 'LEFT' | 'RIGHT'
  rank: number
  representation: 'COMPLEX_VECTOR' | 'PRIMITIVE_PROFILE'
  projection: 'COMPLEX' | 'REAL' | 'IMAGINARY' | 'AMPLITUDE'
  fieldComponent: string
}

export interface DataProvider {
  readonly kind: 'MOCK' | 'API'
  /** Visible origin label; must be MOCK until the real provider is wired. */
  readonly originLabel: string

  getProject(signal?: AbortSignal): Promise<Loaded<ProjectView>>
  listExperiments(signal?: AbortSignal): Promise<Loaded<ExperimentCatalogEntry[]>>
  getExperimentOverview(experimentId: string, signal?: AbortSignal): Promise<Loaded<ExperimentOverview>>
  listSnapshots(configId: string, signal?: AbortSignal): Promise<Loaded<SnapshotMeta[]>>
  getSnapshotField(selector: SnapshotSelector, signal?: AbortSignal): Promise<Loaded<FieldData>>
  getEntropyHistory(configId: string, signal?: AbortSignal): Promise<Loaded<EntropyHistoryView>>
  getSnapshotAlignment(
    configId: string,
    scalarStep: number,
    policy: 'NEAREST_RECORDED' | 'PINNED',
    pinnedIndex?: number,
    signal?: AbortSignal,
  ): Promise<Loaded<SnapshotAlignmentView>>
  getMetrics(configId: string, signal?: AbortSignal): Promise<Loaded<MetricCollectionView>>
  listEvidenceForConfig(configId: string, signal?: AbortSignal): Promise<Loaded<EvidenceSummaryView[]>>
  getEvidence(evidenceId: string, signal?: AbortSignal): Promise<Loaded<EvidenceDetailView>>

  // --- Phase 6B allocation -------------------------------------------------
  //
  // Mirrors the frozen AllocationService surface (describe / metadata / array /
  // mask / summary). Metadata and arrays are separate calls so a page can render
  // representation_type, mask, definition and verification BEFORE any numeric
  // array arrives — and so a missing array never masquerades as an empty one.

  /** Allocation capability + representation for one experiment/config. */
  describeAllocation(selector: AllocationSelector, signal?: AbortSignal): Promise<Loaded<AllocationView>>
  /** Mask identity and definition only (no array values). */
  loadAllocationMask(selector: AllocationSelector, signal?: AbortSignal): Promise<Loaded<AllocationMaskView>>
  /** Budget / inside / outside and the explicit measure rule. */
  loadAllocationSummary(selector: AllocationSelector, signal?: AbortSignal): Promise<Loaded<AllocationSummaryView>>

  // --- Phase 7B Spectral Lab ------------------------------------------------
  //
  // Mirrors the frozen spectral API surface (SPEC00-SPEC05). Selectors are the
  // registered identities, never paths or array-member names. A missing saved
  // vector is a reason-bearing MISSING (not an empty payload); q_at is never
  // interpolated; the eigenpair rank is never treated as a Fourier mode index.

  /** SPEC00: the four registered q_at datasets (selector identities). */
  listSpectra(signal?: AbortSignal): Promise<Loaded<SpectralDatasetRef[]>>
  /** SPEC01: one dataset summary (17 blocks, refs only — no 512-value dump). */
  getSpectrumDataset(selector: SpectralCurveSelector, signal?: AbortSignal): Promise<Loaded<SpectrumDatasetView>>
  /** SPEC02: the complete 17-block spectral curve for one q. */
  getSpectralCurve(selector: SpectralCurveSelector, signal?: AbortSignal): Promise<Loaded<SpectrumCurveView>>
  /** SPEC04: a saved eigenmode view at one Fourier block (values load via ARRAY01). */
  getEigenmode(selector: EigenmodeSelector, signal?: AbortSignal): Promise<Loaded<EigenmodeView>>
  /**
   * ARRAY01: the numeric payload behind an eigenmode view's `values_ref`.
   *
   * Loaded separately from SPEC04 so the manifest and the numbers never arrive as
   * one payload, and so a missing array is a distinct fact from a missing view.
   * A complex128 vector decodes to `[real, imag]` pairs; a primitive profile to
   * plain numbers. No projection, no resampling.
   */
  loadSpectralArray(ref: SpectralArrayRef, signal?: AbortSignal): Promise<Loaded<SpectralArrayView>>
  /** SPEC05: one recorded growth-validation run (PARTIAL when predictions are absent). */
  getGrowthValidation(runId: string, signal?: AbortSignal): Promise<Loaded<GrowthValidationView>>
  /** The recorded validation-run identities (a selector list, not a numeric read). */
  listValidationRuns(signal?: AbortSignal): Promise<Loaded<ValidationRunRef[]>>
}
