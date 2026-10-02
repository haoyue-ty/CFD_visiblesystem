WINDOW=2_EVIDENCE_UI
STATUS=PASS

EVIDENCE_CENTER=PASS
CURRENT=PASS
GAPS=PASS
HISTORY=PASS

EVIDENCE_DETAIL=PASS
QUICK_VIEW=PASS

METHOD_HASH=PASS
SOURCE_ASSETS=PASS
PROCESSING_LINEAGE=PASS
LIMITATIONS=PASS
SOURCE_DRIFT_UI=PASS
SOURCE_DRIFT_FILTER_SCOPE=CURRENT_SERVER_PAGE_ONLY;accepted EVI01 has no source_drift query

RETURN_CONTEXT=PASS
ABSOLUTE_PATH_EXPOSED=NO
FILE_DOWNLOAD_EXPOSED=NO
MOCK_IN_PRODUCTION=NO

FRONTEND_TESTS=PASS;15/15 unit;10 new evidence unit tests
E2E=PASS;183/183 browser;148 production + 35 isolated mock-development;22 new evidence E2E;retries=0;failures=0;skipped=0;flaky=0
BUILD=PASS;vue-tsc and Vite production build
RECHECK_FRONTEND_TESTS=PASS;15/15 unit
RECHECK_E2E=PASS;147/147 production browser;22 evidence acceptance tests included;retries=0;failures=0;skipped=0;flaky=0
RECHECK_BACKEND_EVIDENCE_TESTS=PASS;62/62
RECHECK_BUILD=PASS;production JS/CSS hashes identical to delivery

SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
SOURCE_BASELINE_PRESERVED=PASS;27742/27742
SOURCE_DIRECTORY_ADDITIONS=101;unregistered;not written by this task

MERGE_READY=YES
BLOCKERS=NONE

BRANCH=phase11/evidence-ui
WORKTREE=C:/Users/t/.codex/worktrees/phase11-evidence-ui/CFD_visiblesystem
ACCEPTED_WINDOW1_COMMIT=a09b928d5c48aa262293066ce3543fb37c575d0f
INITIAL_WORKTREE_CLEAN=YES
BACKEND_EVIDENCE_TESTS=PASS;62/62

## Delivery

The top-level Evidence navigation and Home entry open P08 at `/evidence`. CURRENT, GAPS and HISTORY are separate route-backed sections; only the selected section is rendered. EVI01 applies section, experiment and verification filters before server pagination, with 20 records per request. No complete-registry preload or detail-per-card request is used. Cards show the server title, experiment, registered result/config identities, verification, drift, result count, principal limitation and full-detail navigation. The frozen index has no independent config field; config identifiers remain visible in registered result identities when applicable, and the full record supplies the authoritative config fact.

The frozen EVI01 query **does not allow source_drift**. The source-drift control therefore filters the currently loaded server page, retaining that page's offset. Both the control label and explanatory text say this explicitly. Next/Previous navigate the server pages, and the UI distinguishes server totals from displayed matches. This is a page-local drift filter, not a global server drift search. No frozen backend/schema/OpenAPI/types change is introduced to pretend otherwise. An eventual global drift query requires a separate backend contract change.

GAPS includes the actual Cylinder cumulative 2D, authoritative Near-1D five-epsilon raw and serialized Spectrum matrices records, all MISSING. Registered reasons, affected scope and independently supported objects remain visible. Other gaps retain the backend limitations and explicit uncertainty when their unaffected results are not enumerated. No Generate/Reconstruct/Interpolate/Fill actions exist. HISTORY has an explicit historical/nonselected banner and separate visual treatment. P09 preserves this context and displays a successor link only when superseded_by is KNOWN.

## Full record and shared Quick View

P09 reads the complete generated EvidenceRecord directly through the API-only evidence service, independently of previously loaded scientific modules. It shows result headers and support boundaries; recorded method, implementation and data hashes; KNOWN configuration parameters and protocol facts; every source asset's role/display/relative origin/format/hashes/drift/verification/canonical selection; freeze identity/manifest/time; actual processing records; definitions, units, time/spatial rules, masks and detectors; limitations; source observations; related evidence and registered result/source bindings. Missing parent fields and absent dates are explained, without inferred scientific facts or dates.

The frozen verification enum is displayed alongside readable labels. FROZEN_VERIFIED maps to FROZEN / FROZEN_ACCEPTED, DERIVED_VERIFIED to VERIFIED (derivation); VERIFIED_NOT_FROZEN, PARTIAL, MISSING, LEGACY/SUPERSEDED, AVAILABLE_UNVERIFIED and NOT_APPLICABLE remain distinct. DIAGNOSTIC_RERUN is a result-origin fact rather than an invented VerificationStatus. SOURCE DRIFT precedes verification and retains recorded/current comparisons. Evidence inspectability never certifies numerical availability.

The existing EvidenceLink opens one shared modal drawer across Case8, Gate, Allocation, Spectrum, Validation, Cylinder, Cross-flow, Closure, Mechanism and Explore. The earlier Mechanism-specific quick button/panel was removed. Quick View displays result/content identity, experiment/config, semantics/scope, method/hash, freeze reference, verification, source summary and limitations, plus View full record. Positive asset drift shows recorded/current asset hashes. Escape, Close and backdrop dismissal retain the mounted result and restore trigger focus; background controls are inert and focus remains inside the drawer. Modified anchor clicks still open the independently shareable P09 route.

Mechanism's own non-numerical theory/implementation record is discovered using EVI03 with the CONTENT03 content identity. Its separate linked spectral records retain their numerical scope. No numerical header is manufactured for the schematic.

## Return state and public safety

Internal return contexts preserve Case8 D_u Allocation, Spectrum mode8/q_at=.396, Explore Scene6 and the existing Cylinder/Cross-flow/Closure/Mechanism selectors. P09 pops the actual previous result entry when it matches; direct/shared detail links use their validated internal return target. Browser Back is covered separately. Allocation family, Gate configuration and comparison visibility now persist on the result URL so explicit return, browser Back and reload restore the same state.

Public provenance stays text, never a filesystem link. The evidence service additionally strips absolute/file/UNC locators from display/error strings. Source assets provide no download action. Return contexts accept only known internal named routes and reject external/path-based targets. API/network failures and unknown evidence IDs show honest Error/Missing states, without synthetic fallback. Development mock result IDs intentionally remain unresolved on the real evidence API; mock-development assertions were updated accordingly.

## Validation

Final counts and machine reports are recorded in WINDOW2_VALIDATION.json, WINDOW2_FRONTEND_TESTS.xml and WINDOW2_BACKEND_EVIDENCE_TESTS.xml. The frontend runner includes the accepted Phase5–10 production and explicitly isolated mock-development projects, plus the new evidence acceptance tests. The production-artifact checks confirm no synthetic provider/scientific payload. Network/HTTP errors, drift and unsafe locator cases use test-only intercepted payloads; production code has no mock fallback.

Initial checks caught an old heading assertion, Allocation controls missing from the original history entry and an error-case test capturing its URL before initialization. These were repaired; initial/repair reports remain in `.cache/phase11-window2`. Final validation runs with retries=0 and preserves failed-run summaries separately from the final result.

All 27,742 accepted Window1 scientific files (5,429,246,095 bytes) retain identical relative paths, size, mtime_ns and SHA-256. The initial whole-tree audit matched Window1 exactly. The final audit observed 101 additional Jacobian-material and solver-copy files, making 27,843 files in the directory. None intersect canonical or inventory-registered source paths; no baseline file was modified or removed. This task performed no scientific-source writes and did not remove the additions. WINDOW2_SOURCE_PRESERVATION.json distinguishes PASS for accepted-baseline preservation from EXTERNAL_ADDITIONS_OBSERVED for the complete directory; whole_tree_identical=false. The source directory as a whole is therefore not claimed byte-identical. Backend, config, canonical metadata, OpenAPI/generated DTOs, frozen documents and scientific code/data remain unchanged. All numerical requests read existing results; no CFD solver was started. The pre-existing Vite chunk-size advisory remains.

Reproduce from this worktree using PowerShell 7:

```powershell
npm --prefix frontend run build
$env:E2E_API_PORT='5115'
$env:E2E_PRODUCTION_PORT='4415'
$env:E2E_MOCK_PORT='4515'
npm --prefix frontend exec -- playwright test --config frontend/playwright.phase11.window2.config.ts
.\.venv\Scripts\python.exe -m pytest tests/window1_evidence_core/test_evidence_core.py -q
```

The ignored .venv and frontend/node_modules junctions reuse already installed runtimes. Window2 ends with its delivery commit, without merging another branch, running CFD or starting the next window.

## Revalidation of the existing delivery

The repeated Window2 request found the requested branch and independent worktree already present and clean. Implementation commit `a5087dc323e2f0bade186e7b7216e152f171a1c6` directly descends from accepted Window1 commit `a09b928d5c48aa262293066ce3543fb37c575d0f`. The existing implementation was inspected against this request and retained. This follow-up changes delivery documentation and validation reports only.

Fresh validation passed 15 unit tests, all 147 production browser tests in the `phase5-10-real-api` project (including all 22 evidence acceptance tests), 62 backend evidence tests, and the production build. The browser run used one worker with zero retries and had no failures, skips or flaky tests. CURRENT, P09 and Quick View screenshots from this run were inspected. Production JS and CSS hashes match the original committed validation report exactly. The original 198-test complete-run reports remain available; this recheck did not rerun the separate Phase8 browser project or isolated mock-development projects.

Fresh reports: `WINDOW2_RECHECK_VALIDATION.json`, `WINDOW2_RECHECK_FRONTEND_TESTS.xml` and `WINDOW2_RECHECK_BACKEND_TESTS.xml`. The prior complete scientific-tree preservation report is retained; this recheck did not repeat that whole-tree hash audit. No scientific source writes or CFD runs were performed. Backend, contracts, canonical metadata and generated types remain identical to accepted Window1. Source drift remains an explicitly labeled filter of the current server page because the accepted EVI01 contract rejects a global `source_drift` query; experiment, verification and section use server filtering before pagination.

Reproduce the production recheck with PowerShell 7 from this worktree:

```powershell
npm --prefix frontend run build
$env:E2E_API_PORT='5125'
$env:E2E_PRODUCTION_PORT='4425'
$env:E2E_MOCK_PORT='4525'
npm --prefix frontend exec -- playwright test --config frontend/playwright.phase11.window2.config.ts --project=unit --project=phase5-10-real-api
.\.venv\Scripts\python.exe -m pytest tests/window1_evidence_core/test_evidence_core.py -q
```

Stop after committing this revalidation; no merge or next window is performed.
