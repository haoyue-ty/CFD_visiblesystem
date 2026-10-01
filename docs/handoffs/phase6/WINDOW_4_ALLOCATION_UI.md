WINDOW=4_ALLOCATION_UI
STATUS=PASS
BRANCH=phase6/allocation-ui
BASE=phase6/case8-du-allocation
SCOPE=Vue + ECharts frontend only; no scientific files read or modified; no CFD
==================================================
DEPENDS_ON
  Window 0  dev/docs/handoffs/phase6/ALLOCATION_FOUNDATION_DESIGN.md  (representation vocabulary, masks, measures)
  Window 3  docs/handoffs/phase6/WINDOW_3_ALLOCATION_API.md           (ALLOC01-ALLOC04 routes + generated types)
  Semantics docs/handoffs/phase6/ALLOCATION_SEMANTICS_VERIFICATION.json (recorded budgets/fractions/mask counts)
==================================================
FACE_VIEW=FACE_FIELD
  Case8 D_u only. Native x/y normal faces kept as TWO separate figures.
  - arrays: pi_at_x_faces [32,129] (CARTESIAN_X_FACE) + pi_at_y_faces [32,128] (CARTESIAN_Y_FACE)
  - measure: "face integrated"; integral_rule "dy*sum(xfaces)+dx*sum(yfaces)"
  - includes_spatial_measure=FALSE -> summary shows "no (dx/dy still required)"
  - mask: mask.case8.native-face-shock-window / CASE8_NATIVE_FACE_SHOCK_WINDOW
  - mask counts: 640, 648 (per orientation, never merged)
  - semantic: Case8_face_Pi_at_integrated; origin DIAGNOSTIC_RERUN; TERMINAL/TRAJECTORY_INTEGRATED [0,0.08]
  - renderer: FaceAllocationView.vue (own canvas per orientation, native shape, face-grid overlay)
CELL_VIEW=CELL_FIELD
  Gate Acoustic / Pressure / Ungated, all three reachable.
  - array: pi_at_cells [32,128] (CARTESIAN_CELL), single field
  - measure: "cell integrated"; integral_rule "sum(cells); no additional dx/dy/dt"
  - includes_spatial_measure=TRUE -> summary shows "yes (do not multiply again)"
  - mask: mask.gate.cell-shock-window / GATE_CELL_SHOCK_WINDOW; count 672
  - semantic: Gate_cell_Pi_at_integrated; origin FROZEN_PRODUCTION; STATIC/TRAJECTORY_INTEGRATED [0,0.08]
  - recorded summaries: Acoustic 0.0028004425253788713 / Pressure 0.0028430539591530325 / Ungated 0.0028272752981764065
  - renderer: CellAllocationView.vue (cell-centre raster, distinct component)
TWO_OBJECTS_NOT_ONE=ENFORCED
  representation_type is the discriminant of the view union (FaceAllocationView|CellAllocationView),
  so the template cannot route one through the other. Separate mask identity, separate measure rule,
  separate integral rule, separate raster, separate array cardinality (2 vs 1). A dedicated test
  asserts the four headline fields differ and that face=2/0 canvases vs cell=0/1.
  No heatmap projection, no face->cell averaging, no recentring on evolved fronts.
==================================================
PAGE_SHOWS
  representation_type  -> data-testid alloc-representation-type
  mask                 -> alloc-mask (id/type/counts/definition)
  definition           -> alloc-definition (definition + title + time/spatial rule + coordinates)
  verification         -> alloc-verification (status + basis + limitations)
  evidence             -> alloc-evidence (EvidenceLink per evidence_ref)
  plus summary         -> allocation-summary (budget/inside/outside + measure rule + parameters)
==================================================
FUNCTIONALITY
  Case8 D_u                -> FACE_FIELD allocation map + summary   [OK]
  Gate Acoustic            -> CELL_FIELD allocation map + summary   [OK]
  Gate Pressure            -> CELL_FIELD allocation map + summary   [OK]
  Gate Ungated             -> CELL_FIELD allocation map + summary   [OK]
  A/B/C allocation tab     -> stays DISABLED with reason (unchanged behaviour)
PROVIDER_ABSTRACTION=PRESERVED
  DataProvider gained describeAllocation / loadAllocationMask / loadAllocationSummary (AllocationSelector).
  MOCK provider: deterministic seeded builders mirroring the recorded shapes/masks/summaries.
  API provider: real ALLOC01/ALLOC03 calls (ALLOC02 for arrays) via generated types; result ids
  case8.<cfg>.allocation / gate.<cfg>.allocation. No page knows which provider is active.
  MOCK origin forces verification=NOT_APPLICABLE and origin=MOCK on every result.
API_DEGRADATION=HONEST
  The concrete allocation loader is not injected at runtime, so the backend answers
  503 FEATURE_NOT_ENABLED ("Allocation adapter has not been delivered"). Classified to the
  UI state UNSUPPORTED with the backend message; no invented empty array, no zero field,
  no silent fallback to MOCK. Verified by tests/allocation-real-api.spec.ts (no mock-badge on real API).
==================================================
NOT_DONE (constraints honoured)
  NO UI beautification, NO animation, NO 3D. Plain tables, DLs and pixel-exact canvases only.
==================================================
EVIDENCE_LINK=alloc-evidence -> EvidenceLink -> /evidence/:evidence_id with back-query
  mock refs: mock.evidence.case8.D_u.allocation.map ; mock.evidence.gate.<cfg>.allocation.map
BUILD=PASS
  npm run build = vue-tsc --noEmit && vite build -> 0 errors
  dist/assets/index-*.js 1,313.90 kB (gzip 437.09 kB)
TESTS=PASS
  window4-allocation-ui (mock)  10/10 PASS  tests/window4_allocation/allocation_ui.spec.ts
  window3-mock-development      16/16 PASS  no regression
  real-api (full)               24/24 PASS  incl. allocation-real-api.spec.ts + no-mock-fallback
  backend pytest                404/404 PASS
FROZEN_CONTRACTS=UNCHANGED
  04_SYSTEM_ARCHITECTURE.md / 05_DATA_SCHEMA.md / 06_API_CONTRACT.md sha256 match the Phase 4 manifest.
MOCK_IN_PRODUCTION=NO
  Production bundle scanned: 0 hits for mock scientific values, mask ids, MOCK_SYNTHETIC_DATA,
  createMockProvider and the mulberry32 PRNG. Mock provider is registered only under import.meta.env.DEV.
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
==================================================
FILES_CHANGED
  new: frontend/src/views/case8/AllocationTab.vue
  new: frontend/src/scientific/FaceAllocationView.vue
  new: frontend/src/scientific/CellAllocationView.vue
  new: frontend/src/scientific/AllocationSummary.vue
  new: tests/window4_allocation/allocation_ui.spec.ts
  new: frontend/tests/allocation-real-api.spec.ts
  mod: frontend/src/data/domain.ts        (allocation view union)
  mod: frontend/src/data/provider.ts      (3 allocation methods + AllocationSelector)
  mod: frontend/src/data/mockProvider.ts  (Case8 FACE + Gate CELL builders)
  mod: frontend/src/data/apiProvider.ts   (ALLOC01/02/03 mapping + honest degradation)
  mod: frontend/src/data/index.ts         (dataService accessors + type re-exports)
  mod: frontend/src/scientific/index.ts   (export 3 components)
  mod: frontend/src/pages/ExperimentPage.vue (mount AllocationTab, refresh tab note)
  mod: frontend/playwright.config.ts      (window4-allocation-ui project)
NEXT=WINDOW_5 (integration / acceptance on the frozen allocation surface)
