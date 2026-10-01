/**
 * Mock Provider — schema-valid synthetic data for parallel development.
 *
 * Rules enforced here (Window 3 requirements):
 *  - Every result carries data_origin = MOCK.
 *  - Every MOCK result carries verification = NOT_APPLICABLE.
 *  - Every result_id is namespaced with the `mock.` prefix.
 *  - No paper number is hard-coded to masquerade as a real backend value.
 *  - No file is copied from D:\Paper\passage6; all arrays are generated.
 *
 * The generated values are deterministic (seeded) so tests and deep-links are
 * reproducible, but they are SYNTHETIC and must never be cited as science.
 */
import type { DataProvider, SnapshotSelector } from './provider'
import type {
  DataOrigin,
  EntropyHistoryView,
  EvidenceDetailView,
  EvidenceSummaryView,
  ExperimentCatalogEntry,
  ExperimentOverview,
  FieldData,
  FieldMeta,
  Limitation,
  Loaded,
  MetricCollectionView,
  MetricView,
  ProjectView,
  ResultHeader,
  ScalarPointView,
  ScalarSeriesView,
  SnapshotAlignmentView,
  SnapshotMeta,
  UnitSpec,
  VerificationStatus,
} from './domain'

const MOCK_ORIGIN = 'MOCK' as const

/** Deterministic PRNG (mulberry32) — identical sequence across runs. */
function rng(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const CONFIGS = [
  { config_id: 'A_u' as const, name: 'A_u', q_aa: 13.2, q_at: 0 },
  { config_id: 'B_u' as const, name: 'B_u', q_aa: 3.96, q_at: 0 },
  { config_id: 'C_u' as const, name: 'C_u', q_aa: 13.2, q_at: 0.396 },
  { config_id: 'D_u' as const, name: 'D_u', q_aa: 3.96, q_at: 0.396 },
]

/**
 * Recorded snapshot rows. step_index is the canonical 1-based completed-step
 * count; physical_time is illustrative MOCK data (the real values come from the
 * NPZ source). The sixth frame is the documented terminal endpoint.
 */
const SNAPSHOT_ROWS: { index: number; step: number; time: number }[] = [
  { index: 1, step: 0, time: 0 },
  { index: 2, step: 382, time: 0.016 },
  { index: 3, step: 764, time: 0.032 },
  { index: 4, step: 1146, time: 0.048 },
  { index: 5, step: 1529, time: 0.064 },
  { index: 6, step: 1912, time: 0.08 },
]

const FIELDS = [
  { field_id: 'density', label: 'Density', quantity: 'mass density' },
  { field_id: 'pressure', label: 'Pressure', quantity: 'pressure' },
  { field_id: 'front', label: 'Front indicator', quantity: 'shock front indicator' },
] as const

/** Case8 grid: 32 (y) x 128 (x), matching the documented face-array shape. */
const NX = 128
const NY = 32
const TOTAL_POINTS = 1912

const GRID_X: [number, number] = [0, 1]
const GRID_Y: [number, number] = [0, 1]

// --- shared header builders -------------------------------------------------

function mockUnit(quantity: string, label: string): UnitSpec {
  return {
    id: `mock.unit.${quantity.replace(/\s+/g, '-')}`,
    system: 'MODEL',
    quantity,
    label,
    si_mapping: null,
  }
}

function mockVerification(): ResultHeader['verification'] {
  return { status: 'NOT_APPLICABLE', basis: ['Mock provider: synthetic data, no scientific verification'], evidence_refs: [] }
}

function mockHeader(resultId: string, configId: string, semanticId: string, quantity: string, label: string, evidenceRefs: string[] = []): ResultHeader {
  return {
    result_id: resultId,
    experiment_id: 'case8',
    config_id: configId,
    semantic_id: semanticId,
    data_origin: MOCK_ORIGIN,
    availability: 'AVAILABLE',
    unit: mockUnit(quantity, label),
    verification: mockVerification(),
    evidence_refs: evidenceRefs,
    limitations: [LIM_MOCK],
  }
}

const LIM_MOCK: Limitation = {
  id: 'lim.mock.synthetic',
  code: 'MOCK_SYNTHETIC_DATA',
  description: 'Synthetic mock data for parallel frontend development; not real CFD output and not scientifically verified.',
  severity: 'WARNING',
}

// --- field generation -------------------------------------------------------

function fieldSignal(fieldId: string, configId: string, snapshotIndex: number, ix: number, iy: number): number {
  const t = SNAPSHOT_ROWS[snapshotIndex - 1]?.time ?? 0
  const configSeed = CONFIGS.findIndex((c) => c.config_id === configId) + 1
  const r = rng(configSeed * 7919 + snapshotIndex * 104729 + fieldId.length * 31)
  const noise = (r() - 0.5) * 0.04
  const x = ix / (NX - 1)
  const y = iy / (NY - 1)
  // A travelling front whose position depends on snapshot time.
  const front = 0.15 + 0.7 * (t / 0.08)
  const across = Math.exp(-Math.pow((x - front) / 0.045, 2))
  const lateral = 0.6 + 0.4 * Math.cos(Math.PI * y)
  const base = 1 + 0.9 * across * lateral + 0.05 * Math.sin(6 * x) * Math.cos(3 * y)
  if (fieldId === 'density') return base * (1.0 + 0.12 * configSeed * 0.25)
  if (fieldId === 'pressure') return base * base * (0.9 + 0.2 * configSeed * 0.25)
  // front indicator: sharp band marking the front
  return Math.min(1, Math.exp(-Math.pow((x - front) / 0.02, 2)) * lateral + 0.05 * noise * 10)
}

function buildFieldMeta(configId: string, snapshotIndex: number, fieldId: string): FieldMeta {
  const def = FIELDS.find((f) => f.field_id === fieldId) ?? FIELDS[0]
  const resultId = `mock.case8.${configId}.snapshot.${snapshotIndex}.${def.field_id}`
  return {
    field_id: def.field_id,
    label: def.label,
    unit_label: mockUnit(def.quantity, def.label).label,
    shape: [NY, NX],
    axes: ['y', 'x'],
    extent: { x: GRID_X, y: GRID_Y },
    verification_status: 'NOT_APPLICABLE',
    result: mockHeader(resultId, configId, `case8.${def.field_id}.snapshot`, def.quantity, def.label, [
      `mock.evidence.case8.${configId}.snapshot.${snapshotIndex}.${def.field_id}`,
    ]),
  }
}

// --- entropy series ---------------------------------------------------------

function buildSeries(configId: string, channel: 'E_bg' | 'E_aa' | 'E_at'): ScalarSeriesView {
  const r = rng(channel.length * 6151 + configId.charCodeAt(0) * 97)
  const points: ScalarPointView[] = []
  const cumulative = channel === 'E_at'
  let acc = 0
  const configSeed = CONFIGS.findIndex((c) => c.config_id === configId) + 1
  for (let step = 1; step <= TOTAL_POINTS; step += 1) {
    // Sampling the timeline coarsely keeps the mock small while still 1..1912.
    if (step % 8 !== 0 && step !== 1 && step !== TOTAL_POINTS) continue
    const frac = step / TOTAL_POINTS
    const stage = step <= 637 ? 0 : step <= 1274 ? 1 : 2
    const base = channel === 'E_bg' ? 0.35 : channel === 'E_aa' ? 0.5 : 0.85
    const inc = (base * (0.4 + 0.9 * frac) * (0.85 + 0.3 * (0.25 * configSeed))) / 8
    acc += cumulative ? inc : 0
    const value = cumulative ? acc : inc * (0.6 + 0.8 * frac) + (r() - 0.5) * 0.005
    points.push({
      point_index: points.length,
      step_index: step,
      source_step_index: step - 1,
      physical_time: (step / TOTAL_POINTS) * 0.08,
      value: Number(value.toFixed(6)),
    })
    void stage
  }
  const resultId = `mock.case8.${configId}.${channel}_${cumulative ? 'cumulative' : 'step'}`
  return {
    series_id: `mock.case8.${configId}.${channel}_${cumulative ? 'cumulative' : 'step'}`,
    label: channel === 'E_bg' ? 'E_bg (background production)' : channel === 'E_aa' ? 'E_aa (acoustic pathway)' : 'E_at (accumulated total)',
    aggregation: cumulative ? 'CUMULATIVE' : 'STEP_INCREMENT',
    unit: mockUnit('entropy production', 'model entropy units'),
    definition_id: `mock.def.case8.${channel}`,
    points,
    data_origin: MOCK_ORIGIN,
    verification: mockVerification(),
    result: mockHeader(resultId, configId, `case8.${channel}`, 'entropy production', 'model entropy units', [
      `mock.evidence.case8.${configId}.entropy.${channel}`,
    ]),
  }
}

// --- metrics ----------------------------------------------------------------

function buildMetrics(configId: string): MetricCollectionView {
  const r = rng(configId.charCodeAt(0) * 3571 + 11)
  const defs: Omit<MetricView, 'value' | 'unit'>[] = [
    {
      metric_id: 'width',
      display_label: 'Shock width',
      definition_id: 'mock.def.case8.width',
      definition_text: 'Front width measured from the density profile using the recorded width detector; terminal/instantaneous per detector scope.',
      detector_scope: 'case8.width.detector.v1 (native-face density profile)',
      time_scope_label: 'INSTANTANEOUS (displayed snapshot)',
      resolution_limit: 0.0025,
      evidence_refs: [`mock.evidence.case8.${configId}.metric.width`],
      availability: 'AVAILABLE',
      unavailable_reason: null,
    },
    {
      metric_id: 'front_rms',
      display_label: 'Front RMS',
      definition_id: 'mock.def.case8.front_rms',
      definition_text: 'RMS of the front-position residual over the recorded face band; not comparable with cylinder HF-RMS.',
      detector_scope: 'case8.front_band.detector.v1 (±0.08 window)',
      time_scope_label: 'TERMINAL (trajectory accumulated to final recorded step)',
      resolution_limit: 0.001,
      evidence_refs: [`mock.evidence.case8.${configId}.metric.front_rms`],
      availability: 'AVAILABLE',
      unavailable_reason: null,
    },
    {
      metric_id: 'hf',
      display_label: 'High-frequency energy',
      definition_id: 'mock.def.case8.hf',
      definition_text: 'High-frequency content above the recorded detector cutoff; defined per detector and NOT a universal ranking metric.',
      detector_scope: 'case8.hf.detector.v1 (cutoff recorded in definition)',
      time_scope_label: 'TERMINAL',
      resolution_limit: null,
      evidence_refs: [`mock.evidence.case8.${configId}.metric.hf`],
      availability: configId === 'A_u' ? 'PARTIAL' : 'AVAILABLE',
      unavailable_reason: configId === 'A_u' ? 'HF detector resolution limit is close to the measured value for A_u; treat with caution.' : null,
    },
  ]
  return {
    experiment_id: 'case8',
    config_id: configId,
    items: defs.map((d) => ({
      ...d,
      value: Number((0.2 + r() * 0.8).toFixed(4)),
      unit: mockUnit(d.metric_id === 'hf' ? 'energy fraction' : 'model length unit', d.metric_id === 'hf' ? 'dimensionless' : 'model units'),
    })),
  }
}

// --- evidence ---------------------------------------------------------------

function buildEvidenceSummaries(configId: string): EvidenceSummaryView[] {
  return [
    {
      evidence_id: `mock.evidence.case8.${configId}.entropy.E_at`,
      title: `Case8 ${configId} accumulated entropy history`,
      result_ids: [`mock.case8.${configId}.E_at_cumulative`],
      verification: mockVerification(),
      source_drift: false,
    },
    {
      evidence_id: `mock.evidence.case8.${configId}.metric.width`,
      title: `Case8 ${configId} shock width metric`,
      result_ids: [`mock.case8.${configId}.metric.width`],
      verification: mockVerification(),
      source_drift: null,
    },
    {
      evidence_id: `mock.evidence.case8.${configId}.snapshot.6.density`,
      title: `Case8 ${configId} recorded snapshot 6 density field`,
      result_ids: [`mock.case8.${configId}.snapshot.6.density`],
      verification: mockVerification(),
      source_drift: false,
    },
  ]
}

function buildEvidenceDetail(evidenceId: string): EvidenceDetailView | null {
  const match = /^mock\.evidence\.case8\.(\w+)\./.exec(evidenceId)
  if (!match) return null
  const configId = match[1]
  const drift = evidenceId.includes('snapshot') ? true : false
  return {
    evidence_id: evidenceId,
    schema_version: '1.0.0',
    supports: 'Frontend layout, navigation and provenance-display behaviour for the Case8 longitudinal slice (mock only).',
    does_not_support: 'Any scientific claim. This record is MOCK and verification is NOT_APPLICABLE.',
    experiment_id: 'case8',
    config_id: configId,
    config_parameters: CONFIGS.filter((c) => c.config_id === configId).map((c) => [
      { name: 'q_aa', value: String(c.q_aa) },
      { name: 'q_at', value: String(c.q_at) },
    ]).flat(),
    method_name: 'mock.method.case8 (synthetic)',
    method_hash: '0'.repeat(64),
    recorded_source_hash: drift ? 'a'.repeat(64) : 'b'.repeat(64),
    current_source_hash: drift ? 'c'.repeat(64) : 'b'.repeat(64),
    data_hash: null,
    verification: mockVerification(),
    source_drift: drift,
    source_assets: [
      {
        asset_id: `mock.asset.case8.${configId}.history`,
        source_display: 'Synthetic mock scalar log (not a real file)',
        role: 'DATA',
        recorded_hash: 'b'.repeat(64),
        current_hash: 'b'.repeat(64),
        drift: false,
        verification: mockVerification(),
      },
      {
        asset_id: `mock.asset.case8.${configId}.checkpoint`,
        source_display: 'Synthetic mock checkpoint (not a real file)',
        role: 'DATA',
        recorded_hash: drift ? 'a'.repeat(64) : 'b'.repeat(64),
        current_hash: drift ? 'c'.repeat(64) : 'b'.repeat(64),
        drift,
        verification: mockVerification(),
      },
    ],
    related_result_ids: [`mock.case8.${configId}.E_at_cumulative`],
    limitations: [LIM_MOCK],
    freeze_id: null,
    data_origin: MOCK_ORIGIN,
  }
}

// --- provider ---------------------------------------------------------------

/** Simulated latency so Loading states are real and cancellable. */
function delay<T>(value: Loaded<T>, signal: AbortSignal | undefined, ms = 90): Promise<Loaded<T>> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }
    const timer = setTimeout(() => resolve(value), ms)
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(timer)
        reject(new DOMException('Aborted', 'AbortError'))
      },
      { once: true },
    )
  })
}

function ok<T>(data: T, origin: DataOrigin = MOCK_ORIGIN): Loaded<T> {
  return { state: 'READY', data, origin, reason: null }
}

function fail<T>(state: Loaded<T>['state'], reason: string): Loaded<T> {
  return { state, data: null, reason, origin: MOCK_ORIGIN }
}

export function createMockProvider(): DataProvider {
  return {
    kind: 'MOCK',
    originLabel: 'MOCK · synthetic (NOT_APPLICABLE)',

    getProject(signal) {
      return delay(
        ok<ProjectView>({
          project_id: 'shockpath',
          name: 'ShockPath',
          tagline: 'A research digital-experiment and visual-analysis platform driven by a real CFD solver and frozen experiments.',
          scientific_question: 'What triggers numerical dissipation, where does it act, and how does it change modal and macroscopic flow behaviour?',
          mechanism_chain: [
            'Parameter',
            'Dissipation pathway',
            'Entropy production',
            'Trajectory budget',
            'Spatial allocation',
            'Modal response',
            'Macroscopic response',
          ],
          registry_revision: 'mock-registry-v1',
          data_revision: 'mock-no-scientific-data-v1',
        }),
        signal,
      )
    },

    listExperiments(signal) {
      const items: ExperimentCatalogEntry[] = [
        {
          experiment_id: 'case8',
          name: 'Case8',
          scientific_family: 'CFD Experiment Lab',
          summary: 'Four configs A_u/B_u/C_u/D_u · six recorded spatial snapshots + 1912 accepted-step scalar history.',
          delivery_status: 'IMPLEMENTED',
          availability_note: 'SUPPORTED · 6 snapshots + 1912 scalar steps (mock)',
          implementable_route: 'case8',
        },
        {
          experiment_id: 'gate',
          name: 'Gate Ablation',
          scientific_family: 'Allocation Explorer',
          summary: 'Three matched-budget static cumulative cell maps (Acoustic / Pressure / Ungated).',
          delivery_status: 'PLANNED',
          availability_note: null,
          implementable_route: null,
        },
        {
          experiment_id: 'spectrum',
          name: 'Spectrum',
          scientific_family: 'Spectral Lab',
          summary: 'Four q_at levels × ell 0…16 discrete spectra on a common zero-residual base state.',
          delivery_status: 'PLANNED',
          availability_note: null,
          implementable_route: null,
        },
        {
          experiment_id: 'cylinder',
          name: 'Mach3 Cylinder',
          scientific_family: 'Cross-flow Compare',
          summary: 'A_u/B_u/D_u · five instantaneous face frames + 16 cumulative angular sectors.',
          delivery_status: 'PLANNED',
          availability_note: null,
          implementable_route: null,
        },
      ]
      return delay(ok(items), signal)
    },

    getExperimentOverview(experimentId, signal) {
      if (experimentId !== 'case8') {
        return delay(
          fail<ExperimentOverview>('MISSING', `Experiment "${experimentId}" is not part of the Window 3 Case8 slice.`),
          signal,
          10,
        )
      }
      const overview: ExperimentOverview = {
        experiment_id: 'case8',
        name: 'Case8',
        description:
          'Channel shock experiment with four parameter configurations. Each config records 1912 accepted-step scalar points and six real spatial snapshots.',
        delivery_status: 'IMPLEMENTED',
        configurations: CONFIGS.map((c) => ({ ...c })),
        default_config: 'D_u',
        snapshot_count: 6,
        scalar_step_count: TOTAL_POINTS,
        protocol: {
          method_name: 'mock.method.case8 (synthetic)',
          integrator: 'RK-stage (recorded in source)',
          reconstruction: 'MUSCL (source metadata)',
          final_time: 0.08,
          grid: '32 × 128 cartesian',
        },
        limitation: LIM_MOCK,
      }
      return delay(ok(overview), signal)
    },

    listSnapshots(configId, signal) {
      if (!CONFIGS.some((c) => c.config_id === configId)) {
        return delay(fail<SnapshotMeta[]>('MISSING', `Unknown Case8 config "${configId}".`), signal, 10)
      }
      const items: SnapshotMeta[] = SNAPSHOT_ROWS.map((row) => ({
        snapshot_index: row.index,
        snapshot_id: `mock.case8.${configId}.snapshot.${row.index}`,
        step_index: row.step,
        physical_time: row.time,
        fields: FIELDS.map((f) => buildFieldMeta(configId, row.index, f.field_id)),
      }))
      return delay(ok(items), signal)
    },

    getSnapshotField(selector: SnapshotSelector, signal) {
      const { configId, snapshotIndex, fieldId } = selector
      const row = SNAPSHOT_ROWS.find((r) => r.index === snapshotIndex)
      if (!CONFIGS.some((c) => c.config_id === configId)) {
        return delay(fail<FieldData>('MISSING', `Unknown Case8 config "${configId}".`), signal, 10)
      }
      if (!row) {
        // Mirrors the frozen contract: snapshot_index 0 or >6 is a known-missing
        // recorded index (404 SNAPSHOT_NOT_FOUND), listing 1…6.
        return delay(
          fail<FieldData>('MISSING', `Snapshot index ${snapshotIndex} is not a recorded index. Case8 records snapshots 1…6.`),
          signal,
          10,
        )
      }
      const meta = buildFieldMeta(configId, snapshotIndex, fieldId)
      const r = rng(configId.charCodeAt(0) * 131 + snapshotIndex * 17 + fieldId.length)
      const values: number[] = new Array(NY * NX)
      for (let iy = 0; iy < NY; iy += 1) {
        for (let ix = 0; ix < NX; ix += 1) {
          values[iy * NX + ix] = Number((fieldSignal(fieldId, configId, snapshotIndex, ix, iy) + (r() - 0.5) * 0.01).toFixed(6))
        }
      }
      return delay(ok<FieldData>({ meta, values, data_origin: MOCK_ORIGIN }), signal, 140)
    },

    getEntropyHistory(configId, signal) {
      if (!CONFIGS.some((c) => c.config_id === configId)) {
        return delay(fail<EntropyHistoryView>('MISSING', `Unknown Case8 config "${configId}".`), signal, 10)
      }
      const history: EntropyHistoryView = {
        experiment_id: 'case8',
        config_id: configId,
        series: [buildSeries(configId, 'E_bg'), buildSeries(configId, 'E_aa'), buildSeries(configId, 'E_at')],
        total_point_count: TOTAL_POINTS,
        limitations: [LIM_MOCK],
      }
      return delay(ok(history), signal, 160)
    },

    getSnapshotAlignment(configId, scalarStep, policy, pinnedIndex, signal) {
      if (!CONFIGS.some((c) => c.config_id === configId)) {
        return delay(fail<SnapshotAlignmentView>('MISSING', `Unknown Case8 config "${configId}".`), signal, 10)
      }
      if (scalarStep < 1 || scalarStep > TOTAL_POINTS) {
        return delay(
          fail<SnapshotAlignmentView>('UNSUPPORTED', `Scalar step ${scalarStep} is outside the recorded range 1…${TOTAL_POINTS}.`),
          signal,
          10,
        )
      }
      const selectedTime = (scalarStep / TOTAL_POINTS) * 0.08
      let displayed: { index: number; step: number; time: number }
      if (policy === 'PINNED') {
        displayed = SNAPSHOT_ROWS.find((r) => r.index === pinnedIndex) ?? SNAPSHOT_ROWS[SNAPSHOT_ROWS.length - 1]
      } else {
        // NEAREST_RECORDED on physical time; ties resolve to the earlier time / smaller index.
        displayed = SNAPSHOT_ROWS.reduce((best, cur) =>
          Math.abs(cur.time - selectedTime) < Math.abs(best.time - selectedTime) ? cur : best,
        SNAPSHOT_ROWS[0])
      }
      const alignment: SnapshotAlignmentView = {
        experiment_id: 'case8',
        config_id: configId,
        selection_policy: policy,
        selected_scalar_step: scalarStep,
        selected_scalar_time: Number(selectedTime.toFixed(6)),
        displayed_snapshot_id: `mock.case8.${configId}.snapshot.${displayed.index}`,
        displayed_snapshot_index: displayed.index,
        displayed_snapshot_time: displayed.time,
        signed_time_delta: Number((displayed.time - selectedTime).toFixed(6)),
      }
      return delay(ok(alignment), signal, 40)
    },

    getMetrics(configId, signal) {
      if (!CONFIGS.some((c) => c.config_id === configId)) {
        return delay(fail<MetricCollectionView>('MISSING', `Unknown Case8 config "${configId}".`), signal, 10)
      }
      return delay(ok(buildMetrics(configId)), signal, 120)
    },

    listEvidenceForConfig(configId, signal) {
      if (!CONFIGS.some((c) => c.config_id === configId)) {
        return delay(fail<EvidenceSummaryView[]>('MISSING', `Unknown Case8 config "${configId}".`), signal, 10)
      }
      return delay(ok(buildEvidenceSummaries(configId)), signal, 80)
    },

    getEvidence(evidenceId, signal) {
      const detail = buildEvidenceDetail(evidenceId)
      if (!detail) {
        return delay(fail<EvidenceDetailView>('MISSING', `Evidence "${evidenceId}" is not a known mock record.`), signal, 10)
      }
      return delay(ok(detail), signal, 100)
    },
  }
}

export { CONFIGS as MOCK_CASE8_CONFIGS, SNAPSHOT_ROWS as MOCK_SNAPSHOT_ROWS, TOTAL_POINTS as MOCK_TOTAL_SCALAR_STEPS }
