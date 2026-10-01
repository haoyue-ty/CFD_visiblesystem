WINDOW=2_SPECTRAL_API
STATUS=PASS
API_TESTS=PASS;31/31 window2_spectral_api;753/753 full backend regression
OPENAPI=UPDATED;6 SPEC paths;5 public views;CORE_MODELS+=5;frontend api.d.ts regenerated
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
MERGE_READY=YES

Delivered the Flask API for the Spectral Lab on top of the frozen Window 0/1
foundation. The adapter (`backend/adapters/spectral.py`,
`backend/adapters/spectral_data.py`) and the registry were NOT modified; the new
layer depends only on `SpectralAdapterProtocol`.

## Operations

Relative to `/api/v1`:

| id | GET path | response |
| --- | --- | --- |
| SPEC00 | `/spectra` | `ApiEnvelope[list[SpectrumDatasetView]]` |
| SPEC01 | `/spectra/{dataset_id}` | `ApiEnvelope[SpectrumDatasetView]` |
| SPEC02 | `/spectra/{dataset_id}/points` | `ApiEnvelope[SpectrumCurveView]` (17 ell) |
| SPEC03 | `/spectra/{dataset_id}/points/{mode_index}` | `ApiEnvelope[SpectralPointView]` |
| SPEC04 | `/spectra/{dataset_id}/eigenmodes/{mode_index}` | `ApiEnvelope[EigenmodeView]` |
| SPEC05 | `/spectra/validation/{run_id}` | `ApiEnvelope[GrowthValidationView]` (PARTIAL) |

## Required fields on every response

Each view extends a shared `SpectralHeader` and carries `representation`, `q_at`,
`verification` and `provenance`; point, curve and eigenmode views additionally carry
`mode_index` (ell, never eigenpair rank). `SpectralPointView` now carries the full
scientific header so a single-record fetch is as self-describing as a curve.

Representations: `SPECTRUM_DATASET`, `SPECTRUM_CURVE`, `SPECTRUM_POINT`,
`EIGENMODE`, `GROWTH_VALIDATION`.

## Error vocabulary

Added the four contract codes to `SCIENTIFIC_CODES` in `backend/core/errors.py`
plus typed builders `unknown_spectrum`, `unknown_mode`, `missing_eigenmode`,
`unsupported_parameter`:

* `UNKNOWN_SPECTRUM` (404 SCIENTIFIC) — the dataset/run selector is not registered
* `UNKNOWN_MODE` (404 SCIENTIFIC) — the Fourier mode index is not a recorded block
* `MISSING_EIGENMODE` (404 SCIENTIFIC) — registered selection, saved vector absent
* `UNSUPPORTED_PARAMETER` (422 SCIENTIFIC) — selector outside the verified set
* `SOURCE_ERROR` (500 SYSTEM) — the controlled frozen source could not be read faithfully

Mapping rule (both for raised `DomainError` and returned `ResourceSlot`): an
`UNSUPPORTED`/`UNSUPPORTED_COMBINATION` against an **unresolved** identity is a 404
"never registered"; against a **known** identity it is a 422 "registered but
unrenderable". A `MISSING` dataset/curve/point slot is `MISSING_ASSET`; a `MISSING`
eigenmode slot is `MISSING_EIGENMODE`.

## Architecture

Blueprint → `SpectralServiceImpl` → `SpectralAdapterProtocol` → controlled registry
→ READ_ONLY frozen source. No handler opens a file, calls `np.load`, reconstructs a
matrix, fits a growth curve or interpolates `q_at`. The service is a
Flask-independent seam (mirrors `AllocationServiceImpl`); the API layer only builds
the envelope. `create_app(..., spectral_adapter=...)` wires it; a missing adapter is
503 `FEATURE_NOT_ENABLED`.

The service resolves "unknown spectrum" against the adapter's own
`list_spectral_datasets()` (cached per revision) rather than a hard-coded module, so
production ids and MOCK ids resolve identically.

## Public DTOs (no internal model leak)

`backend/models/spectral_api.py` defines the wire views and the only internal→public
projectors (`project_dataset|curve|point|eigenmode|validation`). The internal
`SpectrumDataset/SpectralPoints/Eigenmode/GrowthValidation` remain UNREGISTERED in
`CORE_MODELS`; the five new views ARE registered so OpenAPI emits their schemas.

The Window 0 guard `test_internal_models_not_in_public_schema_catalog` was tightened
from a substring check to `backend\.models\.spectral(?!_)` so it still forbids the
internal module while allowing the public `spectral_api` surface.

## No guessing, no fabrication

* `q_at` is one of the four exact registered configurations; there is no continuous
  range and no interpolation.
* Eigenmode rank is one of the 32 saved ranks; the saved order is retained.
* A missing linear/RK3 amplitude history stays a reason-bearing `MISSING` fact;
  SPEC05 returns `PARTIAL` and the envelope carries the adapter's issue list.
* `verification` and `provenance` are copied verbatim from the scientific header.

## Verification

Real-source round trip (`SpectralAdapter` against the read-only FREEZE): all six
operations return 200; SPEC05 returns PARTIAL with 1 issue; dataset/curve/point/
eigenmode all carry the four required fields; `/nope` → 404 UNKNOWN_SPECTRUM,
`/points/99` → 404 UNKNOWN_MODE, `rank=99` → 422 UNSUPPORTED_PARAMETER,
unknown run → 404 UNKNOWN_SPECTRUM.

Offline acceptance: `tests/window2_spectral_api/` (31 tests, TEST-ONLY
`FakeSpectralAdapter` in the `mock.` namespace) covers valid, missing,
missing-eigenmode, unsupported, source failure, transport hygiene, revision
mismatch, undelivered adapter, and strict re-validation of every success payload
against the declared response model.

## Deliverables

* `backend/models/spectral_api.py` (new)
* `backend/services/spectral.py` (new)
* `backend/api/spectral.py` (new)
* `backend/schemas/requests.py` (SpectrumQuery / SpectrumModeQuery / EigenmodeQuery / ValidationQuery)
* `backend/core/errors.py` (4 codes + builders)
* `backend/core/app.py` (`spectral_adapter` DI + registration)
* `backend/models/__init__.py` (export + CORE_MODELS)
* `backend/services/__init__.py`
* `config/openapi.json`, `frontend/src/types/generated/api.d.ts` (regenerated)
* `tests/window2_spectral_api/` (new)
* `tests/window0_spectral_foundation/test_protocol_and_freeze.py`,
  `tests/window2_case8_api/test_case8_api_contract.py` (guard updates)

## Commands

```powershell
.venv/Scripts/python.exe -m pytest -q tests/window2_spectral_api   # 31 passed
.venv/Scripts/python.exe scripts/export_openapi.py                  # config/openapi.json
cd frontend; npm run generate:types                                  # api.d.ts
.venv/Scripts/python.exe -m pytest -q                               # 753 passed
```
