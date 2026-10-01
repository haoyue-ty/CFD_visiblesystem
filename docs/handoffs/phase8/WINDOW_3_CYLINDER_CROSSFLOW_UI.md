WINDOW=3_CYLINDER_CROSSFLOW_UI
STATUS=PASS
BRANCH=phase8/cylinder-crossflow-ui
BASE_COMMIT=34fbb56
WORKTREE=D:/code_project/CFD_visiblesystem_phase8_cylinder_crossflow_ui

CYLINDER_PAGE=PASS
FLOW=PASS
ENTROPY=PASS
SECTOR_ALLOCATION=PASS
METRICS=PASS
CROSS_FLOW_PAGE=PASS

CUMULATIVE_2D_MISSING_VISIBLE=YES
NO_UNIFIED_RANKING=YES
MOCK_IN_PRODUCTION=NO
MOCK_PRODUCTION_BUNDLE_SCAN_HITS=0

BUILD=PASS (vue-tsc --noEmit + vite build)
TESTS=PASS (33/33 production-browser tests; 80/80 Cylinder/Cross-flow API tests)
SCIENTIFIC_FILES_MODIFIED=NO
BACKEND_AND_GENERATED_CONTRACT_MODIFIED=NO
CFD_RUNS_STARTED=0
FROZEN_DOCS_MODIFIED=NO
ORIGINAL_PHASE7_WORKING_CHANGES_PRESERVED=YES
STOP=Window 3 complete

Routes: `/lab/experiments/cylinder` and `/cross-flow` (alias
`/lab/compare/case8-cylinder`). Lab and Case8/Cylinder details link to the comparison.

Cylinder has exactly Overview / Flow / Entropy / Sector Allocation / Metrics /
Evidence and A_u / B_u / D_u. Five recorded native-face checkpoints expose index,
completed step, physical time and field availability. Native sample rasters retain
their radial/angular index axes, colour range and units. Missing density, absent
fields and source failures have explicit states; no replacement frames are drawn.

The scalar view joins two real API pages (5000 + 4757) for each of four canonical
cumulative series, validates record continuity and preserves the original page
metadata separately. All 9757 endpoints per series render without downsampling.
Scalar-step selection and snapshot selection remain independent URL state.
Definitions, model units, interior scope, source-step indexing, accepted intervals
and endpoint time semantics remain visible with evidence links.

Allocation draws four saved channel arrays on the 16 native angular bins, retaining
the 17 saved radian edges and backend-provided sector fractions. The front-band
REGION_SCALAR shows its canonical fraction, integrated value, denominator,
definition, mask, parameters, scope and evidence. Undefined zero-denominator
fractions remain N/A. Full trajectory cumulative 2D Pi_at is Unavailable / Missing,
with a capability banner on every Cylinder tab and a gap card in Sector Allocation.
There is no reconstructed cumulative heatmap.

Local metrics display the canonical backend values, including centerline width,
front-mean width, front RMS and HF-RMS. Each retains its definition, detector and
parameters, unit, time, scope, evidence and limitations. Detector-floor warnings
and the distinction between nominal mesh spacing and uncertainty remain visible.

P07 uses Case8 native-face cumulative maps and local canonical metrics on the left;
Cylinder angular sectors, fixed front-band scalar and its local canonical metrics
on the right. The page prominently declares DESCRIPTIVE_ONLY and
NO_UNIFIED_RANKING. A separate Comparability Rules section preserves all four
backend rules for localization, HF, width and budget. No ratios, scores,
normalizations or cross-case ranking are computed in the frontend. Case8 configs
without a saved cumulative map retain explicit Missing and their local metrics.

Every result/plot offers registered evidence. Evidence links carry the complete
originating route/query; returning restores config, tab, snapshot, scalar step,
field and comparison state. Request guards cancel stale loads on selector changes
and unmount. Production API failures never select the mock provider.

Validation commands (PowerShell 7):

```powershell
# From frontend; E2E_PYTHON can reuse an existing verified environment.
npm ci
npm run build
$env:E2E_PYTHON = 'D:/code_project/CFD_visiblesystem/.venv/Scripts/python.exe'
npx playwright test --config playwright.phase8.config.ts

# From the worktree root.
& 'D:/code_project/CFD_visiblesystem/.venv/Scripts/python.exe' -m pytest -q tests/window2_cylinder_crossflow_api
```

The 33 browser tests comprise 21 new Cylinder/Cross-flow cases and 12 existing
Case8, allocation and route regressions. They cover all A/B/D snapshots and sectors,
missing fields, complete history, metric context and detector floor, both evidence
returns, independent selector state, API outages, production bundle scan and config
switching. Browser screenshots were inspected to confirm the distinct renderers.
Machine-readable browser results: `.cache/phase8/playwright-window3.json`.

Vite reports the existing large single-chunk size warning; build and typecheck pass.
This window did not rerun the entire historical Python suite. The inherited
Phase5 CRLF/LF freeze-byte baseline discrepancy remains documented by Window 2;
no freeze or source data was changed. No final visual polish was performed.
