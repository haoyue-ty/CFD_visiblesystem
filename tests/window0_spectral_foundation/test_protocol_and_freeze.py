import hashlib
import inspect
import json
from copy import deepcopy
from pathlib import Path
from typing import get_type_hints

import pytest
from pydantic import ValidationError

from backend.adapters.spectral import SpectralAdapterProtocol
from backend.models import CORE_MODELS, ResourceSlot, known
from backend.models.spectral import Eigenmode, GrowthValidation, SpectrumDataset, SpectralPoint, SpectralPoints


ROOT = Path(__file__).resolve().parents[2]


def test_phase4_contract_hashes_and_phase5_phase6_freeze():
    manifest = json.loads((ROOT / "docs/PHASE4_FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    for item in manifest["documents"]:
        # Freeze files record Windows paths; resolve the controlled basename under docs.
        path = ROOT / "docs" / item["path"].replace("\\", "/").rsplit("/", 1)[-1]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"].lower()
    phase5 = json.loads((ROOT / "docs/PHASE5_CASE8_FREEZE.json").read_text(encoding="utf-8"))
    assert phase5["PHASE5_CASE8_STATUS"] == "FROZEN_ACCEPTED"
    phase5_manifest = json.loads((ROOT / "docs/PHASE5_CASE8_FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    freeze = phase5_manifest["freeze_record"]
    assert hashlib.sha256((ROOT / freeze["path"]).read_bytes()).hexdigest() == freeze["sha256"]
    phase5_report = (ROOT / "docs/handoffs/phase5/PHASE5_CASE8_INTEGRATION_AUDIT.md").read_text(encoding="utf-8")
    assert "PHASE5_CASE8_INTEGRATION=PASS" in phase5_report
    phase6 = (ROOT / "docs/handoffs/phase6/PHASE6_ALLOCATION_FREEZE.md").read_text(encoding="utf-8")
    phase6_report = (ROOT / "docs/handoffs/phase6/PHASE6_ALLOCATION_INTEGRATION_AUDIT.md").read_text(encoding="utf-8")
    assert "PHASE6_ALLOCATION_STATUS=FROZEN_ACCEPTED" in phase6
    assert "PHASE6_ALLOCATION_INTEGRATION=PASS" in phase6 and "PHASE6_ALLOCATION_INTEGRATION=PASS" in phase6_report


def test_protocol_five_operations_and_revision_pinning():
    methods = {name: method for name, method in vars(SpectralAdapterProtocol).items() if not name.startswith("_")}
    assert set(methods) == {"list_spectral_datasets", "describe_spectrum", "load_spectral_points",
                            "load_eigenmode", "load_growth_validation"}
    for method in methods.values():
        signature = inspect.signature(method)
        assert signature.parameters["registry_revision"].kind == inspect.Parameter.KEYWORD_ONLY
        assert not ({"path", "file", "member", "q_at", "time", "formula"} & set(signature.parameters))
        assert "return" in get_type_hints(method)
    assert get_type_hints(methods["load_spectral_points"])["return"] == ResourceSlot[SpectralPoints]


def test_internal_models_not_in_public_schema_catalog():
    assert not ({SpectrumDataset, SpectralPoint, SpectralPoints, Eigenmode, GrowthValidation} & set(CORE_MODELS))
    # A negative HTTP delivery assertion would construct the app; this window
    # instead checks the existing registration source without activating readers.
    for directory in ("backend/api", "backend/schemas", "backend/core"):
        for path in (ROOT / directory).glob("*.py"):
            assert "models.spectral" not in path.read_text(encoding="utf-8")
            assert "adapters.spectral" not in path.read_text(encoding="utf-8")


def test_missing_slot_cannot_contain_numeric_value():
    error = {"domain": "SCIENTIFIC", "code": "MISSING_SCIENTIFIC_ASSET", "message": "No saved validation",
             "target": {"resource_type": "growth_validation", "identity": known("missing.test")},
             "retryable": False, "details": [], "evidence_refs": ["mock.evidence"]}
    slot = ResourceSlot[GrowthValidation].model_validate({"availability": "MISSING", "error": error})
    assert "value" not in slot.model_dump()
    with pytest.raises(ValidationError):
        ResourceSlot[GrowthValidation].model_validate({"availability": "MISSING", "error": error, "value": 0.0})


def curve_payload(point_payload):
    points = []
    for mode in range(17):
        point = deepcopy(point_payload)
        point["mode_index"] = mode
        point["spectrum_record_id"] = f"mock.spectrum.point.{mode}"
        point["result"]["result_id"] = point["spectrum_record_id"]
        points.append(point)
    return {key: point_payload[key] for key in ("dataset_id", "collection_id", "base_result_id", "configuration_id", "parameter_value")} | {"points": points}


def test_complete_curve(point_payload):
    value = SpectralPoints.model_validate(curve_payload(point_payload))
    assert len(value.points) == 17


@pytest.mark.parametrize("kind", ["missing_mode", "duplicate_mode", "base", "q", "dataset", "revision"])
def test_curve_rejects_partial_or_mixed_science(kind, point_payload):
    payload = curve_payload(point_payload)
    point = payload["points"][0]
    if kind == "missing_mode":
        payload["points"].pop()
    elif kind == "duplicate_mode":
        point["mode_index"] = 1
    elif kind == "base":
        point["base_result_id"] = "another.base"
    elif kind == "q":
        point["parameter_value"] = 0.264
        point["evidence"]["configuration"]["parameters"][0]["value"] = known(0.264)
    elif kind == "dataset":
        point["dataset_id"] = "another.dataset"
    else:
        point["provenance"]["data_revision"] = "another.revision"
        point["result"]["provenance"] = deepcopy(point["provenance"])
    with pytest.raises(ValidationError):
        SpectralPoints.model_validate(payload)


@pytest.mark.parametrize("mode", [1, 4, 8, 12])
@pytest.mark.parametrize("q", [0.0, 0.396])
@pytest.mark.parametrize("epsilon", [1e-4, 1e-5, 1e-6])
def test_exact_24_validation_combinations(mode, q, epsilon, growth_payload):
    growth_payload.update(mode_index=mode, parameter_value=q, epsilon=epsilon)
    parameters = growth_payload["evidence"]["configuration"]["parameters"]
    parameters[0]["value"] = known(q)
    parameters[1]["value"] = known(mode)
    parameters[2]["value"] = known(epsilon)
    assert GrowthValidation.model_validate(growth_payload).mode_index == mode


def test_saved_left_rank31_is_not_fourier_mode31(eigenmode_payload):
    eigenmode_payload.update(side="LEFT", rank=31)
    value = Eigenmode.model_validate(eigenmode_payload)
    assert value.mode_index == 8 and value.rank == 31
