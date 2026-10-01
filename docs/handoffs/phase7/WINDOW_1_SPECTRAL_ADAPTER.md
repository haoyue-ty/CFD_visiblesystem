WINDOW=1_SPECTRAL_ADAPTER
STATUS=PASS
BRANCH=phase7/spectral-adapter
MODES=0..16;17 per parameter;68 total Fourier records;mode identity and recorded order preserved
QAT_VALUES=0;0.132;0.264;0.396;4 exact registered configurations
EIGENMODE_SUPPORT=AVAILABLE;LEFT/RIGHT complex128;32 saved ranks per block;[128,4];real/imag preserved;MISSING_ASSET when absent
VALIDATION_SUPPORT=PARTIAL;all24 runs;linear/RK3/CFD recorded rates AVAILABLE;CFD33-point history AVAILABLE;linear/RK3 amplitude histories UNAVAILABLE
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
TESTS=PASS;156/156 adapter tests;722/722 full backend regression;53/53 final focused checks after metadata refinement
MERGE_READY=YES

Source: read-only `D:/Paper/passage6/experiments/linear_perturbation_analysis/FREEZE`.
All 43 registered dependencies match Phase 1 inventory identities/hashes and the
frozen manifest. Numerical domain results retain source assets, recorded/current
hashes, verification and pinned registry/data revisions. Selected dependencies
are reobserved; missing/drifted/malformed sources never return numerical values.

Mode and eigenpair rank remain distinct. Validation modes 1 and 4 at q_at=.396
retain the saved rank-1 branch; the spectral envelope remains rank 0. Spectrum
alpha, imaginary parts and kappa are loaded from saved rows and checked against
saved complex eigenvalues. No resorting, smoothing, interpolation, fitting,
screenshot recovery, eigensystem construction or CFD execution occurs.

Growth validation is PARTIAL because predicted amplitude histories are absent.
Their missing Facts and capability states remain explicit; no predictions are
synthesized. The original rates, error fractions and CFD histories are intact.
LEFT localization is MISSING because the saved localization metric is for RIGHT
primitive energy. Raw normalization and phase conventions remain UNKNOWN.
Serialized Fourier matrices remain MISSING.

Validation commands (PowerShell 7):

```powershell
.venv/Scripts/python.exe -m pytest -q tests/window1_spectral_adapter
# 156 passed in 31.83s
.venv/Scripts/python.exe -m pytest -q
# 722 passed in 125.84s
.venv/Scripts/python.exe -m pytest -q tests/window1_spectral_adapter -k 'offline_modes_parameters_complex_and_provenance or offline_growth_24 or real_complex_vectors or real_saved_primitive'
# 53 passed, 103 deselected in 13.64s
```

The full regression ran before the final unit-identity/metadata refinement; the
53 focused checks subsequently exercised the final spectrum, vector, primitive
and growth metadata. Real-source tests all ran in this environment, without skips.
Offline fault tests use synthetic immutable memory bundles and never alter source
files. `SPECTRAL_SOURCE_AUDIT.json` verifies all 93 frozen files' pre/post SHA256,
size and modification time are identical. Phase 4 contract hashes and Phase 5/6
freeze acceptance pass existing regression checks.

Delivery: `backend/adapters/spectral_data.py`,
`backend/registry/spectral_registry.py`, `tests/window1_spectral_adapter/`,
`SPECTRAL_ADAPTER_DESIGN.md`, and `SPECTRAL_SOURCE_AUDIT.json`.
No public schema/API/frontend activation is part of this window.

Existing untracked Window 0 models/protocol/tests/design and the Phase 6 freeze
prerequisite were recorded unchanged in prerequisite commit `6792ba6`, allowing
the Window 1 branch to be merged independently. The unrelated `.workbuddy/`
directory is excluded from this delivery.
