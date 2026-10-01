WINDOW=0_PHASE10_FOUNDATION
STATUS=PASS

MECHANISM_SCHEMA=PASS
MECHANISM_ORIGIN=SCHEMATIC
SUPPORTED_STATES=STRICT_1D,WEAKLY_2D
NEAR1D_NUMERICAL_SCAN=MISSING

SCENE_COUNT=7/7
SCENE_TARGETS=PASS
REAL_API_REUSE=YES
NUMERICAL_DATA_DUPLICATED=NO

PHASE8_BASE_UNCHANGED=YES
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0

NEXT=WINDOW1

## Baseline and review inputs

- BASE_COMMIT=5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3
- CURRENT_BRANCH=phase10/content-foundation
- WORKTREE=D:/code_project/CFD_visiblesystem_phase10_content_foundation
- INITIAL_WORKTREE_CLEAN=YES
- Frozen contracts read: `docs/03_USER_FLOW_AND_IA.md`, `04_SYSTEM_ARCHITECTURE.md`, `05_DATA_SCHEMA.md` §15, `06_API_CONTRACT.md` CONTENT01–03 and the owning scientific operations. All four files retain the baseline bytes.
- Prior delivery inputs: Phase5 Case8 integration audit, Phase6 Allocation integration audit, Phase7 Spectral integration audit; Phase8 accepted candidate and Cylinder/Cross-flow API handoffs at the baseline.
- The baseline retains an earlier `WINDOW_4_PHASE8_QA.md` FAIL report and does not yet contain the final Phase8 integration audit. The final audit was read directly from Git commit `fceb3b6c569cf381b04767da77b4b92418a4b5ed`, path `docs/handoffs/phase8/PHASE8_CYLINDER_CROSSFLOW_INTEGRATION_AUDIT.md`. It records `VALIDATED_CODE_COMMIT=5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3` and supersedes the earlier QA report. Its code was not imported into this worktree.
- No Phase9 files, branches or worktrees were used. Phase9 Closure remains outside this delivery.

## Delivered foundation

`backend/models/content.py` implements the frozen MechanismContent, MechanismNode, MechanismEdge, ScientificTarget, ScenePreset and SceneList fields with the existing strict canonical model policy. Unknown fields and numerical payload additions are rejected. Mechanism origin is the single literal `SCHEMATIC`; the seven ordered Scene IDs are exactly 1–7.

`config/content/mechanism.json` and `config/content/scenes.json` contain only controlled content, scientific references, discrete controls and limitations. `freeze_manifest.json` pins their exact SHA-256 bytes, version, Phase8 baseline and the missing Near-1D scan. This is a software content freeze; it does not upgrade scientific source verification.

`backend/registry/content_registry.py` loads independent validated content objects, rejects freeze drift, validates the scientific graph and curated controls, and supplies single-Scene lookup. Its qualitative state helper returns textual labels only. `backend/registry/content_bindings.py` resolves existing registered identities and returns request metadata. No numerical values are copied or computed. `scripts/verification/phase10_content.py` checks this foundation and the live operation catalog without numerical reads.

No existing runtime, frontend, numerical adapter, API catalog, OpenAPI export, generated types or bootstrap experiment registry was changed. CONTENT01–03 HTTP delivery and the shared Vue views remain for the next window. The foundation is directly loadable by subsequent work; no database is required.

## Mechanism boundary

The graph contains Interface state → Background PSD kernel and Interface state → Acoustic information → Acoustic gate J. J routes the q_aa normal acoustic pathway and the q_at tangential pathway. Tangential receiving content has its own edge into tangential output, with no direct or indirect edge into J.

- J is constructed from acoustic / normal information. `delta_t (δ_t) DOES NOT ENTER THE GATE` is explicit.
- q_at OFF disables its output pathway without declaring the acoustic trigger inactive.
- STRICT_1D with q_at ENABLED preserves a potentially nonzero trigger. The tangential jump and receiving content vanish, hence cross-mode tangential output vanishes.
- WEAKLY_2D can retain the same/similar acoustic trigger and have nonzero tangential receiving content. Enabled output is conditional; actual dissipative amplitude depends on that content.
- Near-1D action `O(epsilon)` and entropy `O(epsilon^2)` appear only in a theory limitation. `NO_AUTHORITATIVE_NEAR1D_RAW_SCAN` is explicit. No epsilon control, numerical chart, five-point scan, formal Near-1D experiment or Fig13 substitution is registered.

The Mechanism Evidence reference resolves to the existing frozen Spectrum record including production method source/hash, explicitly labelled as implementation context. Spectral numerical results are not presented as evidence for the missing asymptotic scan.

## Exact Scene bindings

| Scene | View | Existing resource/API reuse | Allowed controls |
| --- | --- | --- | --- |
| 1 — How much dissipation? | ENTROPY | Case8 B_u and D_u; C805 for real cumulative background/normal/tangential budget histories | B_u / D_u |
| 2 — What triggers it? Where does it act? | MECHANISM | Shared frozen schematic; optional endpoint instantaneous diagnostic is not selected in Window 0 | Trigger/output node selection |
| 3 — Trigger ≠ Output | MECHANISM | Same schematic and qualitative state explanation | STRICT_1D / WEAKLY_2D; OFF / ENABLED |
| 4 — Same budget ≠ Same allocation | ALLOCATION | ALLOC04 `/api/v1/allocations/comparison?experiment_id=gate&representation_type=CELL_FIELD`; registered Acoustic/Pressure/Ungated allocations | Three frozen Gates |
| 5 — Positive entropy ≠ Uniform modal damping | SPECTRUM | SPEC02 `/api/v1/spectra/{dataset_id}/points`; q_at 0 and .396; both complete ell 0–16 curves | Two recorded q values; every mode 0–16 |
| 6 — Same pathway ≠ Same macroscopic response | CROSS_FLOW | CMP01 `/api/v1/comparisons/case8-cylinder?case8_config=D_u&cylinder_config=D_u`; original Case8 native-face and Cylinder sector/front-band resources | Fixed D_u / D_u |
| 7 — Real solver / frozen evidence / hash | EVIDENCE | Existing EVI02 records with method/config/source/hash/verification/limitations | Five registered evidence choices |

Gate matched values, maps and summary values remain in their existing owning registry/API. Scene 5 does not hide modes beyond 4/8. Scene 6 requires `DESCRIPTIVE_ONLY` and `NO_UNIFIED_RANKING`, with Cylinder cumulative2D still MISSING and Case8 allocation still DIAGNOSTIC_RERUN. Scene 7 preserves UNKNOWN and per-result verification. Its evidence selector is a small curated subset, not a complete Evidence Center index.

The exact Phase8 ALLOC and SPEC paths are used, including the accepted differences from the early GATE/SPEC draft paths. Frozen contracts were not edited to erase those recorded delivery decisions.

## Verification

FOUNDATION_TESTS=58/58;0 failures/errors/skips
BACKEND_FULL_RUN=1044 passed;0 failures/errors;1 cache-dependent skip
PRESERVATION_FOLLOWUP=1/1 PASS;initially skipped check covered
BACKEND_UNIQUE_CHECKS_COVERED=1045/1045
CONTENT_AUDIT=PASS;14 real targets;28 registered API bindings;0 numerical reads
SOURCE_PRESERVATION=PASS;189/189 accepted dependencies unchanged
FROZEN_03_04_05_06=UNCHANGED
EXISTING_PHASE8_TRACKED_FILES_CHANGED=0
GIT_DIFF_CHECK=PASS

The independent worktree initially lacked the legacy `.cache/phase6/source-before.json`, so the full run skipped its one cache-dependent preservation check. A fresh local inventory was checked against all 189 accepted dependencies and supplied as that baseline; the exact skipped test then passed separately. No test code or scientific source was changed to clear this environmental condition. All 1045 unique backend checks are covered; the full-run XML retains the original skip.

Commands use PowerShell 7 and the existing project Python runtime:

```powershell
& D:/code_project/CFD_visiblesystem/.venv/Scripts/python.exe -m scripts.verification.phase10_content
& D:/code_project/CFD_visiblesystem/.venv/Scripts/python.exe -m pytest -q --junitxml=.cache/phase10/backend-full.xml
& D:/code_project/CFD_visiblesystem/.venv/Scripts/python.exe -m pytest -q tests/window0_phase10_foundation --junitxml=.cache/phase10/foundation-tests.xml
git diff --check
```

The new tests cover origin, graph direction, trigger/output separation, all four qualitative state combinations, the Near-1D gap, exact scene identities/views, real target/evidence resolution, complete spectral modes, CMP01 policy, forbidden payloads/controls, independent loads and freeze tampering. Flask test-client checks use the existing real read-only adapters. No server, CFD job, database or email operation was started.

Durable execution summary: `FOUNDATION_VALIDATION.json`. Local XML execution records remain under `.cache/phase10/`. Source preservation covers the 189 accepted scientific dependencies by exact path/SHA-256/size/mtime_ns, compared with the Phase8 accepted inventory and again before/after this verification. This is a selected-dependency check, not a new full-tree source audit.

WINDOW1_STARTED=NO
STOP=Window 0 foundation complete; next window requires separate instruction.
