# Phase 9B Window 2 — Entropy Closure API

Branch: `phase9/closure-api`.
Final status: PASS / MERGE_READY=YES. Closure API acceptance: 116 passed;
full backend regression: 1180 passed, 0 failed, 0 skipped. Frontend type check
and build passed. Scientific files modified=NO; CFD runs started=0.

Phase9 base: `5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3`.
Accepted Window1: `31341e75da43f91fd4878edf7e41138aee22c0ff`, integrated by
cherry-pick `7dd3e36`. The accepted adapter, registry, canonical Closure models,
source manifest, and Window0 source-map bytes are preserved.

| Operation | GET path under `/api/v1` | Canonical envelope data |
| --- | --- | --- |
| CLO01 | `/experiments/entropy-closure/runs` | ClosureRunRegistry, exactly five complete runs |
| CLO02 | `/experiments/entropy-closure/runs/{run_id}` | EntropyClosureRun |
| CLO03 | `/experiments/entropy-closure/runs/{run_id}/stage-history` | ClosureHistory, fixed PER_STAGE |
| CLO04 | `/experiments/entropy-closure/runs/{run_id}/step-history` | ClosureHistory, fixed PER_STEP |
| CLO05 | `/experiments/entropy-closure/refinement` | RefinementSummary, four D_u points and frozen slopes |

`backend/api/closure.py` contains only HTTP bindings to `ClosureService`.
`create_app(closure_adapter=...)` provides the accepted protocol injection seam;
`None` leaves the adapter disabled with typed FEATURE_NOT_ENABLED errors.
The default adapter uses the configured scientific root, or the accepted
read-only `D:/Paper/passage6` root. No scientific module is imported or executed.

History requests accept `registry_revision`, `offset`, and `limit` only.
Pagination preserves HistoryQuery defaults (offset 0, limit 2000) and bounds
(offset >= 0; 1 <= limit <= 5000). Every response retains the complete fixed set
of saved scalar columns and original source ordering. Each series retains its
full `total_point_count` and page `total_count`, including empty trailing pages.
Series selectors, granularity, stage/step identity, config, CFL, formulas, and
duplicate single-value query parameters return 400 INVALID_REQUEST.

The five legal run IDs are D_u-cfl-0.2, D_u-cfl-0.1, D_u-cfl-0.05,
D_u-cfl-0.025, and B_u-cfl-0.05. Legal reads return 200. Recognizable frozen-family
combinations outside this allowlist, including B_u-cfl-0.1 and D_u-cfl-0.03,
return 422 UNSUPPORTED_COMBINATION; random IDs return 404 INVALID_RESULT_ID.
Absent saved sources return 404 MISSING_SCIENTIFIC_ASSET with SCIENTIFIC domain
and MISSING availability. Source drift/read/schema failures retain the accepted
typed scientific errors; no missing value becomes a zero.

Registry SYS01/REG01–04 activate Entropy Closure as IMPLEMENTED. The visible
supported tabs are Overview, Semi-discrete, Fully-discrete, and Evidence. Flow is
MISSING with hidden tab and EXPLAIN deep-link behavior. Allocation and Spectrum
are UNSUPPORTED. The only selector control is the complete finite run enum;
independent config/CFL combinations are never offered.

The existing EVI02/EVI03 routes resolve all 16 Closure Evidence groups and
their exact finite result identities, with Closure registry/data revisions.
Generic ARRAY01 rejects Closure scalar results; no Closure array capability is
introduced. There are no spatial, fields, snapshots, trajectory, arbitrary-cfl,
or run-new routes, and no new metrics or allocation API.

Scientific semantics remain those of Window1: 196,677 source stage rows and
65,559 accepted-step rows across five runs; source stages 1/2/3 map to canonical
0/1/2; source/canonical accepted-step indices remain 1..N. Stage clocks retain
the containing step's recorded time_n. Step points retain time_np1 and their
actual interval. Independent D_total, weighted step increments, step residual,
and recorded cumulative residual remain separate. B_u tangential values remain
recorded zero. Refinement binds the four frozen D_u residuals and existing slopes;
no fit is run and no exact fully-discrete entropy theorem is claimed.

OpenAPI 3.1 is exported from the runtime operation catalog. Exactly CLO01–05
are added; every prior schema component is unchanged. The saved export equals
the runtime `/api/v1/openapi.json` response. Generated frontend TypeScript types
include all four Closure entities and five operations, and compare byte-for-byte
with two fresh CLI generations. Frontend TypeScript checking and build passed;
the pre-existing Vite chunk-size warning remains.

The historical Phase8 bootstrap audit still checks the original 161 accepted
Phase7 file hashes and exact prerequisite hashes. It now records the explicit
Closure API software seams separately from their historical Phase8 bytes,
retained by Git; other frozen file changes still fail its negative regression.
The legacy Case8 fixture disables the Closure adapter to preserve its isolated
MOCK assumptions, while its exact operation catalog includes CLO01–05.

Validation artifacts:

- `WINDOW2_TESTS.xml`: Closure API focused acceptance.
- `WINDOW2_FULL_REGRESSION.xml`: complete backend regression, including Window1.
- `WINDOW2_FRONTEND_BUILD.json`: frontend type check/build outcome.
- `WINDOW2_EVIDENCE_BINDINGS.json`: all 16 publicly resolvable Evidence bindings.
- `WINDOW2_SOURCE_BEFORE.json` and `WINDOW2_SOURCE_PRESERVATION.json`: 89-file
  size/SHA-256 and complete Closure file-set comparison.
- `WINDOW2_CLOSURE_API_REPORT.json`: final machine-readable status.
- `WINDOW2_INITIAL_TEST_FAILURE.xml`: initial test-authoring diagnostics, retained
  for traceability. The assertions were corrected to recognize recorded
  R_time_step as STEP_INCREMENT and read generated UTF-8 files explicitly on Windows.
- `WINDOW2_INITIAL_REGRESSION_FAILURE.xml`: the two historical integration-boundary
  failures before updating the audit's explicit software seams and operation catalog.

Reproduce from the repository root using PowerShell 7:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.export_openapi
npm run generate:types --prefix frontend
.\.venv\Scripts\python.exe -B -m pytest tests/window2_closure_api -q --junitxml=docs/handoffs/phase9/WINDOW2_TESTS.xml
.\.venv\Scripts\python.exe -B -m pytest tests -q --junitxml=docs/handoffs/phase9/WINDOW2_FULL_REGRESSION.xml
npm run build --prefix frontend
.\.venv\Scripts\python.exe -B -m scripts.phase9.verify_closure_api
```

Window2 stops after API delivery and its acceptance report. Closure UI work
belongs to a later window. Scientific files are read-only and CFD runs started=0.
