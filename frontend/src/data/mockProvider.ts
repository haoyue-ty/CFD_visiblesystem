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
import type { DataProvider, SnapshotSelector, AllocationSelector, EigenmodeSelector, SpectralCurveSelector } from './provider'
import type { components } from '../types/generated/api'
type S_ErrorBody = components['schemas']['ErrorBody']
type S_ProvenanceRef = components['schemas']['ProvenanceRef']
type S_MaskSpec = components['schemas']['MaskSpec']
import type {
  AllocationArrayView,
  AllocationMaskView,
  AllocationSummaryView,
  AllocationView,
  DataOrigin,
  EigenmodeView,
  GrowthValidationView,
  SpectrumCurveView,
  SpectrumDatasetView,
  SpectralArrayView,
  SpectralDatasetRef,
  SpectralPointView,
  ValidationRunRef,
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

// --- allocation (Phase 6B) --------------------------------------------------
//
// Two representations, two scientific objects. The mock mirrors the recorded
// semantics in docs/handoffs/phase6/ALLOCATION_SEMANTICS_VERIFICATION.json:
//
//   Case8 D_u  FACE_FIELD  x-faces [32,129] + y-faces [32,128], two mask counts
//                          (640 / 648), spatial measure still required
//   Gate       CELL_FIELD  one [32,128] cell field, mask count 672,
//                          spatial measure already included
//
// Values are synthetic (seeded) but the SHAPES, MASK IDENTITIES and SUMMARY
// NUMBERS are the recorded ones so the frontend exercises the real contract.
// Note the summary budgets below are the recorded scientific values; the arrays
// are synthetic — the summary is NOT recomputed from the synthetic arrays.

const CASE8_ALLOC = {
  result_id: 'mock.case8.D_u.allocation',
  semantic_id: 'Case8_face_Pi_at_integrated',
  mask_id: 'mask.case8.native-face-shock-window',
  budget: 0.0027771079325925934,
  inside_fraction: 0.9980884346017243,
  mask_counts: [640, 648],
  dx: 1 / 128,
  dy: 1 / 32,
}

const GATE_ALLOC: Record<string, {
  q_at: number
  budget: number
  inside: number
  outside: number
  mask_count: number
}> = {
  Acoustic: { q_at: 0.4, budget: 0.0028004425253788713, inside: 0.9983067757919961, outside: 0.0016932242080059982, mask_count: 672 },
  Pressure: { q_at: 0.31018332312583474, budget: 0.0028430539591530325, inside: 0.9916868280217838, outside: 0.008313171978215123, mask_count: 672 },
  Ungated: { q_at: 0.03483470441226932, budget: 0.0028272752981764065, inside: 0.8923001329707689, outside: 0.10769986702923035, mask_count: 672 },
}

/** The prescribed initial front for BOTH windows (never an evolved front). */
function initialFront(y: number): number {
  return 0.5 + 0.0125 * Math.sin(8 * Math.PI * y)
}

/** A synthetic cumulative field on a shock-window band around the initial front. */
function allocationField(seed: number, shape: [number, number], location: 'X_FACE' | 'Y_FACE' | 'CELL'): { values: number[]; mask: boolean[]; count: number } {
  const [ny, nx] = shape
  const r = rng(seed)
  const values: number[] = new Array(ny * nx)
  const mask: boolean[] = new Array(ny * nx)
  let count = 0
  for (let j = 0; j < ny; j += 1) {
    // x-normal faces sample y at the row centre; y-normal faces at the row edge.
    const y = location === 'Y_FACE' ? j / ny : (j + 0.5) / ny
    const xs = initialFront(y)
    for (let i = 0; i < nx; i += 1) {
      const x = location === 'X_FACE' || location === 'CELL' ? (i + 0.5) / Math.max(nx - 1, 1) : i / nx
      const inWindow = Math.abs(x - xs) <= 0.08
      mask[j * nx + i] = inWindow
      if (inWindow) count += 1
      // Cumulative production concentrated on the window band (synthetic).
      const band = Math.exp(-Math.pow((x - xs) / 0.05, 2))
      values[j * nx + i] = Number(((inWindow ? band : 0.002 * band) * (0.7 + 0.6 * r())).toFixed(9))
    }
  }
  return { values, mask, count }
}

function allocationMask(id: string, type: AllocationMaskView['mask_type'], definition: string, counts: number[], evidenceRefs: string[]): AllocationMaskView {
  return { mask_id: id, mask_type: type, definition, counts, evidence_refs: evidenceRefs, verification: mockVerification() }
}

function allocationMetric(metricId: string, label: string, value: number, unitLabel: string, fraction: boolean, evidenceRefs: string[]) {
  return {
    metric_id: metricId, display_label: label, value, unit_label: unitLabel,
    definition_id: `mock.def.${metricId}`, fraction_format: fraction ? ('FRACTION' as const) : null, evidence_refs: evidenceRefs,
  }
}

/**
 * Case8 D_u FACE_FIELD — native x/y faces kept as TWO separate arrays.
 * The two orientations are never summed into one field here; the spatial rules
 * (dy, dx) are declared in the summary, not applied by the mock.
 */
function buildFaceAllocation(): AllocationView {
  const xSeed = 0x9e3779b1
  const ySeed = 0x85ebca6b
  const xField = allocationField(xSeed, [32, 129], 'X_FACE')
  const yField = allocationField(ySeed, [32, 128], 'Y_FACE')
  const evidenceRefs = ['mock.evidence.case8.D_u.allocation.map']

  const arrays: [AllocationArrayView, AllocationArrayView] = [
    {
      array_id: 'pi_at_x_faces', label: 'x-normal faces', location_type: 'CARTESIAN_X_FACE',
      shape: [32, 129], axes: ['y', 'x'], unit_label: 'model integrated entropy per model face length',
      values: xField.values,
    },
    {
      array_id: 'pi_at_y_faces', label: 'y-normal faces', location_type: 'CARTESIAN_Y_FACE',
      shape: [32, 128], axes: ['y', 'x'], unit_label: 'model integrated entropy per model face length',
      values: yField.values,
    },
  ]

  const mask = allocationMask(
    CASE8_ALLOC.mask_id,
    'CASE8_NATIVE_FACE_SHOCK_WINDOW',
    'Independent saved native x/y-face bool masks: abs(x - (0.5 + 0.0125*sin(8*pi*y))) <= 0.08; prescribed initial front, inclusive.',
    CASE8_ALLOC.mask_counts,
    evidenceRefs,
  )

  const outside = Number((1 - CASE8_ALLOC.inside_fraction).toPrecision(8))
  const summary: AllocationSummaryView = {
    total_budget: allocationMetric('mock.metric.case8.D_u.allocation.budget', 'Integrated E_at budget', CASE8_ALLOC.budget, 'model integrated entropy per model face length', false, evidenceRefs),
    inside: allocationMetric('mock.metric.case8.D_u.allocation.inside', 'Inside shock window', CASE8_ALLOC.inside_fraction, 'dimensionless', true, evidenceRefs),
    outside: allocationMetric('mock.metric.case8.D_u.allocation.outside', 'Outside shock window', outside, 'dimensionless', true, evidenceRefs),
    integration_interval: '[0,0.08]',
    time_scope_label: 'TERMINAL / TRAJECTORY_INTEGRATED · 1912 accepted steps',
    measure_definition: 'face integrated',
    includes_time_weights: true,
    includes_spatial_measure: false,
    integral_rule: 'dy*sum(xfaces)+dx*sum(yfaces)',
    measure_parameters: [
      { name: 'dx', value: CASE8_ALLOC.dx },
      { name: 'dy', value: CASE8_ALLOC.dy },
    ],
    evidence_refs: evidenceRefs,
  }

  return {
    representation_type: 'FACE_FIELD',
    measure_definition: 'face integrated',
    result_id: CASE8_ALLOC.result_id,
    experiment_id: 'case8',
    config_id: 'D_u',
    semantic_id: CASE8_ALLOC.semantic_id,
    title: 'D_u trajectory-integrated native-face Pi_at',
    definition: 'Saved time-integrated cross-mode entropy density on separate x/y normal faces.',
    time_rule: 'TERMINAL/TRAJECTORY_INTEGRATED [0,0.08], 1912 accepted steps; time/RK weights already included; no additional dt or RK weighting.',
    spatial_rule: 'dy*sum(pi_at_x_faces)+dx*sum(pi_at_y_faces); x boundary faces retained; periodic y seam counted once; duplicate residual y slot excluded.',
    data_origin: MOCK_ORIGIN,
    verification: mockVerification(),
    limitations: [LIM_MOCK],
    evidence_refs: evidenceRefs,
    coordinate_convention: 'Cartesian [y,x], C order on [0,1]^2; x-normal faces x=i/128, y=(j+0.5)/32; y-normal faces x=(i+0.5)/128, y=j/32.',
    mask,
    summary,
    arrays,
  }
}

/**
 * Gate CELL_FIELD — one 32×128 cell field. Spatial measure is already included:
 * the mock must not declare dx/dy for this representation.
 */
function buildCellAllocation(configId: string): AllocationView | null {
  const def = GATE_ALLOC[configId]
  if (!def) return null
  const field = allocationField(0x27d4eb2f ^ (configId.length * 7919), [32, 128], 'CELL')
  const evidenceRefs = [`mock.evidence.gate.${configId}.allocation.map`]

  const arrays: [AllocationArrayView] = [
    {
      array_id: 'pi_at_cells', label: 'cell field', location_type: 'CARTESIAN_CELL',
      shape: [32, 128], axes: ['y', 'x'], unit_label: 'model integrated entropy per cell',
      values: field.values,
    },
  ]

  const mask = allocationMask(
    'mask.gate.cell-shock-window',
    'GATE_CELL_SHOCK_WINDOW',
    'Cell-centre classification: abs(x - (0.5 + 0.0125*sin(8*pi*y))) <= 0.08; prescribed initial front, inclusive.',
    [def.mask_count],
    evidenceRefs,
  )

  const summary: AllocationSummaryView = {
    total_budget: allocationMetric(`mock.metric.gate.${configId}.allocation.budget`, 'Integrated E_at budget', def.budget, 'model integrated entropy per cell', false, evidenceRefs),
    inside: allocationMetric(`mock.metric.gate.${configId}.allocation.inside`, 'Inside shock window', def.inside, 'dimensionless', true, evidenceRefs),
    outside: allocationMetric(`mock.metric.gate.${configId}.allocation.outside`, 'Outside shock window', def.outside, 'dimensionless', true, evidenceRefs),
    integration_interval: '[0,0.08]',
    time_scope_label: 'STATIC / TRAJECTORY_INTEGRATED · frozen full-trajectory contributions',
    measure_definition: 'cell integrated',
    includes_time_weights: true,
    includes_spatial_measure: true,
    integral_rule: 'sum(cells); no additional dx/dy/dt',
    measure_parameters: [],
    evidence_refs: evidenceRefs,
  }

  return {
    representation_type: 'CELL_FIELD',
    measure_definition: 'cell integrated',
    result_id: `mock.gate.${configId}.allocation`,
    experiment_id: 'gate',
    config_id: configId,
    semantic_id: 'Gate_cell_Pi_at_integrated',
    title: `Gate ${configId} cumulative cell allocation`,
    definition: 'Frozen full-trajectory cell contributions of cross-mode entropy production.',
    time_rule: 'STATIC/TRAJECTORY_INTEGRATED [0,0.08]; frozen full-trajectory cell contributions; no map playback.',
    spatial_rule: 'sum(cells); interior face contributions split to neighbouring cells; full x-boundary contributions retained.',
    data_origin: MOCK_ORIGIN,
    verification: mockVerification(),
    limitations: [LIM_MOCK],
    evidence_refs: evidenceRefs,
    coordinate_convention: 'Cartesian [y,x], C order on [0,1]^2; cell centres x=(i+0.5)/128, y=(j+0.5)/32.',
    mask,
    summary,
    arrays,
  }
}

/** Build the requested allocation, or null when the selector is not in scope. */
function buildAllocation(selector: AllocationSelector): AllocationView | null {
  if (selector.experimentId === 'case8') return selector.configId === 'D_u' ? buildFaceAllocation() : null
  return buildCellAllocation(selector.configId)
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

// --- Phase 7B spectral mock --------------------------------------------------
//
// A spectral curve is 17 DISCRETE Fourier blocks for ONE recorded q_at. The mock
// NEVER interpolates q and never draws a smooth curve: each block is a separate
// sample. `Re(lambda)` is strongest at low ell and decays, which is the shape the
// frozen adapter observes — but these numbers are SYNTHETIC and must never be
// cited as science. Every record is namespaced `mock.` and carries MOCK origin.
const SPECTRAL_Q_AT = [0, 0.132, 0.264, 0.396] as const

/** Deterministic mock spectrum dataset identities. */
function mockSpectralDatasets(): SpectralDatasetRef[] {
  return SPECTRAL_Q_AT.map(q => ({ dataset_id: `mock.spectrum.q-${q.toFixed(3)}`, q_at: q, configuration_id: `mock.configuration.q-${q.toFixed(3)}` }))
}

function mockWaveNumbers(): number[] {
  // Registered wave numbers correspond to the 17 recorded modes 0..16; the mock
  // uses a simple monotone placeholder — the definition text states it is mock.
  return Array.from({ length: 17 }, (_, k) => Number((k * (1 / 16)).toFixed(6)))
}

function mockSpectralHeader(datasetId: string, qAt: number): ResultHeader {
  return {
    result_id: `mock.result.${datasetId}`,
    experiment_id: 'spectrum',
    config_id: datasetId,
    semantic_id: 'SpectralRe_lambda',
    data_origin: MOCK_ORIGIN,
    availability: 'AVAILABLE',
    unit: mockUnit('growth_rate', 'rate (model units)'),
    verification: mockVerification(),
    evidence_refs: [`mock.evidence.${datasetId}`],
    limitations: [LIM_MOCK],
    // q_at is echoed by callers; the header itself carries no q field.
  } as ResultHeader & { q_at?: number }
}

/** Mock ProvenanceRef — same shape as the wire record, entirely synthetic. */
function mockProvenance(evidenceRefs: string[]): S_ProvenanceRef {
  return {
    evidence_refs: evidenceRefs, source_asset_ids: [],
    registry_revision: 'mock-registry-v1', data_revision: 'mock-no-scientific-data-v1',
    release_id: { state: 'NOT_APPLICABLE', reason: 'Mock provider has no frozen release.' },
    source_drift: { state: 'NOT_APPLICABLE', reason: 'Mock provider has no source assets.' },
  } as S_ProvenanceRef
}

function mockSpectralPoints(datasetId: string, qAt: number): SpectralPointView[] {
  // Re is strongest at ell 0 and decays with ell; q shifts the peak slightly.
  return Array.from({ length: 17 }, (_, k) => {
    const decay = Math.exp(-0.18 * k)
    const real = Number(((0.28 + qAt * 0.1) * decay - 0.02).toFixed(6))
    const imag = Number(((0.42 * decay) * Math.sign(Math.sin(k / 2))).toFixed(6))
    const abscissa = Number(real.toFixed(6))
    return {
      q_at: qAt, verification: mockVerification(),
      provenance: mockProvenance([`mock.evidence.${datasetId}.mode-${k}`]),
      result: mockSpectralHeader(datasetId, qAt),
      representation: 'SPECTRUM_POINT' as const,
      spectrum_record_id: `mock.spectrum-record.${datasetId}.mode-${String(k).padStart(2, '0')}`,
      mode_index: k,
      wave_number: mockWaveNumbers()[k],
      real_lambda: real, imag_lambda: imag, spectral_abscissa: abscissa, eigenvalue_rank: 0 as const,
    }
  })
}

function mockSpectralCurve(selector: SpectralCurveSelector): SpectrumCurveView | null {
  const qAt = SPECTRAL_Q_AT.find(q => selector.datasetId === `mock.spectrum.q-${q.toFixed(3)}`)
  if (qAt === undefined) return null
  const datasetId = selector.datasetId
  return {
    q_at: qAt, verification: mockVerification(),
    provenance: mockProvenance([`mock.evidence.${datasetId}`]),
    result: mockSpectralHeader(datasetId, qAt),
    representation: 'SPECTRUM_CURVE', dataset_id: datasetId,
    collection_id: 'mock.spectrum.common', base_result_id: 'mock.spectrum.common.base',
    configuration_id: `mock.configuration.q-${qAt.toFixed(3)}`,
    points: mockSpectralPoints(datasetId, qAt),
  }
}

function mockEigenmode(selector: EigenmodeSelector): EigenmodeView | null {
  const qAt = SPECTRAL_Q_AT.find(q => selector.datasetId === `mock.spectrum.q-${q.toFixed(3)}`)
  if (qAt === undefined) return null
  if (!Number.isInteger(selector.modeIndex) || selector.modeIndex < 0 || selector.modeIndex > 16) return null
  // The saved vectors exist only for ranks 0..3 in the mock; a higher rank is a
  // reason-bearing MISSING (the panel shows "Unavailable", never an empty frame).
  if (selector.rank > 3) return null
  const datasetId = selector.datasetId
  const record = `mock.spectrum-record.${datasetId}.mode-${String(selector.modeIndex).padStart(2, '0')}`
  const isProfile = selector.representation === 'PRIMITIVE_PROFILE'
  return {
    q_at: qAt, verification: mockVerification(),
    provenance: mockProvenance([`mock.evidence.${record}`]),
    result: mockSpectralHeader(datasetId, qAt),
    representation: 'EIGENMODE',
    eigenmode_id: `${record}.${selector.side.toLowerCase()}.rank-${String(selector.rank).padStart(2, '0')}.${isProfile ? 'primitive_profile' : 'complex_vector'}.${selector.fieldComponent}`,
    spectrum_record_id: record, dataset_id: datasetId, mode_index: selector.modeIndex,
    side: selector.side, rank: selector.rank, field_component: selector.fieldComponent,
    eigen_representation: selector.representation, projection: selector.projection,
    shape: isProfile ? [128] : [128, 4],
    normalization: {
      id: 'mock.normalization.unknown',
      definition: null, phase_convention: null, component_order: null, processing_ref: null,
    },
    // LEFT localization is genuinely absent in the frozen source; the mock mirrors
    // that by leaving it unresolved for LEFT rather than inventing a value.
    localization_fraction: selector.side === 'RIGHT' ? 0.62 : null,
    localization_definition: 'Fraction of RIGHT primitive energy inside the fixed x-cell mask (mock).',
    mask_reference: { id: 'mock.mask.spectrum.fixed-shock-cells', type: 'SPECTRUM_FIXED_SHOCK_CELLS', definition: 'Mock fixed x-cell shock window 58..66 (zero based).', counts: [9], evidence_refs: [] } as unknown as S_MaskSpec,
    values_ref: {
      result_id: `mock.result.${datasetId}`,
      array_id: `${record}.${selector.side.toLowerCase()}.rank-${String(selector.rank).padStart(2, '0')}`,
      shape: isProfile ? [128] : [128, 4],
      dtype: isProfile ? 'float64' : 'complex128',
    },
    evidence_refs: [`mock.evidence.${record}`],
  }
}

function mockValidationRuns(): ValidationRunRef[] {
  const runs: ValidationRunRef[] = []
  for (const mode of [1, 4, 8, 12]) {
    for (const eps of [1e-4, 1e-5, 1e-6]) {
      runs.push({
        run_id: `mock.modal-validation.m${String(mode).padStart(2, '0')}_q0p396_eps${eps.toExponential(0).replace('e-', 'e-0')}`,
        label: `mode ${mode} · q_at=0.396 · ε=${eps.toExponential(0)}`,
        mode_index: mode, q_at: 0.396, epsilon: eps,
      })
    }
  }
  return runs
}

function mockGrowthValidation(runId: string): GrowthValidationView | null {
  const run = mockValidationRuns().find(item => item.run_id === runId)
  if (!run) return null
  const time = Array.from({ length: 33 }, (_, i) => Number((i * 0.0025).toFixed(6)))
  const cfd = time.map(t => Number((1e-4 * Math.exp(1.62 * t)).toFixed(10)))
  // The linear amplitude history was NOT saved in the frozen source. The mock
  // mirrors that as an all-null, reason-bearing MISSING series — it is never a
  // synthesized exponential.
  const linear: (number | null)[] = time.map(() => null)
  return {
    q_at: run.q_at, verification: mockVerification(),
    provenance: mockProvenance([`mock.evidence.${runId}`]),
    result: mockSpectralHeader(`mock.spectrum.q-0.396`, run.q_at),
    representation: 'GROWTH_VALIDATION', run_id: runId, mode_index: run.mode_index, epsilon: run.epsilon,
    spectrum_record_id: `mock.spectrum-record.mock.spectrum.q-0.396.mode-${String(run.mode_index).padStart(2, '0')}`,
    eigenmode_id: `mock.eigenmode.mode-${run.mode_index}.rank-00`,
    time, step_indices: Array.from({ length: 33 }, (_, i) => i),
    linear_amplitude: linear, cfd_amplitude: cfd,
    growth_rate: { linear: 1.61, rk3: 1.63, cfd: 1.62 },
    error: {
      absolute_discrepancy: 0.01, relative_discrepancy: 0.00613, relative_discrepancy_format: 'FRACTION',
      definition: 'ABS_SIGMA_CFD_MINUS_RK3_OVER_MAX_ABS_RK3_1', definition_id: 'mock.growth.error.definition',
      evidence_refs: [`mock.evidence.${runId}`],
    },
    amplitude_definition: 'ABS_PROJECTED_COEFFICIENT', fit_start: 0, fit_end: 32, fit_point_count: 33,
    issues: [{ code: 'MISSING_ASSET', message: 'Linear amplitude history was not saved for this run; only the recorded rate and the CFD history are available.', target: { resource_type: 'growth_validation', identity: { state: 'KNOWN', value: runId } } } as unknown as S_ErrorBody],
  }
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

    // --- Phase 6B allocation -------------------------------------------------

    describeAllocation(selector, signal) {
      const allocation = buildAllocation(selector)
      if (!allocation) {
        // A/B/C have no recorded cumulative map. This is a known capability gap,
        // not a synthesised zero field.
        const reason =
          selector.experimentId === 'case8'
            ? `Case8 config "${selector.configId}" has no recorded cumulative native-face map; only D_u does.`
            : `Gate config "${selector.configId}" is not one of the frozen variants (Acoustic / Pressure / Ungated).`
        return delay(fail<AllocationView>('MISSING', reason), signal, 10)
      }
      return delay(ok(allocation), signal, 150)
    },

    loadAllocationMask(selector, signal) {
      const allocation = buildAllocation(selector)
      if (!allocation) {
        return delay(fail<AllocationMaskView>('MISSING', `No allocation mask for ${selector.experimentId}/${selector.configId}.`), signal, 10)
      }
      return delay(ok(allocation.mask), signal, 60)
    },

    loadAllocationSummary(selector, signal) {
      const allocation = buildAllocation(selector)
      if (!allocation) {
        return delay(fail<AllocationSummaryView>('MISSING', `No allocation summary for ${selector.experimentId}/${selector.configId}.`), signal, 10)
      }
      return delay(ok(allocation.summary), signal, 80)
    },

    // --- Phase 7B spectral ---------------------------------------------------

    listSpectra(signal) {
      return delay(ok<SpectralDatasetRef[]>(mockSpectralDatasets()), signal, 60)
    },

    getSpectrumDataset(selector, signal) {
      const curve = mockSpectralCurve(selector)
      if (!curve) {
        return delay(fail<SpectrumDatasetView>('MISSING', `Spectrum dataset "${selector.datasetId}" is not one of the four registered q_at configurations.`), signal, 10)
      }
      return delay(ok<SpectrumDatasetView>({
        q_at: curve.q_at, verification: curve.verification, provenance: curve.provenance, result: curve.result,
        representation: 'SPECTRUM_DATASET', dataset_id: curve.dataset_id, collection_id: curve.collection_id,
        base_result_id: curve.base_result_id, configuration_id: curve.configuration_id,
        mode_indices: Array.from({ length: 17 }, (_, k) => k), wave_numbers: mockWaveNumbers(),
        wave_number_definition: 'Mock wave numbers for the 17 recorded Fourier blocks (ell 0..16).',
        matrix_availability: 'MISSING', evidence_refs: curve.provenance.evidence_refs,
      }), signal, 90)
    },

    getSpectralCurve(selector, signal) {
      const curve = mockSpectralCurve(selector)
      if (!curve) {
        return delay(fail<SpectrumCurveView>('MISSING', `No recorded spectral curve for dataset "${selector.datasetId}".`), signal, 10)
      }
      return delay(ok<SpectrumCurveView>(curve), signal, 120)
    },

    getEigenmode(selector, signal) {
      const view = mockEigenmode(selector)
      if (!view) {
        // Distinguish an unregistered selection from a registered-but-unsaved one.
        const known = SPECTRAL_Q_AT.some(q => selector.datasetId === `mock.spectrum.q-${q.toFixed(3)}`)
        if (!known || selector.modeIndex < 0 || selector.modeIndex > 16) {
          return delay(fail<EigenmodeView>('MISSING', `Eigenmode selection (mode ${selector.modeIndex}) is not a recorded block for "${selector.datasetId}".`), signal, 10)
        }
        return delay(fail<EigenmodeView>('MISSING', `No saved eigenmode vector for rank ${selector.rank}; only ranks 0..3 are saved in this mock.`), signal, 10)
      }
      return delay(ok<EigenmodeView>(view), signal, 110)
    },

    getGrowthValidation(runId, signal) {
      const view = mockGrowthValidation(runId)
      if (!view) {
        return delay(fail<GrowthValidationView>('MISSING', `Validation run "${runId}" is not a registered recorded run.`), signal, 10)
      }
      // PARTIAL: the run's rates and CFD history exist, the linear amplitude
      // history does not. A missing prediction stays an explicit MISSING fact.
      return delay({ state: 'PARTIAL', data: view, origin: MOCK_ORIGIN, reason: 'Linear/RK3 amplitude histories were not saved; only recorded rates and the CFD history are available.' }, signal, 130)
    },

    listValidationRuns(signal) {
      return delay(ok<ValidationRunRef[]>(mockValidationRuns()), signal, 60)
    },

    loadSpectralArray(ref, signal) {
      const datasetId = ref.result_id.replace(/^mock\.result\./, '')
      const qAt = SPECTRAL_Q_AT.find(q => datasetId === `mock.spectrum.q-${q.toFixed(3)}`)
      if (qAt === undefined) {
        return delay(fail<SpectralArrayView>('MISSING', `No saved array for result "${ref.result_id}".`), signal, 10)
      }
      const isComplex = ref.dtype === 'complex128'
      // A deterministic, synthetic vector/profile. The envelope shape and the
      // dtype are respected so the renderer exercises the real projection paths.
      const values: number[] | [number, number][] = isComplex
        ? Array.from({ length: 128 * 4 }, (_, i) => {
            const t = i / (128 * 4)
            return [Number((Math.sin(t * Math.PI * 6) * Math.exp(-2 * t)).toFixed(6)),
                    Number((Math.cos(t * Math.PI * 5) * Math.exp(-2 * t)).toFixed(6))] as [number, number]
          })
        : Array.from({ length: 128 }, (_, i) => {
            const t = i / 128
            return Number((Math.exp(-Math.pow((t - 0.62) / 0.09, 2))).toFixed(6))
          })
      return delay(ok<SpectralArrayView>({
        result_id: ref.result_id, array_id: ref.array_id, shape: ref.shape, dtype: ref.dtype, values,
      }), signal, 90)
    },
  }
}

export { CONFIGS as MOCK_CASE8_CONFIGS, SNAPSHOT_ROWS as MOCK_SNAPSHOT_ROWS, TOTAL_POINTS as MOCK_TOTAL_SCALAR_STEPS }
export { GATE_ALLOC as MOCK_GATE_ALLOCATION_CONFIGS }
