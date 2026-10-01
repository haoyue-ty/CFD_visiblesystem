# Phase 9B Window 1 — Entropy Closure Adapter

Branch: `phase9/closure-adapter`.
Independent worktree: `D:/code_project/CFD_visiblesystem_phase9_closure_adapter`.
PHASE9_BASE_COMMIT: `5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3`.
Window0 source-map commit: `5ad96fb43421af09b43c64f88b51a494fc4a5cdf`.
Window0 source-map SHA-256: `fcc71bfa3cecb719b5d74943e639b836107af0e9837d7650dcee0f6088a9fc26`.

`EntropyClosureAdapter` reads real frozen scientific CSV/JSON only. It audits every
saved row before exposing values. `ClosureService` validates the canonical result
independently of Flask and accepts `EntropyClosureAdapterProtocol` for Window2
injection. No application activation, frontend, API path, OpenAPI export, inventory
correction, or edits to frozen 04/05/06 are included.

The single canonical entities are materialized in `backend.models.closure`:
`ClosureRunRegistry`, `EntropyClosureRun`,
`ClosureHistory`, `RefinementSummary`, and `RunMetrics`. They reuse the existing
`ScalarSeries`, `ScalarPoint`, `Metric`, `ScientificResult`, `Fact`, `ResourceSlot`,
and Evidence models. No alternate DTOs are introduced.
The existing frozen package export files remain byte-for-byte unchanged. Import
Closure entities, adapter, and service from their owning modules for Window2.

| Frozen operation / seam | Service method | Canonical result |
| --- | --- | --- |
| CLO01 | `list_runs()` | `ClosureRunRegistry` |
| CLO02 | `load_run(run_id)` | `EntropyClosureRun` |
| CLO03 | `load_stage_history(run_id, series=None, offset=0, limit=2000)` | `ClosureHistory`, PER_STAGE |
| CLO04 | `load_step_history(run_id, series=None, offset=0, limit=2000)` | `ClosureHistory`, PER_STEP |
| CLO05 | `load_refinement()` | `RefinementSummary` |
| Evidence | `load_evidence(evidence_id)` | `EvidenceRecord` |
| Provenance | `load_provenance(result_id)` | `ResultProvenance` |

History pagination keywords are keyword-only. Adapter pagination accepts positive
integer limits for full-source audit tools; the future API slice must apply its
existing frozen HistoryQuery limits. Offset can address an empty trailing page.
Series selection accepts only explicit saved columns for the selected granularity.

| Run ID | Step rows | Stage rows |
| --- | ---: | ---: |
| D_u-cfl-0.2 | 3451 | 10353 |
| D_u-cfl-0.1 | 6901 | 20703 |
| D_u-cfl-0.05 | 13802 | 41406 |
| D_u-cfl-0.025 | 27603 | 82809 |
| B_u-cfl-0.05 | 13802 | 41406 |
| Total | 65559 | 196677 |

The registry is an explicit five-run allowlist. CFL is checked against the real
run summary and frozen temporal summary, not inferred from folder suffix or
inherited protocol default. The Evidence `METADATA_CORRECTION` record binds
`.005` inventory interpretation to canonical `.05`, preserving the inventory.
Recognized B_u/D_u combinations outside this selection return
`UNSUPPORTED_COMBINATION` (422); random run/result IDs return
`INVALID_RESULT_ID` (404). A missing scientific source or required CSV column
returns `MISSING_SCIENTIFIC_ASSET`; no absent field becomes zero.

PER_STAGE retains every saved scalar column, including the eight mandatory
G/D_bg/D_aa/D_at/D_total/R_SD/eps_SD/R_decomp quantities, recorded clock, dt, and
face counts. Source accepted step 1..N remains canonical 1..N. Stage source 1/2/3
maps to canonical 0/1/2; ordinal is 3*(step-1)+(source_stage-1).
Each point retains the containing real step interval. `physical_time` preserves
the raw `t_stage_or_step_time`, which equals `time_n` for all three stages.
Actual stage-state time remains NOT_ESTABLISHED in the explicit clock definition;
no synthetic RK stage times are generated. Point run identity, units, definitions,
verification, and Evidence are inherited from the canonical enclosing series
header, as required by frozen ScalarPoint schema.

PER_STEP retains every real column: time_n/time_np1/dt, S_n/S_np1/DeltaS, all twelve
D_*_stage1/2/3 columns, all recorded E_*_step increments, independent-total
increment, R_time_step and R_time_cumulative. Points use `time_np1` endpoints and
the actual `[time_n,time_np1]` interval; S_n's definition explicitly refers to the
start. Embedded rate columns also retain their source/canonical stage indices.
Only R_time_cumulative is a saved cumulative history. No E_* cumulative history
is generated. Existing frozen terminal E_* totals remain terminal metrics.

The audit checks all finite fields, contiguous steps, three ordered stages,
source clocks, face counts, R_SD, normalization, independent channel decomposition,
stage-to-step copies, SSP-RK3 weighted increments, actual single-state entropy
changes, recorded step/cumulative residual formulas, and frozen terminal totals.
The temporary audit accumulates bg/aa/at independently in accepted-step order
solely to check the already-recorded cumulative residual and terminal totals;
that accumulator is never emitted as a new history. B_u stage D_at, step embedded
D_at, E_at_step, and terminal E_at_total are observed recorded zero.

Arithmetic preserves the frozen driver's Python `sum` in bg/aa/at order, including
Python 3.12 compensated summation. Reassociating it into chained additions changes
floating-point rounding and is not used to redefine frozen decomposition.

Refinement uses the four D_u terminal recorded residuals and effective dt values,
with frozen pairwise slopes 2.9999637884197288, 2.999999431211793, and
3.000017724561341. The existing global slope is 2.9999942283876795. Pairwise input
run IDs/CFLs/dt/residuals are checked against their real runs. No fit is performed.
Pairwise metrics identify the fine run in their metric ID; global-slope Evidence
contains all four run contexts and inputs. Fully-discrete results remain temporal
diagnostics, not an exact entropy identity or a new entropy theorem.

Evidence IDs are `ev.entropy-closure.{run_id}.run`, `.stage`, `.step`, and
`ev.entropy-closure.D_u.temporal-refinement` (16 groups). Source assets retain
Phase1 `asset_*` identities where already registered; internal Window0 audit
locators do not become public asset IDs. Every group includes definitions, method
identity, recorded/current hashes, freeze-manifest reference, processing hashes,
verification, and limitations. Processing hashes bind the actual adapter and
registry bytes. Processing verification is VERIFIED_NOT_FROZEN, distinct from
upstream frozen numeric verification. Evidence data_hash is SHA-256 over sorted
(asset_id, recorded SHA-256) pairs for selected frozen dependencies, encoded as
compact JSON, excluding current imported-code observations.

All requested saved bytes are re-observed even on cache hits. Frozen data,
config, driver, and freeze-authority drift blocks reads with SOURCE_DATA_DRIFT;
missing files block reads. Current imported-code drift is separately exposed by
source_drift, SourceObservation, and source hashes, without changing the recorded
method identity or executing that code. The frozen checksum list excludes its
own hash by design and retains its VERIFIED_NOT_FROZEN subasset status.

Validation outputs are `WINDOW1_TESTS.xml`, `WINDOW1_FULL_REGRESSION.xml`,
`WINDOW1_EVIDENCE_BINDINGS.json`, `WINDOW1_SOURCE_PRESERVATION.json`, and
`WINDOW1_CLOSURE_ADAPTER_REPORT.json`. Reproduce the read-only report with:

```powershell
python -B -m pytest tests/window1_closure_adapter -q --junitxml=docs/handoffs/phase9/WINDOW1_TESTS.xml
python -B -m pytest tests -q --junitxml=docs/handoffs/phase9/WINDOW1_FULL_REGRESSION.xml
python -B -m scripts.phase9.verify_closure_adapter
```

The source preservation comparison covers all 58 Closure-tree files plus all 31
Window0 imported-source identity files, including file-set equality and byte
hashes. No scientific code is imported or executed, and no solver runs start.
Window1 stops here. API integration belongs to the next window.

Final validation: 76 Closure tests plus the prior frozen-package audit passed
(77/77 focused). Full backend regression: 1062 passed, 1 skipped, 0 failed.
The existing skip concerns an absent Allocation integration-run preservation
baseline; all Closure source preservation checks passed. Initial export changes
were reverted after the prior freeze audit identified them; the final delivery
contains additions only and retains that failure diagnostic for traceability.
