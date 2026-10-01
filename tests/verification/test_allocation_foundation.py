"""Scientific category errors for Phase 6A; fixtures are explicitly MOCK."""
from copy import deepcopy
from inspect import signature

import pytest
from pydantic import ValidationError

from backend.adapters.allocation import AllocationAdapterProtocol
from backend.models import known, unresolved
from backend.models.allocation import AllocationResult, WIRE_REPRESENTATION
from backend.services.allocation import AllocationService


@pytest.fixture
def allocation_payload(result_payload):
    def build(kind):
        header = deepcopy(result_payload)
        face = kind == "FACE_FIELD"
        header.update(experiment_id="case8" if face else "gate",
                      config_id="D_u" if face else "Acoustic",
                      semantic_id="Case8_face_Pi_at_integrated" if face else "Gate_cell_Pi_at_integrated")
        na = unresolved("No playback dimension", "NOT_APPLICABLE")
        header["time"].update(sampling="TERMINAL" if face else "STATIC",
                              accumulation="TRAJECTORY_INTEGRATED", physical_time=known(0.08),
                              interval=known({"start": 0.0, "end": 0.08}),
                              step_index=known(1912), stage_index=na, snapshot_index=na)
        header["unit"].update(quantity="integrated_entropy", label="model integrated entropy")
        mask_id = "mock.face-mask" if face else "mock.cell-mask"
        header["scope"]["mask_refs"] = [mask_id]
        measure = {"id": "mock.face-measure" if face else "mock.cell-measure",
                   "description": "Test-only integrated measure",
                   "integral_rule": "dy*sum(x)+dx*sum(y)" if face else "sum(cells)",
                   "measure_parameters": [], "includes_time_weights": True,
                   "includes_spatial_measure": not face}
        error = {"domain": "SCIENTIFIC", "code": "MISSING_SCIENTIFIC_ASSET",
                 "message": "Test-only missing metric", "target": {"resource_type": "metric", "identity": na},
                 "retryable": False, "details": [], "evidence_refs": ["mock.evidence"]}
        missing = {"availability": "MISSING", "error": error}
        summary = {"total_budget": deepcopy(missing), "inside": deepcopy(missing),
                   "outside": deepcopy(missing), "fraction_format": "FRACTION",
                   "mask_refs": [mask_id], "measure": measure,
                   "spatial_cumulative_curve": deepcopy(missing), "evidence_refs": ["mock.evidence"]}
        locations = [("CARTESIAN_X_FACE", [32, 129]), ("CARTESIAN_Y_FACE", [32, 128])] if face else [
            ("CARTESIAN_CELL", [32, 128])]
        fields = []
        for location, shape in locations:
            field_id = f"mock.{location}"
            axes = [{"name": axis, "size": size, "coordinate_values": unresolved("Fixture geometry"),
                     "coordinate_array_ref": unresolved("Fixture geometry"), "unit": header["unit"]}
                    for axis, size in zip(["y", "x"], shape)]
            domain = {"id": field_id, "coordinate_system": "CARTESIAN", "location_type": location,
                      "shape": shape, "axes": axes, "extent": [], "measure_convention": deepcopy(measure),
                      "boundary_scope": header["scope"]["boundary_scope"], "geometry_ref": na,
                      "evidence_refs": ["mock.evidence"]}
            fields.append({"field_id": field_id, "label": "Mock cumulative allocation", "result": deepcopy(header),
                           "domain": domain, "array_ref": {"result_id": header["result_id"], "descriptor": {
                               "array_id": field_id, "dtype": "float64", "shape": shape, "order": "C",
                               "axes": ["y", "x"], "encoding": "FLAT_JSON", "element_count": shape[0]*shape[1]}},
                           "mask_refs": [mask_id]})
        return {"result": header, "representation_type": kind, "summary": summary, "fields": fields}
    return build


@pytest.mark.parametrize("kind", ["FACE_FIELD", "CELL_FIELD"])
def test_frozen_field_variants_roundtrip_without_new_wire_fields(allocation_payload, kind):
    result = AllocationResult.model_validate(allocation_payload(kind))
    assert AllocationResult.model_validate_json(result.model_dump_json()) == result
    assert set(result.model_dump()) == {"result", "representation_type", "fields", "summary"}
    assert '"values":' not in result.model_dump_json()
    assert result.root.summary.inside.root.availability == "MISSING"


@pytest.mark.parametrize("kind", ["FACE_FIELD", "CELL_FIELD"])
def test_time_or_measure_cannot_be_reinterpreted(allocation_payload, kind):
    for change in ("time", "measure", "weights"):
        payload = allocation_payload(kind)
        if change == "time":
            payload["result"]["time"]["accumulation"] = "NONE"
        else:
            key = "includes_spatial_measure" if change == "measure" else "includes_time_weights"
            payload["summary"]["measure"][key] = not payload["summary"]["measure"][key]
            for field in payload["fields"]:
                field["domain"]["measure_convention"][key] = payload["summary"]["measure"][key]
        with pytest.raises(ValidationError):
            AllocationResult.model_validate(payload)


def test_face_to_cell_projection_is_not_authoritative_allocation(allocation_payload):
    payload = allocation_payload("FACE_FIELD")
    payload["fields"] = payload["fields"][1:]
    payload["fields"][0]["domain"]["location_type"] = "CARTESIAN_CELL"
    with pytest.raises(ValidationError):
        AllocationResult.model_validate(payload)


def test_cumulative_face_map_cannot_be_relabelled_as_original_production(allocation_payload):
    payload = allocation_payload("FACE_FIELD")
    for header in [payload["result"], *(field["result"] for field in payload["fields"])]:
        header["data_origin"] = "FROZEN_PRODUCTION"
        header["verification"]["status"] = "FROZEN_VERIFIED"
        header["provenance"]["source_asset_ids"] = ["mock.asset"]
    with pytest.raises(ValidationError, match="DIAGNOSTIC_RERUN"):
        AllocationResult.model_validate(payload)


def test_summary_keeps_original_sampling_but_rejects_different_integral(allocation_payload):
    payload = allocation_payload("FACE_FIELD")
    header = deepcopy(payload["result"])
    header["semantic_id"] = "E_at_cumulative"
    header["time"]["sampling"] = "PER_STEP"
    metric = {"result": header, "metric_id": "mock.E_at", "value": known(0.0),
              "definition_id": "E_at_cumulative", "detector": unresolved("No detector", "NOT_APPLICABLE"),
              "time_scope": deepcopy(header["time"]), "display_label": "Test budget",
              "resolution_limit": unresolved("Test fixture")}
    payload["summary"]["total_budget"] = {"availability": "AVAILABLE", "value": metric}
    result = AllocationResult.model_validate(payload)
    assert result.root.summary.total_budget.root.value.time_scope.sampling == "PER_STEP"
    for time in (metric["result"]["time"], metric["time_scope"]):
        time["interval"] = known({"start": 0.0, "end": 0.04})
    with pytest.raises(ValidationError, match="integration intervals"):
        AllocationResult.model_validate(payload)


@pytest.mark.parametrize("bad", ["config", "time", "revision", "mask"])
def test_field_context_cannot_be_mixed(allocation_payload, bad):
    payload = allocation_payload("CELL_FIELD")
    field = payload["fields"][0]
    if bad == "config":
        field["result"]["config_id"] = "Pressure"
    elif bad == "time":
        field["result"]["time"]["sampling"] = "MULTI_SNAPSHOT"
    elif bad == "revision":
        field["result"]["provenance"]["data_revision"] = "mock.other-data"
    else:
        field["mask_refs"] = ["mock.other-mask"]
    with pytest.raises(ValidationError):
        AllocationResult.model_validate(payload)


def test_heatmap_and_deferred_cylinder_are_not_field_discriminators(allocation_payload):
    for kind in ("heatmap", "ANGULAR_SECTOR", "ANGULAR_SECTORS", "REGION_SCALAR"):
        payload = allocation_payload("CELL_FIELD")
        payload["representation_type"] = kind
        with pytest.raises(ValidationError):
            AllocationResult.model_validate(payload)
    assert WIRE_REPRESENTATION["ANGULAR_SECTOR"] == "ANGULAR_SECTORS"


def test_service_and_optional_adapter_share_all_five_revision_pinned_methods():
    for name in ("describe_allocation", "load_allocation_metadata", "load_allocation_array",
                 "load_mask", "load_summary_metrics"):
        assert signature(getattr(AllocationService, name)) == signature(getattr(AllocationAdapterProtocol, name))
        assert "registry_revision" in signature(getattr(AllocationService, name)).parameters
    with pytest.raises(TypeError):
        AllocationService()


def test_existing_adapter_remains_a_valid_case8_adapter():
    from backend.adapters import Case8Adapter, Case8AdapterProtocol
    adapter = Case8Adapter()
    assert isinstance(adapter, Case8AdapterProtocol)
    assert not isinstance(adapter, AllocationAdapterProtocol)
