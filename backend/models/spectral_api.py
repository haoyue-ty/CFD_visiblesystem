"""Public HTTP projections for the Phase 7B Window 2 Spectral Lab API.

The internal Window 0/1 models (``SpectrumDataset``, ``SpectralPoints``,
``Eigenmode``, ``GrowthValidation``) stay the scientific source of truth but are
NOT registered as public HTTP DTOs: they embed evidence configuration and raw
source-asset records that the wire payload does not require. These views are the
response shapes the contract exposes (frozen 06 §10/§11), and they are strictly
derived from the internal models — the projector never fabricates a value, never
interpolates ``q_at`` and never invents a mode index.

Every view carries the four public identifiers the Spectral Lab relies on:

* ``representation``  — what the payload actually is (dataset / curve / eigenmode / validation)
* ``mode_index``      — the Fourier block ``ell`` for point/eigenmode views (never eigenpair rank)
* ``q_at``            — one of the four exact registered configurations
* ``verification``    — the frozen verification state, preserved verbatim
* ``provenance``      — pinned registry/data revisions and source asset identities

Views revalidate the scientific header so a service/adapter can never bypass the
frozen canonical validators.
"""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .core import (CanonicalModel, ErrorBody, Fact, ID, Integer, Number, PositiveInt,
                   ProvenanceRef, Text, Verification, fact_value)
from .evidence import MaskSpec
from .results import ArrayRef, ScientificResult

ModeIndex = Annotated[Integer, Field(ge=0, le=16)]
Fraction = Annotated[Number, Field(ge=0, le=1)]
Representation = Literal["SPECTRUM_DATASET", "SPECTRUM_CURVE", "EIGENMODE", "GROWTH_VALIDATION"]
EigenSide = Literal["LEFT", "RIGHT"]
EigenRepresentation = Literal["COMPLEX_VECTOR", "PRIMITIVE_PROFILE"]
ComplexProjection = Literal["COMPLEX", "REAL", "IMAGINARY", "AMPLITUDE"]


class SpectralHeader(CanonicalModel):
    """Shared scientific header every spectral view preserves verbatim."""

    result: ScientificResult
    q_at: Number
    verification: Verification
    provenance: ProvenanceRef


class SpectrumDatasetView(SpectralHeader):
    """SPEC01 metadata: one recorded q, 17 blocks, refs only — no 512-value dump."""

    representation: Literal["SPECTRUM_DATASET"] = "SPECTRUM_DATASET"
    dataset_id: ID
    collection_id: ID
    base_result_id: ID
    configuration_id: ID
    parameter_name: Literal["q_at"] = "q_at"
    record_count: Literal[17] = 17
    eigenvalues_per_block: Literal[512] = 512
    saved_vectors_per_side: Literal[32] = 32
    mode_indices: list[ModeIndex]
    wave_numbers: Fact[list[Number]]
    wave_number_definition: Text
    matrix_source: Fact[ID]
    matrix_availability: Literal["MISSING"] = "MISSING"
    mask: MaskSpec
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def complete_blocks(self):
        if self.mode_indices != list(range(17)):
            raise ValueError("A dataset summary preserves all 17 recorded Fourier blocks in order")
        values = fact_value(self.wave_numbers)
        if values is not None and len(values) != 17:
            raise ValueError("Wave numbers must correspond to all 17 recorded modes")
        return self


class SpectralPointView(SpectralHeader):
    """One Fourier block of a curve; ``mode_index`` is ell, never eigenpair rank."""

    representation: Literal["SPECTRUM_POINT"] = "SPECTRUM_POINT"
    spectrum_record_id: ID
    mode_index: ModeIndex
    wave_number: Fact[Number]
    real_lambda: Fact[Number]
    imag_lambda: Fact[Number]
    spectral_abscissa: Fact[Number]
    eigenvalue_rank: Literal[0] = 0
    eigenvalues_ref: ArrayRef


class SpectrumCurveView(SpectralHeader):
    """SPEC02: one q yields exactly 17 ordered points; no interpolation of q."""

    representation: Literal["SPECTRUM_CURVE"] = "SPECTRUM_CURVE"
    dataset_id: ID
    collection_id: ID
    base_result_id: ID
    configuration_id: ID
    points: list[SpectralPointView]

    @model_validator(mode="after")
    def ordered_curve(self):
        if [point.mode_index for point in self.points] != list(range(17)):
            raise ValueError("A spectral curve preserves all 17 unique modes in recorded order")
        ids = [point.spectrum_record_id for point in self.points]
        if len(ids) != len(set(ids)):
            raise ValueError("Fourier record identities must be unique")
        return self


class SpectralNormalizationView(CanonicalModel):
    id: ID
    definition: Fact[Text]
    phase_convention: Fact[Text]
    component_order: Fact[list[Text]]
    processing_ref: Fact[ID]
    evidence_refs: list[ID]


class EigenmodeView(SpectralHeader):
    """SPEC04: a saved LEFT/RIGHT vector or a saved primitive amplitude profile.

    ``representation`` distinguishes a raw complex vector from a primitive profile;
    ``mode_index`` is the Fourier block. Values load separately through ARRAY01.
    """

    representation: Literal["EIGENMODE"] = "EIGENMODE"
    eigenmode_id: ID
    spectrum_record_id: ID
    dataset_id: ID
    mode_index: ModeIndex
    side: EigenSide
    rank: Annotated[Integer, Field(ge=0, le=31)]
    field_component: Text
    eigen_representation: EigenRepresentation
    projection: ComplexProjection
    shape: Annotated[list[PositiveInt], Field(min_length=1)]
    normalization: SpectralNormalizationView
    localization_fraction: Fact[Fraction]
    localization_definition: Text
    mask_reference: MaskSpec
    values_ref: ArrayRef
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def vector_or_profile(self):
        ref = self.values_ref
        if ref.descriptor.shape != self.shape:
            raise ValueError("Eigenmode array shape must match its declared shape")
        if self.eigen_representation == "COMPLEX_VECTOR":
            if ref.descriptor.dtype != "complex128" or self.shape != [128, 4]:
                raise ValueError("Raw eigenvectors preserve 128 cells x 4 conservative components, complex128")
        else:
            if self.projection != "AMPLITUDE" or ref.descriptor.dtype != "float64" or self.shape != [128]:
                raise ValueError("Primitive profiles are one sourced component on 128 x cells")
        return self


class GrowthRatesView(CanonicalModel):
    linear: Fact[Number]
    rk3: Fact[Number]
    cfd: Fact[Number]


class ValidationRunView(CanonicalModel):
    """SPEC06: one registered validation-run identity (a selector, no numeric payload).

    The frontend needs the registered run identities to build the run selector; it
    must never construct a ``modal-validation.*`` id itself. This view carries the
    pinned registry's (mode, q_at, epsilon) triple verbatim — the same triple the
    saved summary CSV agrees with. Listing these identities reads only the pinned
    registry metadata, never a scientific source file.
    """

    run_id: ID
    mode_index: ModeIndex
    q_at: Number
    epsilon: Number
    label: Text


class ValidationRunListView(CanonicalModel):
    """SPEC06 response: the complete registered Fig13 run set (no filtering)."""

    representation: Literal["VALIDATION_RUN_LIST"] = "VALIDATION_RUN_LIST"
    run_count: Integer
    runs: list[ValidationRunView]

    @model_validator(mode="after")
    def complete_registry(self):
        if self.run_count != len(self.runs):
            raise ValueError("Validation run count must match the delivered run identities")
        ids = [run.run_id for run in self.runs]
        if len(ids) != len(set(ids)):
            raise ValueError("Validation run identities must be unique")
        return self


def project_validation_runs(rows: list[dict]) -> ValidationRunListView:
    """Registry triples -> SPEC06 list view (metadata only; no file is opened)."""
    return ValidationRunListView.model_validate({
        "run_count": len(rows),
        "runs": [{"run_id": row["run_id"], "mode_index": row["mode_index"],
                  "q_at": row["q_at"], "epsilon": row["epsilon"], "label": row["label"]}
                 for row in rows],
    })


class GrowthErrorView(CanonicalModel):
    absolute_discrepancy: Fact[Annotated[Number, Field(ge=0)]]
    relative_discrepancy: Fact[Annotated[Number, Field(ge=0)]]
    relative_discrepancy_format: Literal["FRACTION"] = "FRACTION"
    definition: Literal["ABS_SIGMA_CFD_MINUS_RK3_OVER_MAX_ABS_RK3_1"] = "ABS_SIGMA_CFD_MINUS_RK3_OVER_MAX_ABS_RK3_1"
    definition_id: ID
    evidence_refs: list[ID]


class GrowthValidationView(SpectralHeader):
    """SPEC05: one recorded Fig13 run; missing linear amplitudes stay explicit."""

    representation: Literal["GROWTH_VALIDATION"] = "GROWTH_VALIDATION"
    run_id: ID
    mode_index: ModeIndex
    epsilon: Number
    spectrum_record_id: ID
    eigenmode_id: ID
    time: list[Annotated[Number, Field(ge=0)]]
    step_indices: list[Integer]
    linear_amplitude: list[Fact[Annotated[Number, Field(ge=0)]]]
    cfd_amplitude: list[Fact[Annotated[Number, Field(ge=0)]]]
    growth_rate: GrowthRatesView
    error: GrowthErrorView
    amplitude_definition: Literal["ABS_PROJECTED_COEFFICIENT"] = "ABS_PROJECTED_COEFFICIENT"
    fit_start: Literal[0] = 0
    fit_end: Literal[32] = 32
    fit_point_count: Literal[33] = 33
    issues: list[ErrorBody] = []

    @model_validator(mode="after")
    def recorded_steps(self):
        if self.step_indices != list(range(33)) or any(
                len(values) != 33 for values in (self.time, self.linear_amplitude, self.cfd_amplitude)):
            raise ValueError("Validation preserves exactly 33 recorded steps 0..32")
        return self


# --- internal -> public projection ------------------------------------------------
#
# These helpers are the only place internal models become wire DTOs. They copy the
# already-validated scientific header verbatim and never synthesize a value: a MISSING
# fact stays a reason-bearing fact, a missing localization stays MISSING.

def _dump(value):
    return value.model_dump(mode="python") if isinstance(value, CanonicalModel) else value


def project_dataset(dataset) -> SpectrumDatasetView:
    """SpectrumDataset -> SPEC01 metadata view."""
    return SpectrumDatasetView.model_validate({
        "result": _dump(dataset.result),
        "q_at": dataset.parameter_value,
        "verification": _dump(dataset.verification),
        "provenance": _dump(dataset.provenance),
        "dataset_id": dataset.dataset_id,
        "collection_id": dataset.collection_id,
        "base_result_id": dataset.base_result_id,
        "configuration_id": dataset.configuration_id,
        "mode_indices": list(dataset.wave_number_range.mode_indices),
        "wave_numbers": _dump(dataset.wave_number_range.wave_numbers),
        "wave_number_definition": dataset.wave_number_range.definition,
        "matrix_source": _dump(dataset.matrix_source),
        "mask": _dump(dataset.mask),
        "evidence_refs": list(dataset.provenance.evidence_refs),
    })


def project_curve(points) -> SpectrumCurveView:
    """SpectralPoints -> SPEC02 curve view; the 17 points keep recorded order."""
    if not points.points:
        raise ValueError("A spectral curve requires at least one recorded point")
    head = points.points[0]
    return SpectrumCurveView.model_validate({
        "result": _dump(head.result),
        "q_at": points.parameter_value,
        "verification": _dump(head.verification),
        "provenance": _dump(head.provenance),
        "dataset_id": points.dataset_id,
        "collection_id": points.collection_id,
        "base_result_id": points.base_result_id,
        "configuration_id": points.configuration_id,
        "points": [{
            "result": _dump(point.result),
            "q_at": point.parameter_value,
            "verification": _dump(point.verification),
            "provenance": _dump(point.provenance),
            "spectrum_record_id": point.spectrum_record_id,
            "mode_index": point.mode_index,
            "wave_number": _dump(point.wave_number),
            "real_lambda": _dump(point.real_lambda),
            "imag_lambda": _dump(point.imag_lambda),
            "spectral_abscissa": _dump(point.spectral_abscissa),
            "eigenvalues_ref": _dump(point.eigenvalues_ref),
        } for point in points.points],
    })


def project_point(point) -> SpectralPointView:
    """One SpectralPoint -> SPEC03 record view."""
    return SpectralPointView.model_validate({
        "result": _dump(point.result),
        "q_at": point.parameter_value,
        "verification": _dump(point.verification),
        "provenance": _dump(point.provenance),
        "spectrum_record_id": point.spectrum_record_id,
        "mode_index": point.mode_index,
        "wave_number": _dump(point.wave_number),
        "real_lambda": _dump(point.real_lambda),
        "imag_lambda": _dump(point.imag_lambda),
        "spectral_abscissa": _dump(point.spectral_abscissa),
        "eigenvalues_ref": _dump(point.eigenvalues_ref),
    })


def project_eigenmode(eigenmode) -> EigenmodeView:
    """Eigenmode -> SPEC04 view (values load separately via ARRAY01)."""
    return EigenmodeView.model_validate({
        "result": _dump(eigenmode.result),
        "q_at": eigenmode.parameter_value,
        "verification": _dump(eigenmode.verification),
        "provenance": _dump(eigenmode.provenance),
        "eigenmode_id": eigenmode.eigenmode_id,
        "spectrum_record_id": eigenmode.spectrum_record_id,
        "dataset_id": eigenmode.configuration_id,
        "mode_index": eigenmode.mode_index,
        "side": eigenmode.side,
        "rank": eigenmode.rank,
        "field_component": eigenmode.field_component,
        "eigen_representation": eigenmode.representation,
        "projection": eigenmode.projection,
        "shape": list(eigenmode.shape),
        "normalization": {
            "id": eigenmode.normalization.id,
            "definition": _dump(eigenmode.normalization.definition),
            "phase_convention": _dump(eigenmode.normalization.phase_convention),
            "component_order": _dump(eigenmode.normalization.component_order),
            "processing_ref": _dump(eigenmode.normalization.processing_ref),
            "evidence_refs": list(eigenmode.normalization.evidence_refs),
        },
        "localization_fraction": _dump(eigenmode.localization_fraction),
        "localization_definition": eigenmode.localization_definition,
        "mask_reference": _dump(eigenmode.mask_reference),
        "values_ref": _dump(eigenmode.values_ref),
        "evidence_refs": list(eigenmode.provenance.evidence_refs),
    })


def project_validation(validation, *, partial_issues: list | None = None) -> GrowthValidationView:
    """GrowthValidation -> SPEC05 view; PARTIAL issues travel as reason-bearing facts."""
    return GrowthValidationView.model_validate({
        "result": _dump(validation.result),
        "q_at": validation.parameter_value,
        "verification": _dump(validation.verification),
        "provenance": _dump(validation.provenance),
        "run_id": validation.run_id,
        "mode_index": validation.mode_index,
        "epsilon": validation.epsilon,
        "spectrum_record_id": validation.spectrum_record_id,
        "eigenmode_id": validation.eigenmode_id,
        "time": list(validation.time),
        "step_indices": list(validation.step_indices),
        "linear_amplitude": [_dump(item) for item in validation.linear_amplitude],
        "cfd_amplitude": [_dump(item) for item in validation.cfd_amplitude],
        "growth_rate": {
            "linear": _dump(validation.growth_rate.linear),
            "rk3": _dump(validation.growth_rate.rk3),
            "cfd": _dump(validation.growth_rate.cfd),
        },
        "error": {
            "absolute_discrepancy": _dump(validation.error.absolute_discrepancy),
            "relative_discrepancy": _dump(validation.error.relative_discrepancy),
            "definition_id": validation.error.definition_id,
            "evidence_refs": list(validation.error.evidence_refs),
        },
        "issues": [_dump(issue) for issue in (partial_issues or [])],
    })
