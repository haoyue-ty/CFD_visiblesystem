from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.models import ComplexValue, ScientificArray, known, unresolved
from backend.models.spectral import Eigenmode, GrowthValidation, SpectrumDataset, SpectralPoint


@pytest.mark.parametrize("model,fixture", [(SpectrumDataset, "dataset_payload"), (SpectralPoint, "point_payload"),
                                         (Eigenmode, "eigenmode_payload"), (GrowthValidation, "growth_payload")])
def test_required_objects_roundtrip(model, fixture, request):
    value = model.model_validate(request.getfixturevalue(fixture))
    assert model.model_validate_json(value.model_dump_json()) == value
    assert value.scientific_scope == "SELECTIVE_MODAL_RESPONSE"
    assert value.verification.status == "NOT_APPLICABLE"  # synthetic, no new science certification


@pytest.mark.parametrize("q", [0.0, 0.132, 0.264, 0.396])
def test_all_recorded_q_values(q, dataset_payload):
    dataset_payload["parameter_value"] = q
    dataset_payload["evidence"]["configuration"]["parameters"][0]["value"] = known(q)
    assert SpectrumDataset.model_validate(dataset_payload).parameter_value == q


@pytest.mark.parametrize("q", [-1.0, 0.2, 0.4, 1.0, 0.3960000000000001, "0.396", True, float("nan"), float("inf")])
def test_no_interpolation_extrapolation_or_coercion(q, dataset_payload):
    dataset_payload["parameter_value"] = q
    with pytest.raises(ValidationError):
        SpectrumDataset.model_validate(dataset_payload)


@pytest.mark.parametrize("field", ["experiment_id", "configuration_id", "matrix_source", "wave_number_range",
                                  "parameter_value", "verification", "provenance", "evidence"])
def test_dataset_required_fields(field, dataset_payload):
    del dataset_payload[field]
    with pytest.raises(ValidationError):
        SpectrumDataset.model_validate(dataset_payload)


@pytest.mark.parametrize("field,value", [("matrix_source", known("pretend.matrix")), ("matrix_source", unresolved("Unknown")),
                                         ("matrix_availability", "AVAILABLE"), ("record_count", 68),
                                         ("saved_vectors_per_side", 512), ("eigenvalues_per_block", 32),
                                         ("record_count", 17.0), ("scientific_scope", "UNIVERSAL_STABILITY")])
def test_dataset_enum_and_scientific_limits(field, value, dataset_payload):
    dataset_payload[field] = value
    with pytest.raises(ValidationError):
        SpectrumDataset.model_validate(dataset_payload)


def test_wave_number_not_inferred_from_index(point_payload):
    point = SpectralPoint.model_validate(point_payload)
    assert point.mode_index == 8
    assert point.wave_number.root.state == "UNKNOWN"
    point_payload["wave_number"] = known(0.0)
    assert SpectralPoint.model_validate(point_payload).wave_number.root.value == 0.0


@pytest.mark.parametrize("indices", [list(range(16)), list(range(1, 18)), [0] * 17, list(reversed(range(17)))])
def test_complete_recorded_mode_range(indices, dataset_payload):
    dataset_payload["wave_number_range"]["mode_indices"] = indices
    with pytest.raises(ValidationError):
        SpectrumDataset.model_validate(dataset_payload)


@pytest.mark.parametrize("alpha", [-0.5, 0.0, 0.25])
def test_alpha_may_be_negative_zero_or_positive(alpha, point_payload):
    point_payload.update(real_lambda=known(alpha), spectral_abscissa=known(alpha))
    point = SpectralPoint.model_validate(point_payload)
    assert point.spectral_abscissa.root.value == alpha
    assert point.imag_lambda.root.value == -2.0


def test_complex_fact_missing_is_not_zero(point_payload):
    point_payload.update(real_lambda=unresolved("Absent pair", "MISSING"), imag_lambda=unresolved("Absent pair", "MISSING"),
                         spectral_abscissa=unresolved("Absent summary", "MISSING"))
    value = SpectralPoint.model_validate(point_payload)
    assert value.real_lambda.root.state == "MISSING"
    assert "value" not in value.model_dump()["real_lambda"]
    point_payload["real_lambda"] = known(0.0)
    with pytest.raises(ValidationError):
        SpectralPoint.model_validate(point_payload)


@pytest.mark.parametrize("field,value", [("mode_index", True), ("mode_index", 17), ("mode_index", "8"),
                                         ("eigenvalue_rank", 1), ("eigenvalue_rank", False),
                                         ("spectral_abscissa", known(0.5)), ("imag_lambda", known(float("nan"))),
                                         ("spectral_abscissa", None), ("experiment_id", "case8")])
def test_fourier_point_validation(field, value, point_payload):
    point_payload[field] = value
    with pytest.raises(ValidationError):
        SpectralPoint.model_validate(point_payload)


@pytest.mark.parametrize("projection", ["COMPLEX", "REAL", "IMAGINARY", "AMPLITUDE"])
def test_complex_projection_preserves_source(projection, eigenmode_payload):
    eigenmode_payload["projection"] = projection
    value = Eigenmode.model_validate(eigenmode_payload)
    assert value.values_ref.descriptor.dtype == "complex128"
    assert value.shape == [128, 4]
    assert value.normalization.definition.root.state == "UNKNOWN"
    assert value.localization_fraction.root.value == 0.0


@pytest.mark.parametrize("field,value", [("representation", "SCALAR_HEATMAP"), ("representation", "REAL"),
                                         ("projection", "MAGNITUDE"), ("side", "right"), ("rank", 32),
                                         ("rank", False), ("localization_fraction", known(-0.1)),
                                         ("localization_fraction", known(1.1)), ("field_component", "density")])
def test_eigenmode_enum_and_semantics(field, value, eigenmode_payload):
    eigenmode_payload[field] = value
    with pytest.raises(ValidationError):
        Eigenmode.model_validate(eigenmode_payload)


@pytest.mark.parametrize("dtype,shape,axes", [("float64", [128, 4], ["x", "conservative_component"]),
                                           ("complex128", [512], ["x"]),
                                           ("complex128", [128, 4], ["x", "y"])])
def test_complex_vectors_cannot_be_flat_spatial_scalars(dtype, shape, axes, eigenmode_payload):
    eigenmode_payload["shape"] = shape
    eigenmode_payload["values_ref"]["descriptor"].update(dtype=dtype, shape=shape, axes=axes)
    with pytest.raises(ValidationError):
        Eigenmode.model_validate(eigenmode_payload)


def test_complex_values_real_imag_roundtrip(eigenmode_payload):
    values = [ComplexValue(real=3.0, imag=-4.0)] * 512
    array = ScientificArray.model_validate({"result": eigenmode_payload["result"],
                                            "descriptor": eigenmode_payload["values_ref"]["descriptor"], "values": values})
    restored = ScientificArray.model_validate_json(array.model_dump_json())
    assert restored.values[0].real == 3.0 and restored.values[0].imag == -4.0
    assert restored.descriptor.dtype == "complex128"
    with pytest.raises(ValidationError):
        ScientificArray.model_validate({"result": eigenmode_payload["result"],
                                       "descriptor": eigenmode_payload["values_ref"]["descriptor"], "values": [5.0] * 512})


def test_primitive_amplitude_requires_sourced_component(eigenmode_payload):
    eigenmode_payload.update(representation="PRIMITIVE_PROFILE", projection="AMPLITUDE", shape=[128], field_component="density")
    eigenmode_payload["values_ref"]["descriptor"].update(dtype="float64", shape=[128], axes=["x"], element_count=128)
    with pytest.raises(ValidationError):
        Eigenmode.model_validate(eigenmode_payload)
    eigenmode_payload["normalization"]["component_order"] = known(["density", "u", "v", "pressure"])
    assert Eigenmode.model_validate(eigenmode_payload).field_component == "density"


@pytest.mark.parametrize("kind", ["gate", "indices", "index_base", "scope", "evidence"])
def test_mask_identity_and_fixed_indices(kind, eigenmode_payload):
    mask = eigenmode_payload["mask_reference"]
    if kind == "gate":
        mask["type"] = "GATE_CELL_SHOCK_WINDOW"
    elif kind == "indices":
        mask["index_sets"][0]["indices"] = list(range(59, 68))
    elif kind == "index_base":
        mask["index_sets"][0]["index_base"] = 1
    elif kind == "scope":
        mask["id"] = "wrong.mask"
    else:
        mask["evidence_refs"] = []
    with pytest.raises(ValidationError):
        Eigenmode.model_validate(eigenmode_payload)


def test_growth_missing_prediction_and_zero_cfd(growth_payload):
    value = GrowthValidation.model_validate(growth_payload)
    assert value.linear_amplitude[0].root.state == "MISSING"
    assert value.cfd_amplitude[0].root.value == 0.0
    assert value.growth_rate.linear.root.value == 0.0
    assert value.error.relative_discrepancy.root.value == 0.5  # denominator floor 1, not divide by zero


@pytest.mark.parametrize("field,value", [("mode_index", 16), ("parameter_value", 0.132), ("epsilon", 2e-5),
                                         ("time", [0.0] * 33), ("time", [0.0] * 32),
                                         ("step_indices", list(range(1, 34))), ("linear_amplitude", []),
                                         ("cfd_amplitude", [known(-1.0)] * 33), ("fit_start", False),
                                         ("fit_end", 31), ("run_id", "wrong.run")])
def test_validation_restrictions(field, value, growth_payload):
    growth_payload[field] = value
    with pytest.raises(ValidationError):
        GrowthValidation.model_validate(growth_payload)


@pytest.mark.parametrize("field,value", [("relative_discrepancy", known(50.0)), ("relative_discrepancy_format", "PERCENT"),
                                         ("definition", "ABS_CFD_MINUS_LINEAR"), ("evidence_refs", [])])
def test_frozen_growth_error_semantics(field, value, growth_payload):
    growth_payload["error"][field] = value
    with pytest.raises(ValidationError):
        GrowthValidation.model_validate(growth_payload)


@pytest.mark.parametrize("kind", ["empty_assets", "wrong_asset", "no_data", "unselected", "drift", "hash_drift",
                                 "config", "q", "verification", "provenance", "no_verification_evidence",
                                 "no_method", "method_refs", "method_source", "duplicate_assets"])
def test_provenance_required_and_linked(kind, point_payload):
    evidence = point_payload["evidence"]
    if kind == "empty_assets":
        evidence["source_assets"] = []
    elif kind == "wrong_asset":
        point_payload["provenance"]["source_asset_ids"] = ["absent"]
        point_payload["result"]["provenance"] = deepcopy(point_payload["provenance"])
    elif kind == "no_data":
        evidence["source_assets"][0]["role"] = "ANALYSIS"
    elif kind == "unselected":
        evidence["source_assets"][0]["canonical_selected"] = False
    elif kind == "drift":
        evidence["source_assets"][0]["data_drift"] = known(True)
    elif kind == "hash_drift":
        evidence["source_assets"][0].update(recorded_data_hash=known("a" * 64), current_data_hash=known("b" * 64))
    elif kind == "config":
        evidence["configuration"]["experiment_id"] = "case8"
    elif kind == "q":
        evidence["configuration"]["parameters"][0]["value"] = known(0.264)
    elif kind == "verification":
        point_payload["verification"]["basis"] = ["Changed basis"]
    elif kind == "provenance":
        point_payload["provenance"]["data_revision"] = "changed"
    elif kind == "no_verification_evidence":
        point_payload["verification"]["evidence_refs"] = []
    elif kind == "no_method":
        evidence["configuration"]["protocol"]["method_name"] = unresolved("No method")
    elif kind == "method_refs":
        evidence["configuration"]["protocol"]["protocol_asset_refs"] = []
    elif kind == "method_source":
        evidence["configuration"]["protocol"]["protocol_asset_refs"] = ["absent.method"]
    else:
        evidence["source_assets"].append(deepcopy(evidence["source_assets"][0]))
    with pytest.raises(ValidationError):
        SpectralPoint.model_validate(point_payload)


def production_point(point_payload):
    payload = deepcopy(point_payload)
    verification = payload["verification"]
    verification.update(status="FROZEN_VERIFIED", basis=["Synthetic verification guard test ONLY"])
    payload["result"].update(data_origin="FROZEN_PRODUCTION", verification=deepcopy(verification))
    source = payload["evidence"]["source_assets"][0]
    source.update(recorded_data_hash=known("a" * 64), verification=deepcopy(verification))
    return payload


def test_production_data_hash_required_without_inventing_method_hash(point_payload):
    payload = production_point(point_payload)
    value = SpectralPoint.model_validate(payload)
    assert value.evidence.configuration.protocol.method_hash.root.state == "UNKNOWN"
    assert value.evidence.source_assets[0].current_data_hash.root.state == "UNKNOWN"
    payload["evidence"]["source_assets"][0]["recorded_data_hash"] = unresolved("Not recorded")
    with pytest.raises(ValidationError):
        SpectralPoint.model_validate(payload)


@pytest.mark.parametrize("status", ["AVAILABLE_UNVERIFIED", "LEGACY", "SUPERSEDED", "PARTIAL"])
def test_unverified_data_cannot_be_promoted(status, point_payload):
    payload = production_point(point_payload)
    payload["evidence"]["source_assets"][0]["verification"]["status"] = status
    with pytest.raises(ValidationError):
        SpectralPoint.model_validate(payload)


def test_extra_claims_and_unknown_fields_rejected(point_payload):
    point_payload["all_modes_damped"] = True
    with pytest.raises(ValidationError):
        SpectralPoint.model_validate(point_payload)
