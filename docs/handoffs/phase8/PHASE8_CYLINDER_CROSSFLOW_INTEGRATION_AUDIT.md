PHASE8_CYLINDER_CROSSFLOW_INTEGRATION=PASS
BOOTSTRAP=PASS
CYLINDER_ADAPTER=PASS
CYLINDER_API=PASS
CROSS_FLOW_COMPOSITE=PASS
FRONTEND=PASS
EVIDENCE=PASS

CONFIGS=3/3
SNAPSHOTS=15/15;5/config;recorded NPZ times and completed steps preserved
SCALAR_ROWS=29271/29271;9757/config;35 registered scalar series/config;4 complete cumulative channels
SECTORS=16/16
EDGES=17/17
FRONT_BAND=PASS
CUMULATIVE_2D=MISSING

CMP01=PASS;12/12 valid config combinations
COMPARABILITY=DESCRIPTIVE_ONLY
RANKING_POLICY=NO_UNIFIED_RANKING
REAL_BROWSER=PASS;Cylinder D_u Flow->Entropy->Sector Allocation->Metrics->Evidence;Case8 D_u vs Cylinder D_u
REPRESENTATIONS=Case8 FACE_FIELD;Cylinder ANGULAR_SECTORS+REGION_SCALAR;distinct renderers verified
REAL_MISSING_TEST=PASS;typed MISSING slot has no value;direct cumulative2D/array requests404 without data;UI Missing without plot
SCIENTIFIC_BOUNDARY=pathway budget != pathway allocation != macroscopic consequence
PROHIBITED_CONCLUSIONS=NONE;no damping/stability/universality/ranking-transfer inference

BACKEND_TESTS=987/987;0 failures;0 errors;0 skipped
PHASE5_TESTS=273/273 shared+Case8
PHASE6_TESTS=146/146
PHASE7_TESTS=371/371
PHASE8_TESTS=197/197;Bootstrap34+Adapter83+API80
SCIENTIFIC_REGRESSION=PASS;Case8 truth/semantics/provenance60;real Allocation15;real Spectral34;Cylinder source/adapter117
FRONTEND_TESTS=5/5 unit;typecheck PASS;production build PASS
E2E=87/87 browser;full runner92/92;0 skipped;0 unexpected;0 flaky;retries0
OPENAPI=PASS;3.1 validation+independent export equality;pre-existing components unchanged
GENERATED_TYPES=PASS;independent regeneration byte-identical

PHASE4_HASH_UNCHANGED=PASS;3/3 exact raw hashes
PHASE5_FROZEN=PASS;FROZEN_ACCEPTED;record+manifest exact accepted bytes
PHASE6_FROZEN=PASS;FROZEN_ACCEPTED;record unchanged;17/17 source dependencies unchanged
PHASE7_FROZEN=PASS;FROZEN_ACCEPTED;freeze/evidence bytes unchanged;161 accepted files archived;shared integration seams explicitly extended

SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
SOURCE_PRESERVATION=PASS;24842/24842 full-tree files;189/189 selected/dependencies;path/hash/size/mtime_ns identical
SOURCE_FINGERPRINT=caa10a4ecf529cebed34c2eab0fb4d59253c2a408b082fd396808612c6aa7d11;pre=post

KNOWN_LIMITATIONS=5
1=Selected J2C-v2 cumulative2D and five-frame density/pressure movie are MISSING;native diagnostic checkpoints only.
2=Independent Fig15 cumulative2D rerun exists outside the frozen selection and is excluded.
3=A/B q_at=0 fractions are N/A;exact stage-state physical times remain UNKNOWN.
4=Cylinder B/D width readings are detector-limited;HF/width/localization/budget definitions and scopes differ between flows.
5=Cylinder remains VERIFIED_NOT_FROZEN;Case8 D_u cumulative allocation is DIAGNOSTIC_RERUN;Vite retains nonblocking chunk warning.

BLOCKERS=NONE
WINDOW4_FINAL_QA=PASS;supersedes retained pre-integration FAIL report
RUNNER_CORRECTIONS=Wrong Evidence selector corrected;concurrent HTTP audit isolated;final full run separately executed with unchanged timeouts and zero retries;earlier failures retained.
BRANCH=codex/phase8-final-integration
VALIDATED_CODE_COMMIT=5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3
ORIGINAL_WORK_PRESERVED=214 original files in .cache/phase8-final/primary-before.zip;prior dirty Git state in stash@{0}
EXECUTION_EVIDENCE=docs/handoffs/phase8/PHASE8_CYLINDER_CROSSFLOW_INTEGRATION_EVIDENCE.json;.cache/phase8-final/
VALIDATION_COMMANDS=.venv/Scripts/python.exe -m pytest -q;npm run build --prefix frontend;cd frontend && npx playwright test --config playwright.phase8.integration.config.ts
NEXT=STOP_AND_REVIEW
