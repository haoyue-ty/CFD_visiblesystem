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
  EntropyHistoryView,
  EvidenceDetailView,
  EvidenceSummaryView,
  ExperimentCatalogEntry,
  ExperimentOverview,
  FieldData,
  Loaded,
  MetricCollectionView,
  ProjectView,
  SnapshotAlignmentView,
  SnapshotMeta,
} from './domain'

export interface SnapshotSelector {
  configId: string
  snapshotIndex: number
  fieldId: string
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
}
