WINDOW=0_PHASE9_BOOTSTRAP
STATUS=PASS
RUNS=5/5
BU_RUNS=1/1
DU_RUNS=4/4
STAGE_DATA=PASS
STEP_DATA=PASS
REFINEMENT=PASS
SPATIAL_TRAJECTORY=MISSING
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
NEXT=WINDOW1

PHASE9_BASE_COMMIT=5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3
CURRENT_BRANCH=phase9/closure-bootstrap
WORKTREE_CLEAN=TRUE

`WORKTREE_CLEAN` records the initial pre-output worktree check. The independent worktree is `D:/code_project/CFD_visiblesystem_phase9_closure_bootstrap`. The final deliverables are documentation only. Completion of Window 0 stops before Window 1 implementation.

## Source authority and verification

Scientific root: `D:/Paper/passage6`. Closure root: `D:/Paper/passage6/experiments/entropy_budget_closure`. Both were treated as READ ONLY. All 54 manifest entries and 55 frozen checksum entries match their recorded SHA-256; the manifest itself is bound by `FREEZE_HASHES.sha256`. The checksum list excludes its own hash by design; its audit hash is also recorded in the source map. The 31 imported/config scientific identity files match frozen hashes, with no source drift. All 89 audited scientific files, including the complete Closure tree, retain their pre-audit sizes and hashes. No scientific scripts were imported or executed; the temporary audit uses Python stdlib with `-B`.

Source map: [PHASE9_CLOSURE_SOURCE_MAP.json](PHASE9_CLOSURE_SOURCE_MAP.json). SHA-256: `fcc71bfa3cecb719b5d74943e639b836107af0e9837d7650dcee0f6088a9fc26`. It records all source paths/hashes, run identities, CSV headers, definitions, model units, time/index conventions, formula checks, claim boundaries and future implementation requirements. Its local audit asset IDs do not replace the application registry.

## Real CSV counts and terminal residuals

| Run | Accepted steps | Stage rows | Step rows | Recorded terminal R(T) |
| --- | ---: | ---: | ---: | ---: |
| D_u-cfl-0.2 | 3451 | 10353 | 3451 | -2.7921972223232672e-07 |
| D_u-cfl-0.1 | 6901 | 20703 | 6901 | -3.4918516522708387e-08 |
| D_u-cfl-0.05 | 13802 | 41406 | 13802 | -4.3648162861842366e-09 |
| D_u-cfl-0.025 | 27603 | 82809 | 27603 | -5.4565463258882119e-10 |
| B_u-cfl-0.05 | 13802 | 41406 | 13802 | -4.3653944903354613e-09 |

All 196,677 stage rows and 65,559 step rows were read. Every step has exactly three stage rows, complete 1/2/3 source order, contiguous 1..N accepted-step indices and finite fields. No rejected/retry steps were recorded. Production selectors must remain this explicit five-run allowlist; logs/preflight assets are provenance only. CFL is bound to frozen run metadata, not inferred from `005`/`0025` directory suffixes.

## Semi-discrete and fully-discrete semantics

PER_STAGE retains `G`, `D_bg`, `D_aa`, `D_at`, independent `D_total`, `R_SD`, `eps_SD` and `R_decomp`. For every row, `R_SD=G+D_total`, the recorded normalization and decomposition formula reproduce exactly from parsed CSV values. Maximum measured `abs(R_SD)` is `8.604228440844963e-16`; maximum `eps_SD` is `3.742752570252953e-15`. This is measured floating-point closure between the actual FV RHS and independent observer in the tested periodic protocol.

Canonical stage indices are 0/1/2; source indices 1/2/3 remain in `source_stage_index`. Source and canonical step indices are both 1..N. `t_stage_or_step_time` equals the containing step's recorded `time_n` for all three stages. Preserve that original clock value and explain its meaning; do not construct physical stage-state times. PER_STEP uses recorded `time_np1` endpoints and `[time_n,time_np1]` intervals; `S_n` itself refers to the interval start.

PER_STEP retains `S_n`, `S_np1`, `DeltaS`, every real `D_*_stage1/2/3` column, `E_bg_step`, `E_aa_step`, `E_at_step`, `E_obs_step`, `E_total_independent_step`, `R_time_step` and `R_time_cumulative`. Stage weights are 1/6, 1/6, 2/3. The CSV-copy bindings, weighted increments, step residual and cumulative residual formulas were checked for every step, and terminal values agree with frozen summary. `R_time_step=DeltaS+E_obs_step`; `R_time_cumulative=S_np1-S0+sum(channel cumulative increments)` is a separate recorded quantity. It is not a replacement name for the step residual.

The only cumulative column in step CSV is `R_time_cumulative`. Frozen terminal summary records `DeltaS_total`, `E_bg_total`, `E_aa_total`, `E_at_total`, `E_obs_total`, `R_total`, plus `S0`, `ST` and `eps_time_total`. No saved `E_*_cumulative` history column exists. Do not rename `E_*_step` to cumulative. Any future cumulative channel history requires an explicit verified adapter derivation with source hashes, accumulation order and terminal checks; no frontend accumulation creates formal scientific evidence. Units are model integrated entropy, model entropy rate, model time or dimensionless as appropriate; SI mappings remain UNKNOWN.

## Frozen temporal refinement and B_u control

D_u CFL .2/.1/.05/.025 terminal `R_time_cumulative` matches frozen `R_total` exactly. Magnitudes decrease monotonically. Existing frozen pairwise slopes are `2.9999637884197288`, `2.999999431211793`, `3.000017724561341`; existing frozen global slope is `2.9999942283876795` against `dt_eff`, with no identified floating-point floor. Phase9 did not fit or replace these values. A later slope must bind these existing results, or be labeled VERIFIED_DERIVATION with explicit processing and verification (canonical schema status DERIVED_VERIFIED).

B_u q_at=0: all 41,406 raw stage `D_at` values, 41,406 step-embedded `D_at_stage*` values and 13,802 `E_at_step` values are exactly zero; frozen `E_at_total=0`. These are RECORDED ZERO / KNOWN value 0. MISSING DATA must never become zero-fill.

## Scientific scope and implementation boundary

The fully-discrete residual is not an exact identity. The data support only measured semi-discrete FV/observer closure and observed SSP-RK3 temporal refinement in this frozen periodic Case7 protocol. They establish no new fully-discrete entropy theorem, no common property of all time integrators and no claim for all boundary conditions. Channel budgets attribute interface production; they are not separate state entropies.

Flow capability is MISSING and spatial trajectory replay is UNSUPPORTED. The frozen IA permits Overview / Semi-discrete / Fully-discrete / Evidence, with no Flow tab and explanatory unsupported deep links. Allocation and spectrum are UNSUPPORTED here. Do not borrow Case7 vortex, Case8 or another CFL spatial field.

Window 1 may implement the Closure adapter against this map: hash-bound explicit run registry, separate PER_STAGE/PER_STEP histories, preserved source conventions, recorded-zero handling, frozen terminal/refinement bindings and explicit derivation provenance. This window contains no Adapter/API/Vue implementation, no CFD run, no source edits and no new fit. Stop here; NEXT=WINDOW1.
