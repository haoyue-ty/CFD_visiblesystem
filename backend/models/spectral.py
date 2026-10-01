"""Internal Spectral Lab foundation; never registered as public HTTP DTOs.

One dataset describes one recorded q configuration (17 Fourier blocks).
The four descriptions map to the frozen 68-record SpectrumDataset in a later
window. No source loading, matrix construction, interpolation or fitting lives
here. See docs/handoffs/phase7/SPECTRAL_FOUNDATION_DESIGN.md for wire bindings.
"""
from math import prod
from typing import Annotated, Literal

from pydantic import Field, AfterValidator, field_validator, model_validator

from .core import (CanonicalModel, Fact, ID, Integer, Number, PositiveInt,
                   ProvenanceRef, Text, Verification, fact_value)
from .evidence import MaskSpec, SourceAsset
from .experiments import ExperimentConfig
from .results import ArrayRef, ScientificResult


Q_AT_VALUES = (0.0, 0.132, 0.264, 0.396)
FOURIER_MODES = tuple(range(17))
VALIDATION_MODES = (1, 4, 8, 12)
VALIDATION_Q_AT_VALUES = (0.0, 0.396)
VALIDATION_EPSILONS = (1e-4, 1e-5, 1e-6)


def _recorded_q(value: float) -> float:
    if value not in Q_AT_VALUES:
        raise ValueError("q_at must exactly match 0, 0.132, 0.264 or 0.396")
    return value


QAt = Annotated[Number, AfterValidator(_recorded_q)]
ModeIndex = Annotated[Integer, Field(ge=0, le=16)]
EigenRank = Annotated[Integer, Field(ge=0, le=31)]
Fraction = Annotated[Number, Field(ge=0, le=1)]
Amplitude = Annotated[Number, Field(ge=0)]
EigenSide = Literal["LEFT", "RIGHT"]
EigenRepresentation = Literal["COMPLEX_VECTOR", "PRIMITIVE_PROFILE"]
ComplexProjection = Literal["COMPLEX", "REAL", "IMAGINARY", "AMPLITUDE"]


class SpectralEvidence(CanonicalModel):
    """Source hashes stay per asset; method identity stays in config.protocol."""
    configuration: ExperimentConfig
    source_assets: Annotated[list[SourceAsset], Field(min_length=1)]

    @model_validator(mode="after")
    def source_identity(self):
        ids = [asset.asset_id for asset in self.source_assets]
        if len(ids) != len(set(ids)):
            raise ValueError("Evidence assets must be unique")
        if not self.configuration.evidence_refs:
            raise ValueError("Configuration requires evidence")
        if not self.configuration.protocol.protocol_asset_refs:
            raise ValueError("Method identity requires protocol asset references")
        if any(ref not in ids for ref in self.configuration.protocol.protocol_asset_refs):
            raise ValueError("Protocol sources must be present in evidence")
        if fact_value(self.configuration.protocol.method_name) is None:
            raise ValueError("Method name must be identified; method hash may remain UNKNOWN")
        return self


class SpectralContext(CanonicalModel):
    """Internal context shares the existing scientific header and status policy."""
    result: ScientificResult
    experiment_id: Literal["spectrum", "modal-validation"]
    configuration_id: ID
    parameter_value: QAt
    verification: Verification
    provenance: ProvenanceRef
    evidence: SpectralEvidence
    scientific_scope: Literal["SELECTIVE_MODAL_RESPONSE"] = "SELECTIVE_MODAL_RESPONSE"

    @model_validator(mode="after")
    def context_matches(self):
        result, config = self.result, self.evidence.configuration
        if (result.experiment_id, result.config_id) != (self.experiment_id, self.configuration_id):
            raise ValueError("Spectral identity must match the scientific header")
        if (config.experiment_id, config.id) != (self.experiment_id, self.configuration_id):
            raise ValueError("Evidence configuration must match spectral identity")
        if self.verification != result.verification or self.provenance != result.provenance:
            raise ValueError("Verification and provenance must preserve the scientific header")
        params = [p for p in config.parameters if p.name == "q_at"]
        if len(params) != 1 or fact_value(params[0].value) != self.parameter_value:
            raise ValueError("q_at must match exactly one evidenced configuration parameter")
        if not self.verification.evidence_refs or not self.provenance.source_asset_ids:
            raise ValueError("Spectral results require verification evidence and source assets")
        assets = {a.asset_id: a for a in self.evidence.source_assets}
        for asset_id in self.provenance.source_asset_ids:
            if asset_id not in assets or not assets[asset_id].canonical_selected:
                raise ValueError("Provenance must resolve to selected evidence assets")
            asset = assets[asset_id]
            recorded, current = fact_value(asset.recorded_data_hash), fact_value(asset.current_data_hash)
            if fact_value(asset.data_drift) is True or (recorded is not None and current is not None and recorded != current):
                raise ValueError("Source data drift prevents numerical results")
            if result.data_origin != "MOCK" and asset.role == "DATA":
                if recorded is None:
                    raise ValueError("Numerical source assets require a recorded data hash")
                if asset.verification.status not in ("FROZEN_VERIFIED", "VERIFIED_NOT_FROZEN", "DERIVED_VERIFIED"):
                    raise ValueError("Unverified source data cannot supply numerical results")
        if not any(assets[ref].role == "DATA" for ref in self.provenance.source_asset_ids):
            raise ValueError("Numerical provenance must include a data asset")
        return self


class WaveNumberRange(CanonicalModel):
    """ell is an index, k is a sourced physical/model wave number, never guessed."""
    mode_indices: list[ModeIndex]
    wave_numbers: Fact[list[Number]]
    definition: Text
    evidence_refs: Annotated[list[ID], Field(min_length=1)]

    @model_validator(mode="after")
    def recorded_modes(self):
        if self.mode_indices != list(FOURIER_MODES):
            raise ValueError("A complete configuration contains ell 0 through 16 in source order")
        values = fact_value(self.wave_numbers)
        if values is not None and len(values) != 17:
            raise ValueError("Wave numbers must correspond to all 17 recorded modes")
        return self


def _fixed_mask(mask: MaskSpec, result: ScientificResult) -> None:
    if mask.type != "SPECTRUM_FIXED_SHOCK_CELLS":
        raise ValueError("Spectral localization requires the spectrum mask")
    if len(mask.index_sets) != 1:
        raise ValueError("Spectrum has one fixed x-cell index set")
    indices = mask.index_sets[0]
    if (indices.axis, indices.index_base, indices.indices) != ("x", 0, list(range(58, 67))):
        raise ValueError("Spectrum mask is fixed x cells 58..66, zero based")
    if not mask.evidence_refs or mask.id not in result.scope.mask_refs:
        raise ValueError("Mask evidence and result scope must agree")


class SpectrumDataset(SpectralContext):
    """Complete recorded experiment for one q; metadata only, no fabricated data."""
    experiment_id: Literal["spectrum"]
    dataset_id: ID
    collection_id: ID
    base_result_id: ID
    matrix_source: Fact[ID]
    matrix_availability: Literal["MISSING"] = "MISSING"
    wave_number_range: WaveNumberRange
    parameter_name: Literal["q_at"] = "q_at"
    record_count: Literal[17] = 17
    eigenvalues_per_block: Literal[512] = 512
    saved_vectors_per_side: Literal[32] = 32
    mask: MaskSpec

    @field_validator("record_count", "eigenvalues_per_block", "saved_vectors_per_side", mode="before")
    @classmethod
    def strict_counts(cls, value):
        if type(value) is not int:
            raise ValueError("Recorded counts must be strict integers")
        return value

    @model_validator(mode="after")
    def spectrum_scope(self):
        if self.matrix_source.root.state != "MISSING":
            raise ValueError("Serialized spectral matrices are known MISSING; do not reconstruct them")
        if (self.result.time.sampling, self.result.time.accumulation) != ("STATIC", "NONE"):
            raise ValueError("Spectrum datasets are static, not CFD trajectories")
        _fixed_mask(self.mask, self.result)
        return self


class SpectralPoint(SpectralContext):
    """One Fourier block: lambda is its leading eigenvalue; alpha=max Re(lambda).

    mode_index denotes ell, never eigenpair rank. Individual eigenpairs belong
    to Eigenmode; their real part must not be relabeled as the block envelope.
    """
    experiment_id: Literal["spectrum"]
    dataset_id: ID
    collection_id: ID
    base_result_id: ID
    spectrum_record_id: ID
    mode_index: ModeIndex
    wave_number: Fact[Number]
    real_lambda: Fact[Number]
    imag_lambda: Fact[Number]
    spectral_abscissa: Fact[Number]
    eigenvalue_rank: Literal[0] = 0
    eigenvalues_ref: ArrayRef
    spectral_abscissa_definition: Literal["MAX_REAL_ALL_512_EIGENVALUES"] = "MAX_REAL_ALL_512_EIGENVALUES"

    @field_validator("eigenvalue_rank", mode="before")
    @classmethod
    def strict_rank(cls, value):
        if type(value) is not int:
            raise ValueError("Eigenvalue rank must be a strict integer")
        return value

    @model_validator(mode="after")
    def point_semantics(self):
        if self.spectrum_record_id != self.result.result_id:
            raise ValueError("Fourier record identity must match its header")
        if (self.result.time.sampling, self.result.time.accumulation) != ("STATIC", "NONE"):
            raise ValueError("Fourier spectrum points are static")
        if self.result.semantic_id != "spectral_abscissa":
            raise ValueError("Fourier envelope requires spectral_abscissa semantics")
        if self.real_lambda.root.state != self.imag_lambda.root.state:
            raise ValueError("A complex eigenvalue requires both real and imaginary facts")
        real, alpha = fact_value(self.real_lambda), fact_value(self.spectral_abscissa)
        if real is not None and alpha is not None and real != alpha:
            raise ValueError("Leading eigenvalue real part must equal the block spectral abscissa")
        descriptor = self.eigenvalues_ref.descriptor
        if (descriptor.dtype, descriptor.shape, descriptor.axes) != ("complex128", [512], ["rank"]):
            raise ValueError("Each Fourier block references 512 complex eigenvalues in saved rank order")
        return self


class SpectralPoints(CanonicalModel):
    """A complete recorded curve under one configuration/base/revision."""
    dataset_id: ID
    collection_id: ID
    base_result_id: ID
    configuration_id: ID
    parameter_value: QAt
    points: list[SpectralPoint]

    @model_validator(mode="after")
    def complete_curve(self):
        if [point.mode_index for point in self.points] != list(FOURIER_MODES):
            raise ValueError("A spectral curve preserves all 17 unique modes in recorded order")
        ids = [point.spectrum_record_id for point in self.points]
        if len(ids) != len(set(ids)):
            raise ValueError("Fourier record identities must be unique")
        revisions = {(p.provenance.registry_revision, p.provenance.data_revision) for p in self.points}
        if len(revisions) != 1:
            raise ValueError("A curve cannot mix registry/data revisions")
        for point in self.points:
            if (point.dataset_id, point.collection_id, point.base_result_id, point.configuration_id, point.parameter_value) != (
                self.dataset_id, self.collection_id, self.base_result_id, self.configuration_id, self.parameter_value
            ):
                raise ValueError("A curve cannot mix dataset, base or configuration identities")
        return self


class NormalizationSpec(CanonicalModel):
    id: ID
    definition: Fact[Text]
    phase_convention: Fact[Text]
    component_order: Fact[list[Text]]
    processing_ref: Fact[ID]
    evidence_refs: Annotated[list[ID], Field(min_length=1)]


class Eigenmode(SpectralContext):
    experiment_id: Literal["spectrum"]
    eigenmode_id: ID
    spectrum_record_id: ID
    mode_index: ModeIndex
    side: EigenSide
    rank: EigenRank
    field_component: Text
    shape: Annotated[list[PositiveInt], Field(min_length=1)]
    normalization: NormalizationSpec
    localization_fraction: Fact[Fraction]
    localization_definition: Text
    mask_reference: MaskSpec
    representation: EigenRepresentation
    projection: ComplexProjection
    values_ref: ArrayRef

    @model_validator(mode="after")
    def complex_semantics(self):
        if self.eigenmode_id != self.result.result_id:
            raise ValueError("Eigenmode identity must match its header")
        if (self.result.time.sampling, self.result.time.accumulation) != ("STATIC", "NONE"):
            raise ValueError("Eigenmode spatial structure is static, not a CFD movie")
        ref = self.values_ref
        if ref.result_id != self.result.result_id or ref.descriptor.shape != self.shape:
            raise ValueError("Eigenmode array identity and shape must match")
        if self.representation == "COMPLEX_VECTOR":
            if ref.descriptor.dtype != "complex128" or self.shape != [128, 4]:
                raise ValueError("Raw eigenvectors preserve 128 cells x 4 conservative components, complex128")
            if ref.descriptor.axes != ["x", "conservative_component"]:
                raise ValueError("A component axis cannot be relabeled as a spatial cell axis")
            if self.field_component != "stored_vector":
                raise ValueError("Raw composite vectors use stored_vector; do not invent a component order")
        else:
            if self.projection != "AMPLITUDE" or ref.descriptor.dtype != "float64":
                raise ValueError("Only sourced primitive amplitude profiles are supported")
            if self.shape != [128] or ref.descriptor.axes != ["x"]:
                raise ValueError("Primitive profiles are one sourced component on 128 x cells")
            order = fact_value(self.normalization.component_order)
            if order is None or self.field_component not in order:
                raise ValueError("Primitive component identity requires sourced component order")
        if ref.descriptor.element_count != prod(self.shape):
            raise ValueError("Eigenmode size must preserve shape")
        _fixed_mask(self.mask_reference, self.result)
        return self


class GrowthRates(CanonicalModel):
    """Selected branch rates; never the full-spectrum alpha envelope."""
    linear: Fact[Number]
    rk3: Fact[Number]
    cfd: Fact[Number]


class GrowthError(CanonicalModel):
    absolute_discrepancy: Fact[Annotated[Number, Field(ge=0)]]
    relative_discrepancy: Fact[Annotated[Number, Field(ge=0)]]
    relative_discrepancy_format: Literal["FRACTION"] = "FRACTION"
    definition: Literal["ABS_SIGMA_CFD_MINUS_RK3_OVER_MAX_ABS_RK3_1"] = "ABS_SIGMA_CFD_MINUS_RK3_OVER_MAX_ABS_RK3_1"
    definition_id: ID
    evidence_refs: Annotated[list[ID], Field(min_length=1)]


class GrowthValidation(SpectralContext):
    """One recorded Fig13 run; missing linear amplitudes are not generated.

    Arrays are aligned to the 33 saved steps. No fitting or exponential curve
    construction is performed; error fields retain the frozen summary formula.
    """
    experiment_id: Literal["modal-validation"]
    run_id: ID
    mode_index: ModeIndex
    epsilon: Number
    spectrum_record_id: ID
    eigenmode_id: ID
    time: list[Annotated[Number, Field(ge=0)]]
    step_indices: list[Integer]
    linear_amplitude: list[Fact[Amplitude]]
    cfd_amplitude: list[Fact[Amplitude]]
    growth_rate: GrowthRates
    error: GrowthError
    amplitude_definition: Literal["ABS_PROJECTED_COEFFICIENT"] = "ABS_PROJECTED_COEFFICIENT"
    fit_start: Literal[0] = 0
    fit_end: Literal[32] = 32
    fit_point_count: Literal[33] = 33

    @field_validator("fit_start", "fit_end", "fit_point_count", mode="before")
    @classmethod
    def strict_fit(cls, value):
        if type(value) is not int:
            raise ValueError("Fit selectors must be strict integers")
        return value

    @model_validator(mode="after")
    def validation_semantics(self):
        if self.run_id != self.configuration_id:
            raise ValueError("Modal validation configuration identity is its recorded run id")
        if self.mode_index not in VALIDATION_MODES or self.parameter_value not in VALIDATION_Q_AT_VALUES or self.epsilon not in VALIDATION_EPSILONS:
            raise ValueError("Fig13 supports only modes 1/4/8/12, q_at 0/.396, epsilon 1e-4/1e-5/1e-6")
        for name, expected in (("mode", self.mode_index), ("epsilon", self.epsilon)):
            params = [p for p in self.evidence.configuration.parameters if p.name == name]
            if len(params) != 1 or fact_value(params[0].value) != expected:
                raise ValueError("Validation selection must match the evidenced run parameters")
        if self.step_indices != list(range(33)) or any(len(values) != 33 for values in (self.time, self.linear_amplitude, self.cfd_amplitude)):
            raise ValueError("Validation preserves exactly 33 recorded steps 0..32")
        if any(a >= b for a, b in zip(self.time, self.time[1:])):
            raise ValueError("Recorded validation times must be strictly ordered")
        if (self.result.time.sampling, self.result.time.accumulation) != ("PER_STEP", "NONE"):
            raise ValueError("Validation is projected amplitude history, not a spatial trajectory")
        rk3, cfd = fact_value(self.growth_rate.rk3), fact_value(self.growth_rate.cfd)
        if rk3 is not None and cfd is not None:
            absolute = abs(cfd - rk3)
            for fact, expected in ((self.error.absolute_discrepancy, absolute),
                                   (self.error.relative_discrepancy, absolute / max(abs(rk3), 1.0))):
                value = fact_value(fact)
                if value is not None and value != expected:
                    raise ValueError("Saved discrepancy must use the frozen CFD/RK3 definition")
        return self
