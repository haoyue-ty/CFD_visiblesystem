WINDOW=4_PHASE8_QA
STATUS=FAIL

SOURCE_TRUTH=PASS
CYLINDER_SCOPE=FAIL
ALLOCATION_SEMANTICS=FAIL
CUMULATIVE_2D_MISSING=FAIL
CROSS_FLOW_COMPARABILITY=FAIL
NO_UNIFIED_RANKING=FAIL
EVIDENCE=FAIL

SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0

BLOCKERS=Window1 Cylinder Adapter absent; Window2 Cylinder/Cross-flow API absent; Window3 Cylinder/Cross-flow frontend absent; C_u scientific rejection absent; typed cumulative2D missing slot and Evidence absent; explicit comparability and NO_UNIFIED_RANKING absent.

AUDIT_DATE=2026-10-01;Asia/Shanghai
AUDIT_ROLE=INDEPENDENT;production code unchanged;no automatic scientific fixes
AUDITED_STATE=Current shared working tree, including pre-existing Phase7 uncommitted changes
PHASE5_REGRESSION=PASS
PHASE6_REGRESSION=PASS
PHASE7_REGRESSION=PASS
PRODUCTION_FABRICATION_SCAN=PASS;no forbidden scientific fabrication found in delivered runtime paths
METRIC_SEMANTICS_ACCEPTANCE=FAIL;Cylinder/Cross-flow result definitions and comparability are not implemented
SOURCE_PRESERVATION=PASS;full D:/Paper/passage6 tree, not only selected scientific dependencies
NEXT=STOP

## Acceptance scope and blocking findings

This is a FAIL for the requested Phase8 delivery. Source truth and older regression checks pass, but design documents and existing raw assets do not establish that Window1–3 have been delivered. There are no Phase8 Cylinder adapter/service/API modules, Cylinder views, Cross-flow views or corresponding acceptance suites in this working tree. No production or scientific-source repairs were made.

| Requirement | Observed evidence | Verdict |
| --- | --- | --- |
| Window1 Cylinder Adapter | `backend/adapters` contains Case8, Gate, Allocation and Spectral implementations; no Cylinder implementation. `backend/core/app.py` initializes only those existing services. | FAIL |
| A/B/D only; C rejected | Source protocol and run directories contain exactly A_u/B_u/D_u. Runtime Cylinder catalog has `available_configs=[]`, `delivery_status=PLANNED`, `status=UNSUPPORTED`. Requests for A/B/C/D scientific resources all return generic route 404. C_u does not return the specified 422 `UNSUPPORTED_COMBINATION`. | FAIL for delivery; source facts PASS |
| Window2 Cylinder API | Cylinder metadata/configs/capabilities return 503 `FEATURE_NOT_ENABLED`. All tested snapshots, entropy-history, metrics and allocation paths return 404 `API_ROUTE_NOT_FOUND`. None of CYL01–09 is registered in the 27-operation application catalog. | FAIL |
| Window2 Cross-flow API | `/api/v1/comparisons/case8-cylinder` returns 404 `API_ROUTE_NOT_FOUND`; no composite schema/operation is registered. | FAIL |
| Window3 frontend | `frontend/src/pages/LabPage.vue:32` displays Cross-flow PLANNED; Cylinder is a PLANNED catalog entry. `frontend/src/pages/ExperimentPage.vue` implements Case8 selectors/tabs. No Cylinder/Cross-flow data-service methods or dedicated views exist. | FAIL |
| Allocation semantics | `backend/models/allocation.py:134` explicitly defers Cylinder sectors and REGION_SCALAR; the result union accepts only FaceAllocation/CellAllocation. No runtime interior-only sector/front-band result can be checked. | FAIL |
| cumulative2D MISSING | Source lacks a trajectory cumulative 2D field. Runtime allocation overview is absent, so it does not supply the required PARTIAL overview with a MISSING slot, limitation and Evidence. Generic route MISSING is not this scientific resource declaration. | FAIL |
| Explicit comparability | `ComparabilityRule` and `CrossFlowComparison` are absent from runtime code/OpenAPI. Source metric differences are established below but not exposed by a comparison result. | FAIL |
| NO_UNIFIED_RANKING | Neither `ranking_policy` nor `NO_UNIFIED_RANKING` is present in backend, frontend source or current OpenAPI. Absence of a ranking page does not satisfy the mandatory policy field. | FAIL |
| Evidence | No real Cylinder result is delivered, so the non-empty and resolvable result Evidence requirement cannot be accepted. Cylinder catalog `evidence_refs` and `limitations` are empty. `/api/v1/evidence/ev.missing.cylinder-cumulative2d` returns 404 `UNKNOWN_EVIDENCE_ID`, with empty error Evidence refs. | FAIL |

Frozen design requirements remain in `docs/05_DATA_SCHEMA.md` §12 and `docs/06_API_CONTRACT.md` §12–13. They do not substitute for runtime responses.

## Independently observed source truth

Authoritative read-only bundle:
`D:/Paper/passage6/jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2`.
All 57 inventoried assets in this bundle match their recorded SHA-256 values in `data/data_asset_inventory.json`. No historical Cylinder baseline was substituted for the J2C-v2 bundle.

- Protocol/config identity: A_u=(13.2,0), B_u=(3.96,0), D_u=(3.96,.396); no C_u run. Mach3, O-grid nr32×ntheta128, r=.5…8, stretch3, T=2, 9757 accepted steps.
- Each configuration has exactly five saved native-face NPZ checkpoints. Source identities and scalar `time` values were read from each NPZ with `allow_pickle=False`; no times were generated or rounded for the audit.

| User snapshot index | Completed step | Saved NPZ time, identical for A/B/D |
| --- | ---: | ---: |
| 1 | 0 | 0.0 |
| 2 | 2439 | 0.4999487547401866 |
| 3 | 4878 | 0.9998975094803731 |
| 4 | 7318 | 1.5000512452598136 |
| 5 | 9757 | 2.0 |

- Each CSV contains exactly 9757 scalar records. Its source `step` runs 0…9756 and its final `time_end` is 2.0. These row indices differ from checkpoint completed-step identities; they must retain their conventions when delivered.
- Instantaneous native radial faces have shape [31,128], angular faces [32,128]. These five face checkpoints do not establish five complete density/pressure field snapshots.
- Each `spatial_cumulative.npz` has 17 `bins` edges and 16 values for each `channel_bg/aa/at/total`. The saved contents contain only vectors and scalars, including scalar `shock_at`; no full cumulative 2D array is present.
- Sector channel sums agree with the final scalar history budgets and `run_result.json` totals. Maximum absolute history closure difference across all configurations/channels is 6.927791673660977e-14.
- Saved A/B channel_at values and cumulative E_at histories are truly zero because q_at=0. This is a recorded identity, not missing-data zero filling. A/B front-band fraction has a zero denominator and is not accepted as a numeric zero fraction.
- D_u saved `shock_at` is 0.000710992371911638; its saved cumulative sector denominator gives front-band fraction 0.007776872193019843. This is a source observation, not a delivered API result.
- Read-only inspection of `analysis/cylinder_j2c_v2.py:235`–270 establishes radial/angular interior-face selection and stage/time/face weighting. The fixed band uses authoritative A_u front anchors and radial half-width .16. `shock_at` is accumulated with dt/RK weights across the trajectory; it is not a terminal instantaneous rate.

SOURCE_LIMITATION=The upstream comparison file/driver uses the misleading key `Cylinder_fixed_geometry_final_rate_localization_at`. Its numeric value derives from cumulative `shock_at` and cumulative channel totals. No system may preserve the final-rate meaning by merely copying or relabelling that field. The source was preserved unchanged and not executed.

## Metric semantics and conclusion audit

| Quantity | Case8 | Cylinder | Acceptance constraint |
| --- | --- | --- | --- |
| HF | `case8_front_high_k_energy`, stored front mode energy summed above seeded k=4; `backend/registry/case8_semantics.py:253` | `front_hf_rms`: eight upstream rays in ±12°, quadratic detrend, neighboring three-point angular high-pass, normalized by local radial spacing, then RMS; `D:/Paper/passage6/solver/diagnostics/cylinder.py:90` | Different definitions, units and sampling. No label-only equivalence or common ranking. |
| Localization | Cumulative native x/y face shock window ±.08 with Case8 geometry/scope | Cumulative fixed A_u radial front band ±.16, interior-only, scalar/sector denominator | Different masks, geometry and boundary scope. No localization ranking between flows. |
| Width | Row p10–p90 crossing-distance detector; `backend/registry/case8_semantics.py:241` | Radial locally anchored ordered p90–p50–p10 bow-front crossings; `D:/Paper/passage6/solver/diagnostics/cylinder.py:43` | Different detectors. Source claim boundary explicitly retains detector-limited B/D readings. |

No inspected delivered scientific path declares winner, best, better allocation, more localized or more stable as a Cross-flow conclusion. `best` matches are a nearest-record UI local variable, explicitly disclaimed superiority text, or development mock selection. This absence does not establish the missing explicit comparability rules or mandatory ranking policy.

## Prohibited-fabrication scan

Searched backend and frontend source for `interpolat`, `synthetic`, `reconstruct`, `heatmap`, `zero-fill` variants, `fallback mock` variants, `sector-to-grid` variants and all requested conclusion terms. Inspected matches in their execution context.

- Backend matches describe forbidden interpolation/reconstruction or preserved numerical-protocol metadata; no synthetic Cylinder scientific path exists.
- `frontend/src/data/mockProvider.ts` is explicit development/test data. `frontend/src/data/index.ts:84` gates mock creation and selection with `import.meta.env.DEV`; API failures retain unavailable/error states. The freshly built production assets contain no `MOCK_SYNTHETIC_DATA`, `createMockProvider`, `mulberry32` or `mock.method.case8` signatures.
- No sector-to-grid reconstruction, fake cumulative heatmap or missing-array zero fill was found in delivered runtime paths. External upstream solver/analysis text was read as evidence only; no solver, reconstruction or scientific driver was executed by this audit.

## Source protection and regressions

Full-tree before/after inventories cover all 24842 files under `D:/Paper/passage6`, including environment/cache files. Total file bytes: 4524549696. Relative file lists, each file SHA-256, size and mtime_ns are identical; changed paths: 0.

Both inventory fingerprints (SHA-256 over sorted inventory JSON):
`caa10a4ecf529cebed34c2eab0fb4d59253c2a408b082fd396808612c6aa7d11`.

| Verification | Result |
| --- | --- |
| Complete backend suite | 790 passed; 0 failures/errors/skips; 156.91 seconds |
| Backend coverage groups by test module | Phase5/shared 273; Phase6 Allocation 146; Phase7 Spectral 371; all passed |
| Complete Chromium suite | 71 passed; 0 skipped/unexpected/flaky; real API and existing development UI suites |
| Frontend production build | vue-tsc + Vite PASS; existing nonblocking large-chunk warning |
| OpenAPI | Spec validation PASS; independently exported catalog equals checked-in config |
| Generated API types | Independent regeneration in audit cache is SHA-256-identical |
| Phase7 accepted manifest | 161/161 accepted files retain frozen SHA-256; includes earlier production implementation |
| git diff --check | PASS; pre-existing Phase7 modifications retained |

These regression passes cover the existing delivered features. They do not supply Phase8 coverage for absent implementation.

Commands used PowerShell 7 (`pwsh`). Backend command: `.venv/Scripts/python.exe -m pytest -q --junitxml=.cache/phase8-window4/pytest.xml`. Frontend build: `npm run build`. Browser command: `npx playwright test --config=playwright.phase7.config.ts`, with API/production/mock ports 5088/4388/4488 and `PHASE7_REPORT` directed to this audit cache. Only local replay servers were started; CFD runs started by this audit: 0.

## Execution evidence

Raw records are in `D:/code_project/CFD_visiblesystem/.cache/phase8-window4/`:

- `runtime-source.json`, `runtime-source.log`, `audit_runtime_source.py`: actual HTTP response bodies, route catalog, 57 source hash checks, NPZ identities/times/shapes, scalar counts and closure checks.
- `source-before.json`, `source-after.json`, `preservation.json`: complete relative file lists and per-file pre/post SHA-256/size/mtime_ns.
- `pytest.xml`, `pytest.log`, `playwright.json`, `playwright.log`, `build.log`: executed regression records.
- `phase7-freeze-check.json`, `openapi.json`, `api.d.ts`, `type-generation.log`: freeze/catalog/type verification.
- `scientific-path-scan.txt`, `cross-flow-scan.txt`: source scan matches; cross-flow policy scan has no matches.

Only this handoff and local QA execution artifacts were added. Existing production edits were not changed. No scientific issue was automatically fixed. Audit complete; stopped.
