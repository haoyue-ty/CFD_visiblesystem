PHASE9_ENTROPY_CLOSURE_INTEGRATION=PASS
DELIVERABLE=Entropy Closure Lab V1

BOOTSTRAP=PASS
ADAPTER=PASS
API=PASS
FRONTEND=PASS
EVIDENCE=PASS;16/16 groups
WINDOW4_QA=PASS

RUNS=5/5
BU_RUNS=1/1;CFL .05
DU_RUNS=4/4;CFL .2/.1/.05/.025

SEMIDISCRETE=PASS;PER_STAGE
FULLY_DISCRETE=PASS;PER_STEP numerical diagnostics
REFINEMENT=PASS;4/4 real D_u points
BU_ZERO_CHANNEL=PASS;D_at recorded zero
SPATIAL_TRAJECTORY=MISSING

CLO01_05=PASS
BACKEND_TESTS=1180/1180;0 failures;0 errors;0 skipped
PHASE9_TESTS=192/192 backend;21/21 real-API browser;independent all-row QA PASS
FRONTEND_TESTS=5/5 unit;113/113 including browser
E2E=108/108;0 skipped;0 flaky;0 unexpected;0 retries
TYPECHECK=PASS
BUILD=PASS
OPENAPI=PASS;3.1 valid;runtime and saved JSON identical
GENERATED_TYPES=PASS;two fresh generations byte-identical to committed types

PHASE4_8_FROZEN=PASS
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0

KNOWN_LIMITATIONS=Frozen periodic Case7,128x128,first-order FV,SSP-RK3 and five recorded runs only;fully-discrete residual is a numerical diagnostic;no new entropy theorem or universal time-integrator claim;actual stage-state time NOT_ESTABLISHED;spatial trajectory MISSING;model-unit SI mapping unknown;frozen refinement slopes are read without refit;existing Vite chunk-size warning.
BLOCKERS=NONE
NEXT=STOP_AND_REVIEW

AUDIT_DATE=2026-10-02;Asia/Shanghai
BRANCH=codex/phase9-final-integration
WORKTREE=D:/code_project/CFD_visiblesystem_phase9_integration_candidate
INITIAL_CLEAN_CANDIDATE_HEAD=f809a68ccbf4784612b4caa239365c8ed5191282
VALIDATED_SOFTWARE_HEAD=4182fe133533a44508cc763fb2759fbdf502d5a5
FINAL_REPORT_NOTE=The subsequent report-only commit adds this audit and its evidence;validated software and acceptance tools are unchanged.
WORKTREE_CLEAN=YES;after final report commit
PHASE10_STARTED=NO

## Integrated delivery and exact audit object

The audit began on the clean independent Phase9 integration candidate above.
Before scientific acceptance, W1 effective, W2 and W3 each passed
`git merge-base --is-ancestor <commit> HEAD`. The final branch retains those
commits and adds the completed independent W4 QA and acceptance tools. The main
`phase9/closure-ui` worktree and all Phase10 worktrees were left unchanged.

| Window | Accepted identity | Final integration verification |
| --- | --- | --- |
| W0 Bootstrap | `5ad96fb43421af09b43c64f88b51a494fc4a5cdf` | Source-map and bootstrap handoff bytes exactly equal the original W0 Git blobs; present through W1 delivery. |
| W1 Adapter | accepted `31341e75da43f91fd4878edf7e41138aee22c0ff`; effective `7dd3e36a279942351f39c00cde1e1ac5087e0d8b` | Stable patch-id equivalence PASS; effective commit is an ancestor. |
| W2 API | `12cb79eeaef321429f2687d3671112310969b437` | Ancestor; exact CLO01–05 and canonical responses verified. |
| W3 Frontend | `b8eb0b8ff261b064c6c71390f6c023059347a90a` | Ancestor; production Vue chain and failure behavior verified. |
| W4 QA / final acceptance tools | `4182fe133533a44508cc763fb2759fbdf502d5a5` | Independent saved-source QA, full browser configuration, unit configuration and Window4 PASS handoff committed. |

W1 stable patch-id is `07b07cef49d3f36330f770b5aa803450fb5f84ce` for both
accepted and effective commits. The original W1 SHA is not an ancestor;
equivalence is recorded explicitly and ancestry checks use the effective SHA.
No patch was duplicated to manufacture an original-SHA ancestry relationship.

The existing Phase8 final acceptance/freeze records were merged from
`codex/phase8-final-integration` in documentation-only merge
`b7811df01d6db109b466e676c3d9e43dd471c0ff`. Its diff adds exactly four Phase8
documents. No production backend, frontend source, OpenAPI, generated type or
scientific manifest changed during this final integration. Additions are QA
tools/configuration, six browser-chain assertions, handoffs and evidence.

## Scientific source → adapter → canonical models → API → Vue → Evidence

| Link | Verification |
| --- | --- |
| Frozen scientific source | Original Window0 map and scientific identities; read-only CSV/JSON plus full-tree pre/post SHA-256 preservation. |
| EntropyClosureAdapter | Public run values equal the live canonical API response; numeric expectations are independently read from raw sources. |
| Canonical Models | ClosureRunRegistry, EntropyClosureRun, ClosureHistory, RefinementSummary and EvidenceRecord validate actual wire payloads. |
| CLO01–05 | Exact finite registry, all five run identities, fixed PER_STAGE/PER_STEP histories and four-run refinement. OpenAPI/runtime catalog agree. |
| Vue | Production build against a fresh backend; complete real browser chain, record pagination, finite selector and recorded zero channel. |
| Evidence | All 16 groups resolve with definitions, result identities, nonempty source assets, matching recorded/current data hashes and no source drift. |

Frozen source: `D:/Paper/passage6/experiments/entropy_budget_closure`.
Scientific solvers and drivers were never executed. Expected run counts and
selections in the independent QA script are explicit, rather than read from
adapter validation helpers.

| Run | CFL | Accepted steps / step rows | Stage rows | Recorded terminal R(T) |
| --- | ---: | ---: | ---: | ---: |
| D_u | 0.2 | 3451 | 10353 | -2.792197222323267e-7 |
| D_u | 0.1 | 6901 | 20703 | -3.491851652270839e-8 |
| D_u | 0.05 | 13802 | 41406 | -4.3648162861842366e-9 |
| D_u | 0.025 | 27603 | 82809 | -5.456546325888212e-10 |
| B_u | 0.05 | 13802 | 41406 | -4.365394490335461e-9 |
| Total | | 65559 | 196677 | |

All raw rows were independently checked for finite values, exact counts,
indices, original stage clocks, intervals, R_SD=G+D_total, eps_SD normalization,
independent D_total and channel decomposition, stage-rate bindings, weighted
increments and terminal/cumulative diagnostics. PER_STAGE and PER_STEP retain
distinct sampling and accumulation semantics. B_u D_at, E_at_step and E_at_total
are actual recorded zeros, not missing values.

API first/middle/last page values and terminal values compare exactly with their
saved observations. Independent vector arithmetic checks differently associated
sums with an eight-machine-epsilon error bound scaled by original terms;
the maximum observed difference is 2.220446049250313e-16. The audit checks every
raw row and all public total counts, without claiming an independent download
of every API page. Existing suites also validate full adapter source audits,
pagination boundaries, query rejection and missing/drift failures.

Refinement uses exactly the four D_u terminal residuals above. Frozen global
slope is 2.9999942283876795 against dt_eff; existing pairwise slopes and their
inputs are retained. No new fitting or synthetic refinement point was added.

UI/API/Evidence make no claim of an exact fully-discrete identity, a new SSP-RK3
entropy theorem or universal time-integrator behavior. Fully-discrete PASS
means faithful delivery and checking of the recorded diagnostic. Stage clocks
remain the containing step's time_n, with actual stage-state time explicitly
NOT_ESTABLISHED. Spatial trajectory is MISSING; unsupported spatial routes and
views remain absent. Channel attribution is interface production, not separate
state entropies.

## Real browser acceptance

Production preview and real scientific API were started from this worktree;
existing servers were not reused. The requested chain passes:

Lab → Entropy Closure → D_u CFL .05 → Semi-discrete → Fully-discrete →
four-point Refinement → refinement Evidence → return → run Evidence.
Then B_u CFL .05 → Semi-discrete → recorded D_at=0 visible.

The suite also checks all five legal selector values, original saved values,
record pagination including the final page, recorded cumulative versus increment
semantics, Evidence return context, stale-request cancellation, missing sources,
non-production rejection and API failures without substitute charts. The
production JavaScript mock/synthetic marker scan passes with no matches.

## Complete regression

Fresh backend pytest result: 1180 passed, 0 failed, 0 errors, 0 skipped.

| Backend group | Passed |
| --- | ---: |
| Phase4/5 and shared models/contracts | 273 |
| Phase6 allocation | 146 |
| Phase7 spectral | 371 |
| Phase8 Cylinder/cross-flow/bootstrap | 198 |
| Phase9 Closure adapter/API | 192 |

Frontend unit tests: 5 passed. Typecheck and production build pass.
The full browser suite covers every existing browser spec and all registered
legacy development projects: 108 passed, 0 skipped, 0 flaky, 0 unexpected,
0 retries.

| Browser project | Passed | Data mode |
| --- | ---: | --- |
| real-api | 31 | Production scientific API |
| phase8-real-api | 21 | Production scientific API |
| phase9-real-api | 21 | Production scientific API |
| window3-mock-development | 16 | Historical explicit development/mock tests |
| window4-allocation-ui | 10 | Historical explicit development/mock tests |
| window3-spectral-ui | 9 | Historical explicit development/mock tests |

The 35 development-mode regression checks are intentionally isolated in the
existing mock development server. All 73 real-api checks use the production
build and scientific backend; Closure acceptance has no production mock fallback.
Unit tests run separately and are excluded from the browser project, giving
113 unique frontend checks in total.

The previous conditional Phase6 skip was avoided by selecting its 17 actual
dependencies from this run's full source pre-inventory and saving the expected
local baseline. The original source-preservation assertion executed unchanged.
No tests were disabled or retries enabled to obtain acceptance.

OpenAPI 3.1 validates and equals both the runtime export and saved parsed JSON.
Fresh Windows CLI export differs in CRLF serialization only; normalized bytes
are identical, with no schema, order or content change. Two fresh generated
TypeScript files equal each other and the committed declarations byte-for-byte.

OpenAPI saved SHA-256:
`7009b4a81f9c94c9081e68e4b806b6d1e1cd5d2a969c4dea4f5290fc1556f5ee`.
Generated types SHA-256:
`d22874fa5c65bdd99e10c0ee483f174f0dff209b00c328b9ab568331361170a9`.

## Frozen phases and source protection

All 11 Phase8-manifest prerequisite and freeze-record hashes match current
files exactly, including Phase4 architecture/schema/API documents and the
Phase5/6/7 freeze records. The original 161 accepted Phase7 file hashes remain
verified by their saved archive. All 268 Phase8 accepted file Git identities
are verified against the original validated-code or acceptance-report commits.
Fourteen historical software files legitimately evolved in W1–W3; their
current contents match the already accepted Phase9 delivery. The original
freeze manifests and their original identities are retained unchanged.

The complete `D:/Paper/passage6` tree has 24842 files and 4524549696 bytes.
Pre/post relative paths, sizes, mtime_ns and per-file SHA-256 values are identical.
Both inventory fingerprints equal:
`caa10a4ecf529cebed34c2eab0fb4d59253c2a408b082fd396808612c6aa7d11`.
Negative source-drift tests modify temporary relocated copies only.
Scientific files modified=NO; CFD runs started=0.

## Evidence and reproduction

Committed evidence: `PHASE9_ENTROPY_CLOSURE_INTEGRATION_EVIDENCE.json`.
Independent QA handoff: `WINDOW_4_PHASE9_QA.md`.
Detailed pytest/Playwright outputs, source inventory and fresh contract/type
exports are local under `.cache/phase9-final/`; their hashes are bound in the
committed evidence. Logs, node_modules, caches and screenshots are not staged.

From this worktree in PowerShell 7, the acceptance commands were:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.phase9.audit_closure_integration
.\.venv\Scripts\python.exe -B -m pytest tests -q --junitxml=.cache/phase9-final/backend.xml
Push-Location frontend
npx vue-tsc --noEmit
npm run build
npx playwright test --config playwright.unit.config.ts
$env:E2E_API_PORT='5099'
$env:E2E_PRODUCTION_PORT='4399'
$env:E2E_MOCK_PORT='4499'
npx playwright test --config playwright.phase9.integration.config.ts
Pop-Location
.\.venv\Scripts\python.exe -B -m scripts.export_openapi --output .cache/phase9-final/openapi.json
node frontend/node_modules/openapi-typescript/bin/cli.js .cache/phase9-final/openapi.json -o .cache/phase9-final/api.d.ts
node frontend/node_modules/openapi-typescript/bin/cli.js .cache/phase9-final/openapi.json -o .cache/phase9-final/api-repeat.d.ts
.\.venv\Scripts\python.exe -B -m scripts.verification.source_audit --root D:/Paper/passage6 --baseline .cache/phase9-final/source_before.json --output .cache/phase9-final/source-preservation.json
```

The source pre-inventory was captured before tests; comparison commands never
write under the scientific root. Existing ignored Python/Node dependency
junctions supply installed runtimes, while backend modules and tests resolve
inside this worktree. No installation, deployment or Phase10 work was performed.

STOP=PHASE9D_COMPLETE
