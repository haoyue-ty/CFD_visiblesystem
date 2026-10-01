PHASE9_INTEGRATION_CANDIDATE=READY

PHASE8_BASE_COMMIT=5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3
W1_ACCEPTED_COMMIT=31341e75da43f91fd4878edf7e41138aee22c0ff
W1_EFFECTIVE_COMMIT=7dd3e36a279942351f39c00cde1e1ac5087e0d8b
W1_LINEAGE_STATUS=CHERRY_PICK_EQUIVALENT
W1_PATCH_EQUIVALENCE=PASS
W1_STABLE_PATCH_ID=07b07cef49d3f36330f770b5aa803450fb5f84ce
W2_COMMIT=12cb79eeaef321429f2687d3671112310969b437
W3_COMMIT=b8eb0b8ff261b064c6c71390f6c023059347a90a

BRANCH=phase9/integration-candidate
WORKTREE=D:/code_project/CFD_visiblesystem_phase9_integration_candidate
VALIDATED_CODE_HEAD=b8eb0b8ff261b064c6c71390f6c023059347a90a
VALIDATED_CODE_TREE=34a0fa420a29d2b0217f6b4b7bf9f5e279878fa5
REPORT_NOTE=The following documentation-only commit adds this handoff; validated production and test files remain identical to VALIDATED_CODE_HEAD.

W1_PRESENT=YES
W2_PRESENT=YES
W3_PRESENT=YES
W1_EFFECTIVE_IS_ANCESTOR=PASS
W2_IS_ANCESTOR=PASS
W3_IS_ANCESTOR=PASS
W1_COMMIT_FOR_WINDOW4=7dd3e36a279942351f39c00cde1e1ac5087e0d8b

CLOSURE_ADAPTER=PASS
CLO01_05=PASS
CLOSURE_FRONTEND=PASS

RUNS=5/5
PER_STAGE=PASS
PER_STEP=PASS
REFINEMENT=PASS
BU_ZERO_CHANNEL=PASS
SPATIAL_TRAJECTORY=MISSING
EVIDENCE_NAVIGATION=PASS
MOCK_IN_PRODUCTION=NO

W1_W2_TESTS=192 passed; 0 failures; 0 errors; 0 skipped
W3_TESTS=21 passed; 0 unexpected; 0 flaky; 0 skipped; real Chromium with production build and live scientific API
W3_BUILD=PASS; vue-tsc and Vite

W3_DELIVERY_WORKTREE_CLEAN=YES
WORKTREE_CLEAN=YES
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
WINDOW4_EXECUTED=NO
PHASE5_8_FULL_REGRESSION=NOT_RUN_RESERVED_FOR_WINDOW4
FULL_SOURCE_PRE_POST_AUDIT=NOT_RUN_RESERVED_FOR_WINDOW4
FINAL_SCIENTIFIC_WORDING_QA=NOT_RUN_RESERVED_FOR_WINDOW4

READY_FOR_WINDOW4=YES
BLOCKERS=NONE

## Candidate identity and lineage

The initial shared `phase9/closure-ui` tree contained the completed W3 page,
components, bindings, browser tests and handoff, but HEAD still pointed to W2.
No existing W3 commit was assumed. Explicit file classification and a fresh
production build, 21 browser tests and 192 W1/W2 scope tests preceded the W3
commit `phase9: add entropy closure frontend`. The W3 delivery tree was clean
before creating the candidate.

The candidate was created in the independent worktree above at the exact
Phase8 base, then fast-forwarded to W3. No uncommitted code was copied from the
shared worktree. No W1/W2 patch was recreated or applied twice.

`git show <commit> | git patch-id --stable` returns the same patch ID for the
accepted W1 commit and its effective cherry-pick. The adapter, service,
canonical models, run registry, manifest and source map also compare without
differences between these W1 commits. The original accepted SHA is not an
ancestor of this lineage; Window4 must check the effective equivalent SHA
specified above, together with W2 and W3, against this candidate's HEAD.

All three `git merge-base --is-ancestor <commit> HEAD` checks return exit code
0 in this candidate. The report commit changes only this Markdown file.

## File classification and delivery boundary

Initial non-ignored inventory:

- `W3_OWNED`: `frontend/src/pages/ExperimentDetailPage.vue`,
  `frontend/src/pages/ClosurePage.vue`, `frontend/src/data/closure.ts`,
  `frontend/src/views/closure/ClosureChart.vue`,
  `frontend/src/views/closure/ClosureHistory.vue`,
  `frontend/src/views/closure/ClosureRefinement.vue`,
  `frontend/playwright.closure.config.ts`,
  `frontend/tests/closure-real-api.spec.ts`,
  `scripts/phase9/verify_closure_frontend.py`, and
  `docs/handoffs/phase9/WINDOW_3_CLOSURE_FRONTEND.md`.
- `PREEXISTING`: no entries in the non-ignored dirty-file inventory.
- `UNRELATED`: no entries in that inventory.
- `TEMP_ARTIFACT`: `WINDOW3_BACKEND_REGRESSION.xml`,
  `WINDOW3_CLOSURE_FRONTEND_REPORT.json`, `WINDOW3_FRONTEND_BUILD.json`,
  `WINDOW3_PLAYWRIGHT.json`, `WINDOW3_PRODUCTION_SCAN.json`,
  `WINDOW3_SOURCE_PRESERVATION.json`, and `WINDOW3_TESTS.xml`.

The seven original artifacts were preserved under
`D:/code_project/CFD_visiblesystem/.cache/phase9-closure/pre-recovery/`.
None was staged. Original screenshots, caches and dependencies remain local.
Only the ten explicit W3-owned files were staged; no `git add -A` was used.
Recovery redirected test/report outputs to ignored `.cache/phase9-closure/`
and added the requested Lab navigation chain to the existing browser suite.
No frontend production behavior was rewritten during recovery.

The candidate uses ignored directory junctions for `.venv` and
`frontend/node_modules`, pointing to existing installed runtimes in the W3
worktree. Source and test files are the candidate's own committed files.
Python `backend.__file__` and `closure_registry.ROOT` were asserted to resolve
inside this candidate before its tests and API server were started.
Playwright disables server reuse and starts the backend and production preview
with this candidate's working directories.

## Verification on the actual candidate

Actual tracked files were checked for `EntropyClosureAdapter`, `ClosureService`,
CLO01–05, `ClosurePage`, all three Closure components, browser tests,
`closure_resources` Evidence bindings, and the refinement UI. The W1/W2 suites
were then rerun here, including their accepted source-preservation assertions.
This does not constitute the independent Window4 pre/post audit.

Live HTTP smoke results saved locally as `CANDIDATE_API_SMOKE.json`:

- CLO01 returns exactly `D_u-cfl-0.2`, `D_u-cfl-0.1`, `D_u-cfl-0.05`,
  `D_u-cfl-0.025`, and `B_u-cfl-0.05` in frozen registry order.
- CLO02 returns the selected `D_u-cfl-0.05` run identity.
- CLO03 returns `PER_STAGE`; CLO04 returns `PER_STEP`.
- CLO05 returns exactly the four D_u identities and four metrics records.
- B_u stage `D_at` is `{state: KNOWN, value: 0}`, with run Evidence resolvable.

The real browser suite confirms the four tabs, finite five-run selector,
recorded stage and step displays, four-point refinement, recorded B_u zeros,
`Spatial trajectory: MISSING / not recorded`, the existing numerical-diagnostic
limitation, Evidence return navigation, pagination, stale-request protection,
and absence of fallback when the API fails. The added navigation test follows
Lab → Entropy Closure → D_u CFL .05 → Semi-discrete → Fully-discrete → Evidence
→ B_u CFL .05 → recorded `D_at=0`.

The production JavaScript marker scan passed without mock/synthetic matches.
The existing Vite chunk-size warning remains. Scientific solvers were not run;
scientific-source writes were not performed. Negative source-drift tests use
temporary relocated copies.

Candidate-local artifacts, all ignored by Git:

- `.cache/phase9-closure/WINDOW3_BACKEND_REGRESSION.xml`
- `.cache/phase9-closure/WINDOW3_PLAYWRIGHT.json`
- `.cache/phase9-closure/WINDOW3_TESTS.xml`
- `.cache/phase9-closure/WINDOW3_FRONTEND_BUILD.json`
- `.cache/phase9-closure/WINDOW3_PRODUCTION_SCAN.json`
- `.cache/phase9-closure/CANDIDATE_API_SMOKE.json`
- `.cache/phase9-closure/W1_PATCH_EQUIVALENCE.json`

Reproduce the candidate's scope validation from its own root in PowerShell 7:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/window1_closure_adapter tests/window2_closure_api -q --junitxml=.cache/phase9-closure/WINDOW3_BACKEND_REGRESSION.xml
npm run build --prefix frontend
Push-Location frontend
npx playwright test --config playwright.closure.config.ts
Pop-Location
```

STOP=RECOVERY_AND_CANDIDATE_COMPLETE
