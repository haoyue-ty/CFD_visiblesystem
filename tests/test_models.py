import copy
import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.models import (CORE_MODELS, ApiEnvelope, ArrayDescriptor,
                            Fact, HashFact, Metric, Number, PageWindow,
                            PositiveInt, ResourceSlot, ScientificArray, ScientificResult,
                            TimeSpec, Verification, known, unresolved)


@pytest.mark.parametrize("payload", [
    {"state": "UNKNOWN", "reason": "missing", "value": 0},
    {"state": "KNOWN"}, {"state": "KNOWN", "value": None},
    {"state": "KNOWN", "value": "0"}, {"state": "KNOWN", "value": True},
    {"state": "KNOWN", "value": float("nan")},
    {"state": "KNOWN", "value": float("inf")}, {"state": "UNKNOWN", "reason": ""},
])
def test_facts_reject_invalid_variants(payload):
    with pytest.raises(ValidationError):
        Fact[Number].model_validate(payload)


def test_zero_is_known_not_missing():
    assert Fact[Number].model_validate(known(0)).model_dump() == known(0.0)
    assert Fact[Number].model_validate(unresolved("No fact", "MISSING")).model_dump()["state"] == "MISSING"


@pytest.mark.parametrize("value", ["A" * 64, "a" * 63, "x" * 64])
def test_hash_validation(value):
    with pytest.raises(ValidationError):
        HashFact.model_validate(known(value))


def test_hash_accepts_lowercase_sha256():
    HashFact.model_validate(known("a" * 64))


@pytest.mark.parametrize("index", [0, -1, True, "1"])
def test_snapshot_zero_and_coercion_are_rejected(index):
    with pytest.raises(ValidationError):
        Fact[PositiveInt].model_validate(known(index))


def test_stage_bool_and_out_of_range_rejected(result_payload):
    for value in (True, -1, 3, "1"):
        payload = copy.deepcopy(result_payload["time"])
        payload["stage_index"] = known(value)
        with pytest.raises(ValidationError):
            TimeSpec.model_validate(payload)


def test_timestamp_timezone_required(result_payload):
    payload = copy.deepcopy(result_payload["verification"])
    payload["verified_at"] = known(datetime(2026, 1, 1))
    with pytest.raises(ValidationError):
        Verification.model_validate(payload)


def descriptor(dtype="float64", shape=None):
    return {"array_id": "mock.array", "dtype": dtype, "shape": shape if shape is not None else [2],
            "order": "C", "axes": [] if shape == [] else ["x"], "encoding": "FLAT_JSON", "element_count": 1 if shape == [] else 2}


@pytest.mark.parametrize("dtype,values", [("int64", [1.5, 2]), ("bool", [0, 1]), ("float64", [True, 0]),
                                         ("complex128", [1, 2]), ("float64", [float("inf"), 0]), ("int64", ["1", 2])])
def test_dtype_is_strict(result_payload, dtype, values):
    with pytest.raises(ValidationError):
        ScientificArray.model_validate({"result": result_payload, "descriptor": descriptor(dtype), "values": values})


@pytest.mark.parametrize("dtype,values", [("int64", [1, 2]), ("float64", [1.2, 2.3]), ("bool", [True, False]),
                                         ("complex128", [{"real": 1.0, "imag": 0.0}, {"real": 0.0, "imag": 2.0}])])
def test_array_roundtrip(result_payload, dtype, values):
    array = ScientificArray.model_validate({"result": result_payload, "descriptor": descriptor(dtype), "values": values})
    assert ScientificArray.model_validate_json(array.model_dump_json()) == array


def test_shape_and_flat_length_rejected(result_payload):
    payload = descriptor()
    payload["element_count"] = 3
    with pytest.raises(ValidationError):
        ArrayDescriptor.model_validate(payload)
    with pytest.raises(ValidationError):
        ScientificArray.model_validate({"result": result_payload, "descriptor": descriptor(), "values": [0.0]})
    ScientificArray.model_validate({"result": result_payload, "descriptor": descriptor(shape=[]), "values": [0.0]})


def test_mock_cannot_claim_verified(result_payload):
    result_payload["verification"]["status"] = "FROZEN_VERIFIED"
    with pytest.raises(ValidationError):
        ScientificResult.model_validate(result_payload)


def test_scientific_evidence_required(result_payload):
    result_payload["provenance"]["evidence_refs"] = []
    with pytest.raises(ValidationError):
        ScientificResult.model_validate(result_payload)


def test_metric_time_cannot_disagree(result_payload):
    time = copy.deepcopy(result_payload["time"])
    time["physical_time"] = known(1.0)
    with pytest.raises(ValidationError):
        Metric.model_validate({"result": result_payload, "metric_id": "mock.metric", "value": known(1.0),
                               "definition_id": "mock.definition", "detector": unresolved("No detector"),
                               "time_scope": time, "display_label": "Test", "resolution_limit": unresolved("No limit")})


def test_slots_have_no_zero_fill():
    with pytest.raises(ValidationError):
        ResourceSlot[Number].model_validate({"availability": "MISSING", "value": 0})
    with pytest.raises(ValidationError):
        ResourceSlot[Number].model_validate({"availability": "PARTIAL", "value": 0, "issues": []})


def test_envelope_requires_data_and_valid_issues():
    header = {"schema_version": "1.0.0", "request_id": "test", "registry_revision": unresolved("Not loaded"),
              "data_revision": unresolved("Not loaded")}
    for extra in ({"availability": "AVAILABLE", "issues": []},
                  {"availability": "PARTIAL", "data": 0, "issues": []},
                  {"availability": "MISSING", "data": 0, "issues": []}):
        with pytest.raises(ValidationError):
            ApiEnvelope[Number].model_validate({**header, **extra})


def test_pagination_preserves_total():
    PageWindow(offset=5, limit=10, returned_count=0, total_count=2, has_more=False)
    with pytest.raises(ValidationError):
        PageWindow(offset=0, limit=2, returned_count=2, total_count=5, has_more=False)


def test_public_models_forbid_absolute_locators():
    from backend.models import SourceAsset
    assert "absolute_source_path" not in SourceAsset.model_fields
    assert SourceAsset.model_config["extra"] == "forbid"


def test_all_slice_models_export_serialization_schemas():
    for model in CORE_MODELS:
        assert model.model_json_schema(mode="serialization")


def test_frozen_subset_has_canonical_exports():
    import backend.models as models
    from pathlib import Path
    freeze = json.loads(Path("docs/PHASE4_TECHNICAL_FOUNDATION_FREEZE.json").read_text(encoding="utf-8"))
    assert all(hasattr(models, name) for name in freeze["case8_schema_subset"])
    for excluded in ("GateRegistry", "SpectrumDataset", "CylinderAllocationOverview", "AccountUser", "CrossFlowComparison"):
        assert not hasattr(models, excluded)
