WINDOW=4_PHASE9_QA
STATUS=PASS

RUN_REGISTRY=PASS
SEMIDISCRETE=PASS
FULLY_DISCRETE=PASS
REFINEMENT=PASS
BU_ZERO_CHANNEL=PASS
NO_SPATIAL_FABRICATION=PASS
SCIENTIFIC_WORDING=PASS
EVIDENCE=PASS

PHASE5_8_REGRESSION=PASS;988 non-Closure backend/shared checks and 87 legacy browser checks
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
BLOCKERS=NONE

AUDITED_WORKTREE=D:/code_project/CFD_visiblesystem_phase9_integration_candidate
INITIAL_CLEAN_AUDITED_HEAD=f809a68ccbf4784612b4caa239365c8ed5191282
FINAL_INTEGRATION_BRANCH=codex/phase9-final-integration
W1_ACCEPTED_COMMIT=31341e75da43f91fd4878edf7e41138aee22c0ff
W1_EFFECTIVE_COMMIT=7dd3e36a279942351f39c00cde1e1ac5087e0d8b
W1_PATCH_EQUIVALENCE=PASS;stable patch-id 07b07cef49d3f36330f770b5aa803450fb5f84ce
W1_EFFECTIVE_IS_ANCESTOR=PASS
W2_COMMIT=12cb79eeaef321429f2687d3671112310969b437
W2_IS_ANCESTOR=PASS
W3_COMMIT=b8eb0b8ff261b064c6c71390f6c023059347a90a
W3_IS_ANCESTOR=PASS
PRODUCTION_CODE_MODIFIED_DURING_QA=NO

## Independent scientific acceptance

`scripts/phase9/audit_closure_integration.py` reads the frozen CSV/JSON directly.
Its five-run allowlist, expected step counts and source directories are explicit;
it does not obtain numeric expectations from adapter validation helpers. It
guards ordinary source-file writes and asserts that scientific solver/diagnostic
packages have not been imported. Public canonical/API values are compared with
saved observations, and all 16 Evidence groups are read and source-hash checked.

| Run | CFL | Accepted steps / step rows | Stage rows |
| --- | ---: | ---: | ---: |
| D_u | 0.2 | 3451 | 10353 |
| D_u | 0.1 | 6901 | 20703 |
| D_u | 0.05 | 13802 | 41406 |
| D_u | 0.025 | 27603 | 82809 |
| B_u | 0.05 | 13802 | 41406 |
| Total | | 65559 | 196677 |

Every raw row was checked for finite fields, step/stage identity, interval and
clock continuity, recorded R_SD=G+D_total, normalized eps_SD, independent
D_total versus channel decomposition, source stage-rate bindings, weighted
increments, recorded temporal residuals, and terminal-summary agreement.
PER_STAGE retains source stages 1/2/3 with canonical indices 0/1/2 and the
containing time_n. PER_STEP retains time_np1 and the recorded interval. Actual
stage-state physical time is NOT_ESTABLISHED; it is not synthesized.

Independent vector arithmetic permits only an eight-machine-epsilon bound
scaled by original term magnitudes for differently associated sums. Maximum
observed difference is 2.220446049250313e-16 for the cumulative diagnostic.
This bound is not a relative tolerance on the tiny residual. API first/middle/
last page samples, original clocks and terminal values must match saved values
exactly. The complete API total counts and all raw rows are checked; this audit
does not claim to have independently downloaded every public history page.

B_u D_at and E_at_step are recorded zero in every raw row, and E_at_total is
recorded zero. Refinement contains the four real D_u runs and terminal residuals,
with slopes bound to the frozen dt_eff results. No new fit is performed.

## Claim and capability boundaries

UI, API and Evidence consistently retain the fully-discrete numerical-diagnostic
limitation. None claims an exact fully-discrete identity, a new SSP-RK3 entropy
theorem or universal time-integrator behavior. Results are scoped to the frozen
periodic Case7 128x128 first-order FV experiment with SSP-RK3. Channel budgets
describe interface production, not separate state entropies.

Flow capability is MISSING and hidden; spatial/field/snapshot/trajectory/new-run
routes are absent. Only five complete legal run selections are offered.
Browser checks confirm that no substitute plot appears when scientific API
transport fails or a non-production result is returned.

## Regression and preservation

Fresh final-run results: backend 1180/1180, including Closure 192/192; browser
108/108, including Closure 21/21; frontend unit 5/5; 0 skipped, 0 flaky and
0 retries. Typecheck/build, OpenAPI validation and generated-type equality pass.
The historical Phase6 preservation test uses 17 dependencies selected from this
run's actual full-source pre-inventory, so its original assertion executes.

Full `D:/Paper/passage6` pre/post preservation checks all 24842 relative paths,
sizes, mtime_ns and file SHA-256 values; all 4524549696 bytes are unchanged.
Both inventory fingerprints are
`caa10a4ecf529cebed34c2eab0fb4d59253c2a408b082fd396808612c6aa7d11`.
Negative source-drift tests modify temporary copies only. CFD runs started=0.

Evidence: `PHASE9_ENTROPY_CLOSURE_INTEGRATION_EVIDENCE.json`; local detailed
execution artifacts are under `.cache/phase9-final/`.

STOP=WINDOW4_COMPLETE
