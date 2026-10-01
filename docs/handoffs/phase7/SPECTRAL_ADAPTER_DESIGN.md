# Phase 7B Window 1 — Frozen spectral adapter

The implementation is internal to the adapter boundary. The Window 0 canonical
models and five-operation protocol, Phase 4 public contracts, and Phase 5/6
API/frontend remain unchanged.

`backend.adapters.spectral_data.SpectralAdapter` implements
`SpectralAdapterProtocol`. Its default scientific root is `D:/Paper/passage6`;
all runtime input selectors are registered IDs, never paths or NPZ member names.
The only source is `experiments/linear_perturbation_analysis/FREEZE`.
Scientific scripts are read as hashed evidence, never imported or executed.

## Registered identities and loading

| Resource | Identity / recorded support |
| --- | --- |
| Dataset | `spectrum.q-0.000`, `spectrum.q-0.132`, `spectrum.q-0.264`, `spectrum.q-0.396` |
| Collection / common base | `spectrum.common-mach6` / `spectrum.common-mach6.base` |
| Fourier record | `<dataset>.mode-00` through `<dataset>.mode-16` |
| Raw vector | `<record>.<right-or-left>.rank-00.complex_vector.stored_vector`, ranks 0..31 |
| Validation run | `modal-validation.<original-history-basename>`; all 24 identities in `spectral_registry.RUNS` |
| Registry / data revision | `spectral-registry-v1` / `linear-perturbation-freeze-v1` |

The summary CSV is mode-major, then q-major. Filtering one q preserves its saved
0..16 order. The adapter rejects missing/duplicate/reordered identities instead
of repairing them. Each alpha and leading imaginary part must equal the saved
rank-0 complex eigenvalue; alpha must also equal the maximum real part of that
block's 512 values. Saved kappa is loaded verbatim, independently of mode identity.
No sorting, smoothing, interpolation, fitting or recomputation of eigensystems
occurs. Serialized matrices remain explicitly MISSING.

`load_eigenmode` loads and validates the existing selected vector and returns its
canonical metadata, evidence and array reference. `load_array(result_id,
array_id)` resolves that exact reference to the existing `ScientificArray` model.
Raw LEFT/RIGHT vectors retain complex128, real/imag elements, saved rank order,
and a C-order reshape from 512 conservative entries to [128,4]. Display projection
selections do not transform or discard the underlying complex values. Unknown
raw normalization/phase conventions remain UNKNOWN; the validation experiment's
initialization normalization is not applied to raw vectors.

Saved RIGHT primitive amplitude profiles are supported for density/u/v/pressure
and ranks 0..31 by exact component selection from the existing amplitude NPZ.
No primitive conversion is performed. Saved RIGHT localization fractions are
loaded from eigenvector_metrics.csv when present; absent metrics remain MISSING.
LEFT localization remains MISSING because the saved metric describes RIGHT
primitive energy. Its fixed x-cell mask is 58..66, zero based.

## Growth validation and missing assets

All 24 saved runs cover modes 1/4/8/12, q_at 0/.396 and epsilon 1e-4/1e-5/1e-6.
Linear/RK3/CFD growth rates, error fractions and the 33 CFD amplitude/time records
are read verbatim. The source summary is checked against its registered history,
mode-selection record and saved complex eigenvalue branch. At q_at=.396, modes
1 and 4 retain rank 1, rather than being relabeled as the spectral envelope's rank
0. Saved error definitions and fit selectors 0..32 are preserved, with no new fit.

Linear and RK3 amplitude histories were not saved. Growth responses therefore
use PARTIAL slots with a MISSING_ASSET issue; their existing rates and CFD history
remain available, and every linear amplitude Fact is MISSING. No exponential or
RK3 curve is synthesized. Internal `describe_capabilities` reports the missing
prediction histories and per-run support. If validation summary/history assets
are absent, that run's capability becomes unavailable. Missing vectors return
MISSING/MISSING_ASSET and do not disable the spectrum. No screenshot recovery or
fallback to non-frozen duplicates exists.

## Provenance and observation

43 selected asset bindings preserve Phase 1 inventory identities, SHA256 values,
formats and original verification status. Each operation verifies only its actual
dependencies against both the pinned registry and frozen manifest. Files are read
into immutable bytes, hashed before parsing, and reobserved for byte/stat changes.
DATA drift or mixed reads return an ERROR without numerical values. Missing assets
and unsupported selectors likewise have no value. No result cache masks later
source drift. Descriptions and results carry selected SourceAssets, recorded and
current hashes, verification basis/time, method identity/hash, and registry/data
revisions. The manifest retains its original AVAILABLE_UNVERIFIED status because
its self-hash was excluded upstream; observing its inventory hash does not promote
that status.

The array transport uses the unchanged ScientificArray header and its provenance
references to the corresponding domain result's complete evidence. This window
does not add public DTOs, API routes, registry activation or frontend code.

## Verification

Offline tests build explicitly synthetic immutable in-memory bundles and inject
missing files, hash drift, read races, malformed schemas and invalid selectors.
They never edit or copy back scientific files. Real-source tests compare every
alpha/imaginary/kappa row, selected complex vectors and primitive components,
all 24 growth runs, inventory bindings and frozen hashes exactly. Real tests skip
explicitly when the installation is absent; offline tests still run.

`SPECTRAL_SOURCE_AUDIT.json` records pre/post SHA256, size and modification time
for every file in the frozen experiment directory. The full backend regression
also verifies frozen Phase 4 contract hashes and Phase 5/6 acceptance.
