"""Synthetic model fixtures only; no spectral source assets are opened."""
from copy import deepcopy

import pytest

from backend.models.core import known, unresolved


@pytest.fixture
def spectral_context(result_payload):
    payload = deepcopy(result_payload)
    na = unresolved("Synthetic model fixture", "NOT_APPLICABLE")
    unknown = unresolved("Not observed in a model fixture")
    payload.update(result_id="mock.spectrum.point.8", experiment_id="spectrum",
                   config_id="q-0.396", semantic_id="spectral_abscissa")
    payload["time"].update(sampling="STATIC", physical_time=na, step_index=na,
                           snapshot_index=na, index_convention="RECORDED_FOURIER_MODE")
    payload["scope"]["mask_refs"] = ["mock.mask.spectrum"]
    payload["provenance"]["source_asset_ids"] = ["mock.data.asset"]
    unit = {"id": "mock.dimensionless", "system": "DIMENSIONLESS", "quantity": "coefficient",
            "label": "dimensionless", "si_mapping": na}
    verification = deepcopy(payload["verification"])
    source = {"asset_id": "mock.data.asset", "source_id": "mock.sources", "source_display": "SYNTHETIC TEST ONLY",
              "relative_origin": na, "role": "DATA", "format": "MODEL_FIXTURE",
              "recorded_data_hash": unknown, "current_data_hash": unknown, "data_drift": known(False),
              "verification": verification, "canonical_selected": True, "limitations": []}
    method = deepcopy(source)
    method.update(asset_id="mock.method.asset", role="METHOD")
    configuration = {
        "id": "q-0.396", "experiment_id": "spectrum", "name": "SYNTHETIC TEST ONLY",
        "parameters": [{"name": "q_at", "value": known(0.396), "unit": unit}],
        "protocol": {"method_name": known("synthetic-test-method"), "method_hash": unknown,
                     "grid": unknown, "integrator": unknown, "reconstruction": unknown,
                     "final_time": unknown, "boundary_scope": unknown,
                     "protocol_asset_refs": ["mock.method.asset"]},
        "verification": verification, "limitations": [], "evidence_refs": ["mock.evidence"],
    }
    return {"result": payload, "experiment_id": "spectrum", "configuration_id": "q-0.396",
            "parameter_value": 0.396, "verification": verification,
            "provenance": deepcopy(payload["provenance"]),
            "evidence": {"configuration": configuration, "source_assets": [source, method]}}


@pytest.fixture
def spectral_mask(spectral_context):
    return {"id": "mock.mask.spectrum", "type": "SPECTRUM_FIXED_SHOCK_CELLS", "domain_refs": ["mock.x"],
            "definition": "Fixed zero-based x cells 58..66", "parameters": [],
            "index_sets": [{"axis": "x", "indices": list(range(58, 67)), "index_base": 0}],
            "mask_array_refs": [], "scope": deepcopy(spectral_context["result"]["scope"]),
            "verification": deepcopy(spectral_context["verification"]), "evidence_refs": ["mock.evidence"]}


def array_ref(result_id, dtype, shape, axes):
    count = 1
    for size in shape:
        count *= size
    return {"result_id": result_id, "descriptor": {"array_id": "eigenvector", "dtype": dtype, "shape": shape,
            "order": "C", "axes": axes, "encoding": "FLAT_JSON", "element_count": count}}


@pytest.fixture
def dataset_payload(spectral_context, spectral_mask):
    return {**deepcopy(spectral_context), "dataset_id": "mock.spectrum.q-0.396", "collection_id": "mock.spectrum",
            "base_result_id": "mock.common-base", "matrix_source": unresolved("No serialized matrices", "MISSING"),
            "wave_number_range": {"mode_indices": list(range(17)), "wave_numbers": unresolved("Unbound k convention"),
                                  "definition": "k must be sourced separately from ell", "evidence_refs": ["mock.evidence"]},
            "mask": spectral_mask}


@pytest.fixture
def point_payload(spectral_context):
    return {**deepcopy(spectral_context), "dataset_id": "mock.spectrum.q-0.396", "collection_id": "mock.spectrum",
            "base_result_id": "mock.common-base", "spectrum_record_id": "mock.spectrum.point.8",
            "mode_index": 8, "wave_number": unresolved("Unbound k convention"),
            "real_lambda": known(0.25), "imag_lambda": known(-2.0), "spectral_abscissa": known(0.25),
            "eigenvalues_ref": array_ref("mock.spectrum.values.8", "complex128", [512], ["rank"])}


@pytest.fixture
def eigenmode_payload(spectral_context, spectral_mask):
    context = deepcopy(spectral_context)
    context["result"].update(result_id="mock.spectrum.eigenmode.8", semantic_id="eigenmode")
    return {**context, "eigenmode_id": "mock.spectrum.eigenmode.8", "spectrum_record_id": "mock.spectrum.point.8",
            "mode_index": 8, "side": "RIGHT", "rank": 0, "field_component": "stored_vector", "shape": [128, 4],
            "normalization": {"id": "mock.normalization", "definition": unresolved("Raw normalization unbound"),
                              "phase_convention": unresolved("Phase unbound"), "component_order": unresolved("Order unbound"),
                              "processing_ref": unresolved("No processing", "NOT_APPLICABLE"), "evidence_refs": ["mock.evidence"]},
            "localization_fraction": known(0.0), "localization_definition": "Synthetic fixed-mask localization test",
            "mask_reference": spectral_mask, "representation": "COMPLEX_VECTOR", "projection": "COMPLEX",
            "values_ref": array_ref("mock.spectrum.eigenmode.8", "complex128", [128, 4], ["x", "conservative_component"])}


@pytest.fixture
def growth_payload(spectral_context):
    context = deepcopy(spectral_context)
    context.update(experiment_id="modal-validation", configuration_id="mock.fig13.m08")
    context["result"].update(experiment_id="modal-validation", config_id="mock.fig13.m08",
                             result_id="mock.fig13.m08.history", semantic_id="modal_validation")
    context["result"]["time"]["sampling"] = "PER_STEP"
    config = context["evidence"]["configuration"]
    config.update(experiment_id="modal-validation", id="mock.fig13.m08")
    unit = deepcopy(config["parameters"][0]["unit"])
    config["parameters"] += [{"name": "mode", "value": known(8), "unit": unit},
                             {"name": "epsilon", "value": known(1e-5), "unit": unit}]
    return {**context, "run_id": "mock.fig13.m08", "mode_index": 8, "epsilon": 1e-5,
            "spectrum_record_id": "mock.spectrum.point.8", "eigenmode_id": "mock.spectrum.eigenmode.8",
            "time": [step / 100.0 for step in range(33)], "step_indices": list(range(33)),
            "linear_amplitude": [unresolved("No bound saved prediction", "MISSING") for _ in range(33)],
            "cfd_amplitude": [known(0.0) for _ in range(33)],
            "growth_rate": {"linear": known(0.0), "rk3": known(0.0), "cfd": known(0.5)},
            "error": {"absolute_discrepancy": known(0.5), "relative_discrepancy": known(0.5),
                      "definition_id": "fig13.relative-discrepancy-CFD-RK3", "evidence_refs": ["mock.evidence"]}}
