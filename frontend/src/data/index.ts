/**
 * Data service facade — the ONLY module pages import for data.
 *
 * Responsibilities:
 *  - own the "current provider" (MOCK now, REAL API after integration)
 *  - expose typed, page-oriented accessors
 *  - implement the request-generation / abort strategy so switching config or
 *    snapshot can never render a stale result under a new heading
 *
 * Pages never import a mock module or a transport directly.
 */
import { ref, type Ref } from 'vue'
import type { AllocationSelector, EigenmodeSelector, DataProvider, SnapshotSelector, SpectralCurveSelector } from './provider'
import type { SpectralArrayRef } from './domain'
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
  SpectralDatasetRef,
  ValidationRunRef,
} from './domain'
import { createMockProvider } from './mockProvider'
import { createApiProvider } from './apiProvider'
export { cylinderService } from './cylinder'

export type {
  AllocationArrayView,
  AllocationMaskView,
  AllocationMeasureDefinition,
  AllocationMetricView,
  AllocationRepresentation,
  AllocationSummaryView,
  AllocationView,
  CellAllocationView,
  ComplexProjection,
  DataOrigin,
  EigenmodeView,
  EigenRepresentation,
  EigenSide,
  EntropyHistoryView,
  EvidenceDetailView,
  EvidenceSummaryView,
  ExperimentCatalogEntry,
  ExperimentOverview,
  FaceAllocationView,
  FieldData,
  GrowthErrorView,
  GrowthRatesView,
  GrowthValidationView,
  Loaded,
  LoadState,
  MetricCollectionView,
  ProjectView,
  SnapshotAlignmentView,
  SnapshotMeta,
  SpectralDatasetRef,
  SpectralHeader,
  SpectralNormalizationView,
  SpectralPointView,
  SpectralRepresentation,
  SpectralArrayRef,
  SpectralArrayView,
  SpectrumCurveView,
  SpectrumDatasetView,
  ValidationRunRef,
} from './domain'

const providers: Partial<Record<'MOCK' | 'API', DataProvider>> = { API: createApiProvider() }
// A production bundle can never select or fall back to synthetic science.
if (import.meta.env.DEV) providers.MOCK = createMockProvider()
const activeKind = ref<'MOCK' | 'API'>(import.meta.env.DEV && import.meta.env.VITE_DATA_PROVIDER === 'MOCK' ? 'MOCK' : 'API')

/** Reactive handle so the UI can render a persistent MOCK badge. */
export const activeProvider: Ref<DataProvider> = ref(providers[activeKind.value]!)

export function getProvider(): DataProvider {
  return activeProvider.value
}

/** Switch provider at integration time; pages need no changes. */
export function setProviderKind(kind: 'MOCK' | 'API'): void {
  const provider = providers[kind]
  if (!provider) throw new Error('Mock provider is available only in development/tests')
  activeKind.value = kind
  activeProvider.value = provider
}

/**
 * A per-consumer request generation guard.
 *
 * Usage:
 *   const guard = createRequestGuard()
 *   const result = await guard.run((signal) => getProvider().getMetrics(cfg, signal))
 *   // stale in-flight requests are aborted; only the newest resolves.
 */
export interface RequestGuard {
  run<T>(task: (signal: AbortSignal) => Promise<Loaded<T>>): Promise<Loaded<T> | null>
  cancel(): void
}

export function createRequestGuard(): RequestGuard {
  let controller: AbortController | null = null
  let generation = 0
  return {
    async run<T>(task: (signal: AbortSignal) => Promise<Loaded<T>>): Promise<Loaded<T> | null> {
      controller?.abort()
      controller = new AbortController()
      const myGeneration = ++generation
      const signal = controller.signal
      try {
        const result = await task(signal)
        // Only the newest generation may resolve; older ones are discarded.
        if (myGeneration !== generation) return null
        return result
      } catch (error) {
        if ((error as { name?: string }).name === 'AbortError') return null
        if (myGeneration !== generation) return null
        return { state: 'ERROR', data: null, origin: getProvider().kind === 'MOCK' ? 'MOCK' : 'VERIFIED_PRODUCTION', reason: String(error) }
      }
    },
    cancel() {
      ++generation
      controller?.abort()
    },
  }
}

// --- page-oriented accessors -------------------------------------------------

export const dataService = {
  getProject: (signal?: AbortSignal): Promise<Loaded<ProjectView>> => getProvider().getProject(signal),
  listExperiments: (signal?: AbortSignal): Promise<Loaded<ExperimentCatalogEntry[]>> => getProvider().listExperiments(signal),
  getExperimentOverview: (experimentId: string, signal?: AbortSignal): Promise<Loaded<ExperimentOverview>> =>
    getProvider().getExperimentOverview(experimentId, signal),
  listSnapshots: (configId: string, signal?: AbortSignal): Promise<Loaded<SnapshotMeta[]>> =>
    getProvider().listSnapshots(configId, signal),
  getSnapshotField: (selector: SnapshotSelector, signal?: AbortSignal): Promise<Loaded<FieldData>> =>
    getProvider().getSnapshotField(selector, signal),
  getEntropyHistory: (configId: string, signal?: AbortSignal): Promise<Loaded<EntropyHistoryView>> =>
    getProvider().getEntropyHistory(configId, signal),
  getSnapshotAlignment: (
    configId: string,
    scalarStep: number,
    policy: 'NEAREST_RECORDED' | 'PINNED',
    pinnedIndex?: number,
    signal?: AbortSignal,
  ): Promise<Loaded<SnapshotAlignmentView>> => getProvider().getSnapshotAlignment(configId, scalarStep, policy, pinnedIndex, signal),
  getMetrics: (configId: string, signal?: AbortSignal): Promise<Loaded<MetricCollectionView>> =>
    getProvider().getMetrics(configId, signal),
  listEvidenceForConfig: (configId: string, signal?: AbortSignal): Promise<Loaded<EvidenceSummaryView[]>> =>
    getProvider().listEvidenceForConfig(configId, signal),
  getEvidence: (evidenceId: string, signal?: AbortSignal): Promise<Loaded<EvidenceDetailView>> =>
    getProvider().getEvidence(evidenceId, signal),

  // --- Phase 6B allocation -------------------------------------------------
  describeAllocation: (selector: AllocationSelector, signal?: AbortSignal): Promise<Loaded<AllocationView>> =>
    getProvider().describeAllocation(selector, signal),
  loadAllocationMask: (selector: AllocationSelector, signal?: AbortSignal): Promise<Loaded<AllocationMaskView>> =>
    getProvider().loadAllocationMask(selector, signal),
  loadAllocationSummary: (selector: AllocationSelector, signal?: AbortSignal): Promise<Loaded<AllocationSummaryView>> =>
    getProvider().loadAllocationSummary(selector, signal),

  // --- Phase 7B spectral ---------------------------------------------------
  listSpectra: (signal?: AbortSignal): Promise<Loaded<SpectralDatasetRef[]>> => getProvider().listSpectra(signal),
  getSpectrumDataset: (selector: SpectralCurveSelector, signal?: AbortSignal): Promise<Loaded<SpectrumDatasetView>> =>
    getProvider().getSpectrumDataset(selector, signal),
  getSpectralCurve: (selector: SpectralCurveSelector, signal?: AbortSignal): Promise<Loaded<SpectrumCurveView>> =>
    getProvider().getSpectralCurve(selector, signal),
  getEigenmode: (selector: EigenmodeSelector, signal?: AbortSignal): Promise<Loaded<EigenmodeView>> =>
    getProvider().getEigenmode(selector, signal),
  loadSpectralArray: (ref: SpectralArrayRef, signal?: AbortSignal): Promise<Loaded<SpectralArrayView>> =>
    getProvider().loadSpectralArray(ref, signal),
  getGrowthValidation: (runId: string, signal?: AbortSignal): Promise<Loaded<GrowthValidationView>> =>
    getProvider().getGrowthValidation(runId, signal),
  listValidationRuns: (signal?: AbortSignal): Promise<Loaded<ValidationRunRef[]>> => getProvider().listValidationRuns(signal),
}

export type { AllocationSelector, DataProvider, EigenmodeSelector, SnapshotSelector, SpectralCurveSelector }
