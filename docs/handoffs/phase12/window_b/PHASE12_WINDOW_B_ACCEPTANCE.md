# Phase12 Window B — independent final acceptance

```text
WINDOW=PHASE12_B
CANDIDATE_HEAD=81fe5d428b9d18261aab10ae483ebf62ae1c1d51
WINDOW_A_ACCEPTED_COMMIT=d9f2f1b66bf146cf3c42217f8509752f970755a1
WORKTREE_CLEAN_AT_START=YES
ACCEPTED_PRODUCT_TREE_IDENTICAL=YES
INDEPENDENT_ACCEPTANCE=PASS
BACKEND_TOTAL=1356
BACKEND_PASS=1356
BACKEND_FAIL=0
BACKEND_ERROR=0
BACKEND_SKIP=0
FRONTEND_TOTAL=217
FRONTEND_UNIT=15 passed
FRONTEND_E2E=202 passed; 167 production real API + 35 DEV-only mock
FRONTEND_FAIL=0
FRONTEND_SKIP=0
FRONTEND_FLAKY=0
RETRIES=0
TYPECHECK=PASS
PRODUCTION_BUILD=PASS
OPENAPI_31_VALIDATION=PASS
OPENAPI_EXPORT_EQUALITY=PASS
TS_REGEN_EQUALITY=PASS
PRODUCTION_SCIENTIFIC_MOCK_FALLBACK=0
SOURCE_PATH_EXPOSURE=0
EXPLORE_FULL_FLOW=PASS
LAB_FULL_FLOW=PASS
EVIDENCE_DEEP_LINK=PASS
STATE_RESTORE=PASS
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
BLOCKERS=NONE
```

B uses a new clean managed worktree on codex/phase12-final-acceptance. Git log, ancestry and diff show the actual A accepted implementation with only A reporting artifacts added since it; every product, contract, script and test file is identical. Runtime dependencies are the same pinned software installation, but build, source capture, server processes and all test evidence are fresh. B did not copy A test results as acceptance evidence. The fresh production bundle independently matches A byte for byte.

Full pytest and all projects of the existing combined Playwright runner passed unfiltered. The JSON argv confirms no grep/project restriction. Tests have one passed attempt each, no skipped or flaky cases, with workers=1/retries=0. Waitress, production Vite preview and isolated development Vite server use reuseExistingServer=false. Build includes vue-tsc. Complete JUnit/JSON/logs and validation.json record actual counts; the 35 explicitly separate development tests do not stand in for the 167 production API cases.

The complete Entry/Home/Explore S1–S7/Evidence/Scene/Lab-return journey asserts no page errors, console errors, server errors or unhandled request failures (expected navigation aborts excluded). The complete Lab paths, real charts, all six delivered catalog entries, capability hiding/config disabling/unsupported locations, injected outages, Quick View/Detail/provenance/assets, history navigation and refresh passed. Fresh production screenshots were reviewed for Strict1D trigger/output semantics and the complete 0…16 modal spectrum; both signs of modal change remain visible. S6 remains DESCRIPTIVE_ONLY / NO_UNIFIED_RANKING. Fully-discrete residual remains a numerical diagnostic, never an exact identity.

After both full suites, independent OpenAPI 3.1 validation, runtime/export/artifact equality, TypeScript byte equality, public payload audit and production bundle scan were rerun. The canonical generator itself also produced no tracked diff. Public audit covers 2,438 safe SourceAssets, nine real result/evidence families and the three required missing records. No source locator or download route is exposed. Context scan classifies 430 TEST_ONLY, 180 DEV_ONLY and 106 reachable spelling occurrences; reachable entries are guards, source badges, null loading/error states, types/comments or explicit scientific denials, with zero numerical mock fallback.

The fresh B pre-audit equals the original pre-Phase12 A audit for every path, size, mtime_ns and SHA-256. The post-suite B audit again equals B pre-audit: 27,843 files / 5,429,811,970 bytes, manifest `8c9bf82f0e0caa69ce671e057c4202faf42f4b579e92deee94aef7ad6f05ad46`. Audit files exist only in the software workspace. No scientific source or accepted scientific registry/adapter/content was changed, and no CFD run was started.

Required gaps remain Cylinder cumulative2D=MISSING, Near1D authoritative five-epsilon raw=MISSING and Spectrum serialized matrices=MISSING; saved linear/RK3 amplitude histories also remain MISSING. UNKNOWN facts are not false and recorded zero is not missing. The software vocabulary addition retains original scientific source status/basis/origin and frozen Fact wire compatibility, as documented by A. Source drift readability never implies current reproducibility; hashes retain their separate scientific meanings, with unknown composite data hashes retained.

B introduces only independently produced acceptance records. Its acceptance commit is the stable functional freeze target recorded in the following PHASE12_FINAL_HANDOFF.md. The final reporting commit contains no product changes. No functional blocker remains. The existing bundle-size advisory is deferred to authorized UI/competition polish.
