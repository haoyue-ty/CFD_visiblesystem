WINDOW=3_CLOSURE_FRONTEND
STATUS=PASS

OVERVIEW=PASS
SEMIDISCRETE=PASS
FULLY_DISCRETE=PASS
REFINEMENT=PASS
BU_ZERO_CHANNEL=PASS
NO_SPATIAL_TRAJECTORY=PASS
EVIDENCE=PASS

BUILD=PASS
TESTS=21/21 production browser; 192/192 W1+W2 backend scope; 0 failures, 0 skipped
MOCK_IN_PRODUCTION=NO

Branch: `phase9/closure-ui`, based on the accepted Window2 checkout with accepted
Window1 integrated. Backend, OpenAPI, generated types, source manifests, and the
Window0 source map remain unchanged. No final UI styling pass was performed.

The experiment dispatch opens Entropy Closure at
`/lab/experiments/entropy-closure`. Its only tabs are Overview, Semi-discrete,
Fully-discrete, and Evidence. The sole run selector consumes CLO01's five
complete selections in registry order; it does not construct config/CFL pairs.
Unregistered run links show an unsupported-selection explanation and issue no
history requests. Unsupported view links explain the absent spatial capability.
Overview explicitly shows `Spatial trajectory: MISSING / not recorded`.

PER_STAGE charts compare G with -D_total, explicitly labelled as a display sign
change; recorded D_total remains unchanged in the value table. R_SD and eps_SD
use their own units and retain their backend Evidence definitions. D_bg, D_aa,
D_at, R_decomp and other saved columns are selectable. The stage axis is source
record ordinal; source stages, accepted step, original clock, and recorded
interval are inspectable. `3 RK stages per accepted step` and actual stage-state
time `NOT_ESTABLISHED` remain visible. No stage-state timeline is synthesized.

PER_STEP separates DeltaS/E_obs_step increments, R_time_step increments,
recorded R_time_cumulative, existing channel increments, and terminal R_total.
Other saved columns are inspectable. Terminal summaries remain separate from
per-step histories. The fully-discrete numerical-diagnostic limitation is
visible on all four tabs. No exact fully-discrete entropy identity is claimed.
B_u displays `D_at=0 — recorded zero channel`; actual D_at, E_at_step and
E_at_total values are tested against zero.

Histories use explicit pages of 1,000 saved rows. Every recorded row is reachable
using Previous/Next/Last, with the current range and total count visible. Charts
show only the labelled page; zoom does not synthesize values. Requests use the
frozen API pagination parameters. The frontend verifies run/granularity,
result owners, counts, ordinals, source steps and canonical/source stages.
Aborted or stale requests cannot appear under a new run selection.

Refinement displays exactly four D_u CFL values (0.2, 0.1, 0.05, 0.025) against
the corresponding terminal abs(R_total), with a log-log scatter plot and table.
dt_eff and the existing frozen global/pairwise slopes are displayed from CLO05.
The order is explicitly identified as measured against dt_eff. No fit line,
extra point, frontend fit or cumulative channel reconstruction was added.

Each run and both history groups link to the existing Evidence page. Refinement
also links to its Evidence. The Evidence tab offers the current run's groups
and all five run records. Return preserves run/tab and the history page offset.
Failure, missing-source, non-production response, and in-flight run-switch
tests confirm no scientific fallback or substitute chart is displayed.

Validation artifacts (local, excluded from Git, under `.cache/phase9-closure/`):

- `WINDOW3_TESTS.xml` and `WINDOW3_PLAYWRIGHT.json`: 21-test production run,
  including Lab → Closure → D_u CFL .05 → Semi-discrete → Fully-discrete →
  Evidence → B_u CFL .05 → recorded D_at zero.
- `WINDOW3_BACKEND_REGRESSION.xml`: accepted W1/W2 regression, 192 passed.
- `WINDOW3_FRONTEND_BUILD.json`: TypeScript and Vite production build passed.
- `WINDOW3_PRODUCTION_SCAN.json`: production JavaScript mock/synthetic marker scan.
- `pre-recovery/WINDOW3_SOURCE_PRESERVATION.json`: original Window3 check of
  all 89 saved source sizes/SHA-256 hashes and the entire Closure file set
  against the accepted Window2 baseline; preserved, not rerun during recovery.
- `pre-recovery/WINDOW3_CLOSURE_FRONTEND_REPORT.json`: original 20-test report.
- Local browser screenshots: `.cache/phase9-closure/semi-discrete.png` and
  `.cache/phase9-closure/fully-discrete.png`; both inspected after final build.

The existing Vite warning for a bundle chunk larger than 500 kB remains.
Scientific files modified=NO; CFD runs started=0.

Reproduce from the repository root in PowerShell 7:

```powershell
npm run build --prefix frontend
Push-Location frontend
npx playwright test --config playwright.closure.config.ts
Pop-Location
.\.venv\Scripts\python.exe -B -m pytest tests/window1_closure_adapter tests/window2_closure_api -q --junitxml=.cache/phase9-closure/WINDOW3_BACKEND_REGRESSION.xml
```

Recovery file classification: `W3_OWNED` consists of Closure page/components,
provider bindings, experiment dispatch, browser test/config, Window3 acceptance
helper, and this handoff. `PREEXISTING` and `UNRELATED` have no entries in the
initial non-ignored dirty-file inventory. All seven `WINDOW3_*` reports/logs
are `TEMP_ARTIFACT`, preserved under `.cache/phase9-closure/pre-recovery/` and
excluded from the delivery. Existing ignored dependencies and screenshots are
excluded too. Classification is saved locally as `RECOVERY_FILE_CLASSIFICATION.json`.

Recovery changes only test/report destinations and adds the requested browser
navigation chain. Backend, schemas, generated types and scientific assets are
unchanged. The source-preservation aggregation helper remains available for
Window3 reproduction, with output redirected to `.cache`; recovery does not
invoke it or perform the independent Window4 audit.

STOP=WINDOW3_COMPLETE
