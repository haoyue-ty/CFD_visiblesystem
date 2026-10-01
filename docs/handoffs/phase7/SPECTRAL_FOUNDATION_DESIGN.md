# Phase 7A Window 0 — Spectral foundation bindings

Authority: frozen [Architecture](../../04_SYSTEM_ARCHITECTURE.md) §§2/5/7/13, [Schema](../../05_DATA_SCHEMA.md) §11/11.1, [API](../../06_API_CONTRACT.md) §§10/11. Phase 5/6 remain frozen. This window adds internal adapter models and a protocol only; the modules are intentionally absent from CORE_MODELS, route/catalog registration and schema exports.

The requested vocabulary is internal, with explicit bindings to the unchanged public contract:

| Internal domain | Frozen public binding for later windows |
| --- | --- |
| SpectrumDataset | Complete experiment for one recorded configuration: 17 Fourier blocks. Internal dataset_id selects that exact configuration; four descriptions share collection_id/base_result_id and comprise the public SpectrumDataset's 68 records, with collection_id → public dataset_id. They do not replace its full-dataset shape. configuration_id → config_id; parameter_value → q_at; wave_number_range.mode_indices → ell_values. |
| SpectralPoint / SpectralPoints | SpectrumRecord for one Fourier block: mode_index → ell, real_lambda/imag_lambda → leading_eigenvalue.real/imag; spectral_abscissa is max Re(lambda) over all 512 eigenvalues. rank is separate from ell. SpectralPoints validates one complete 17-mode curve without mixed configurations, bases or revisions. |
| Eigenmode | mode_index → ell; field_component → component; shape → values_ref.descriptor.shape; mask_reference → mask; localization_fraction must bind to the existing localization Metric and its exact definition. projection is an explicit internal display selection, never a replacement representation or verification. |
| GrowthValidation | One shared Fig13 run identity: mode_index → mode; recorded cfd_amplitude → ModalPoint.amplitude, growth_rate → sigma_LIN/RK3/CFD, error → existing summary discrepancy facts. time comes from the 33 original history records. |

All internal results carry the existing ScientificResult, identical Verification/ProvenanceRef, evidenced ExperimentConfig (including method name/hash and protocol asset refs), and selected SourceAssets with separate recorded/current hashes. Unknown method hash/current observations retain HashFact UNKNOWN; unverified DATA sources cannot supply production values. DATA hash drift blocks numerical objects. This is structural validation, not a new asset audit or scientific certification.

Only q_at 0/.132/.264/.396 is accepted exactly. No tolerance mapping, interpolation, extrapolation or new fitted curves. ell is 0..16; the wave number k is a separately sourced Fact with definition/evidence, not automatically ell or 2πell. Each block has 512 eigenvalues and top32 vectors per LEFT/RIGHT side. No serialized matrix exists: matrix_source is explicitly MISSING with a reason, not a path or permission to reconstruct.

Raw complex vectors retain complex128 shape [128,4], axes [x,conservative_component], C order, and real/imag elements through existing ComplexValue/ScientificArray. COMPLEX/REAL/IMAGINARY/AMPLITUDE selections preserve the underlying complex ref. Only an already sourced single-component primitive amplitude profile [128] is admitted separately; its component order must be known. No generic scalar heatmap representation exists. UNKNOWN normalization/phase remains explicit; no re-normalization or inferred primitive conversion occurs.

The spectrum mask is fixed x-cell58..66, zero based, independent of q, with its own identity/evidence. Localization fractions are [0,1] or unresolved Facts; neither localization nor a plot title establishes shock localization of modes4/8.

Fig13 validation admits only mode1/4/8/12 × q0/.396 × epsilon1e-4/1e-5/1e-6. A run preserves steps0..32, 33 actual times and projected coefficient magnitudes. Selected-branch rates are distinct from alpha(k). The frozen relative error is abs(sigma_CFD-sigma_RK3)/max(abs(sigma_RK3),1), a fraction; fit0..32 inclusive. Known discrepancy facts are checked against the full-precision rate formula without an invented tolerance; unresolved facts remain unresolved. linear_amplitude entries must remain MISSING when no saved/verified prediction is bound; this window does not synthesize exponentials or fit rates.

Scientific scope is SELECTIVE_MODAL_RESPONSE. Positive alpha, nonzero imaginary parts, zero growth, and mixed modal responses are valid. These objects cannot establish universal stability, all modes damped, q_at always improving stability, D_u always better, or a universal shock stabilizer.

SpectralAdapterProtocol declares the five requested operations with revision pinning and ID selectors. ResourceSlot expresses known missing/unsupported/error without a value. Future adapters must enforce dataset/base/q/ell/rank/run relations through registered identities and unchanged frozen baseline/normalization/processing definitions; models do not certify unregistered references. API layers never access source files directly. No concrete adapter, service, public DTO projection, registry activation, API or frontend is implemented in Window 0.
