"""Window 2 real-source contract acceptance, with software-only fault injection."""
import csv
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate
from pydantic import ValidationError

from backend import create_app
from backend.core.errors import system_error
from backend.models import ApiEnvelope, ScientificArray, known
from backend.models.crossflow import CrossFlowComparison
from backend.registry import cylinder_registry as R
from backend.schemas.openapi import export_openapi
from backend.services.cylinder_resources import RESULT_IDS

BASE = "/api/v1/experiments/cylinder/configs"
CMP = "/api/v1/comparisons/case8-cylinder"
PATHS = {
    "CYL01": "/snapshots", "CYL02": "/snapshots/{snapshot_index}",
    "CYL03": "/snapshots/{snapshot_index}/fields/{field_id}", "CYL04": "/entropy-history",
    "CYL05": "/scalar-series/{series_id}", "CYL06": "/allocation",
    "CYL07": "/allocation/sectors", "CYL08": "/allocation/front-band", "CYL09": "/metrics",
}
EXAMPLES = {key: value.replace("{snapshot_index}", "1").replace("{field_id}", "radial_interior_pi_at")
            .replace("{series_id}", "E_at_cumulative") for key, value in PATHS.items()}


@pytest.fixture(scope="module")
def app():
    assert Path(R.SCIENTIFIC_ROOT).is_dir(), "Real scientific source is required"
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def read(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.json
    return response.json


@pytest.fixture(scope="module")
def comparison(client):
    return read(client, CMP)


def test_exact_frozen_operations_openapi_and_generated_contract(app, client):
    document = export_openapi(app.extensions["operation_catalog"])
    validate(document)
    assert document["openapi"] == "3.1.0"
    expected = {f"{BASE}/{{config_id}}{suffix}": operation for operation, suffix in PATHS.items()}
    actual = {p: v["get"]["operationId"] for p, v in document["paths"].items() if p.startswith(BASE)}
    assert actual == expected
    assert document["paths"][CMP]["get"]["operationId"] == "CMP01"
    assert document == read(client, "/api/v1/openapi.json")
    assert document == json.loads(Path("config/openapi.json").read_text(encoding="utf-8"))
    parameters = document["paths"][CMP]["get"]["parameters"]
    assert {p["name"] for p in parameters} == {"registry_revision", "case8_config", "cylinder_config"}
    assert {p["name"]: p["schema"]["default"] for p in parameters if "default" in p["schema"]} == {
        "case8_config": "D_u", "cylinder_config": "D_u", "registry_revision": None}
    generated = Path("frontend/src/types/generated/api.d.ts").read_text(encoding="utf-8")
    for path, operation in expected.items():
        assert path in generated and operation in generated
    assert CMP in generated and 'ranking_policy: "NO_UNIFIED_RANKING"' in generated
    baseline = json.loads(subprocess.check_output(["git", "show", "69a318b:config/openapi.json"]))
    for key, value in baseline["components"]["schemas"].items():
        current = document["components"]["schemas"][key]
        if key == "Verification":
            # The authorized Phase12 addition is the sole schema exception.
            assert set(current["properties"]) == set(value["properties"]) | {"canonical_status"}
            from typing import get_args
            from backend.models.core import CanonicalVerificationStatus
            assert current["properties"]["canonical_status"]["enum"] == list(get_args(CanonicalVerificationStatus))
            current = {**current, "properties": {k: v for k, v in current["properties"].items() if k != "canonical_status"}}
        assert current == value


@pytest.mark.parametrize("operation", PATHS)
@pytest.mark.parametrize("config,status,code", [("C_u", 422, "UNSUPPORTED_COMBINATION"), ("Z_u", 404, "UNKNOWN_CONFIG")])
def test_reject_config_consistently(client, operation, config, status, code):
    response = client.get(f"{BASE}/{config}{EXAMPLES[operation]}")
    assert response.status_code == status
    assert response.json["error"]["code"] == code


@pytest.mark.parametrize("config", R.CONFIGS)
def test_registered_configs_and_five_actual_snapshots(client, config):
    snapshots = read(client, f"{BASE}/{config}/snapshots")["data"]
    assert snapshots["snapshot_count"] == 5
    assert [s["snapshot_index"] for s in snapshots["items"]] == [1, 2, 3, 4, 5]
    assert [s["step_index"] for s in snapshots["items"]] == list(R.STEPS)
    assert [s["physical_time"] for s in snapshots["items"]] == [s["physical_time"] for s in R.MANIFEST["runs"][config]["snapshot_source"]]
    first = read(client, f"{BASE}/{config}/snapshots/1")["data"]
    assert first == snapshots["items"][0]
    assert first["step_index"] == first["physical_time"] == 0
    selected = read(client, f"{BASE}/{config}/snapshots/1?field=angular_interior_pi_at")["data"]
    assert [f["field_id"] for f in selected["fields"]] == ["angular_interior_pi_at"]
    configs = read(client, "/api/v1/experiments/cylinder/configs")["data"]
    assert [c["id"] for c in configs["items"]] == list(R.CONFIGS)
    capability = read(client, "/api/v1/experiments/cylinder/capabilities")["data"]
    assert next(c for c in capability["items"] if c["task"] == "cumulative-2d")["status"] == "MISSING"


@pytest.mark.parametrize("suffix", ["/snapshots/0", "/snapshots/-1", "/snapshots/0/fields/radial_interior_pi_at",
                                  "/snapshots/one", "/metrics?snapshot_index=0"])
def test_snapshot_invalid_syntax_is_400(client, suffix):
    response = client.get(f"{BASE}/D_u{suffix}")
    assert response.status_code == 400 and response.json["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("config", R.CONFIGS)
def test_history_all_9757_rows_exact_source_and_pagination(client, config):
    with (Path(R.SCIENTIFIC_ROOT) / R.run_path(config, "stage_weighted_history.csv")).open(encoding="utf-8", newline="") as stream:
        raw = list(csv.DictReader(stream))
    points = []
    for offset in (0, 5000):
        payload = read(client, f"{BASE}/{config}/entropy-history?series=E_at_cumulative&offset={offset}&limit=5000")["data"]
        series = payload["series"][0]
        assert series["total_point_count"] == series["page"]["total_count"] == 9757
        assert series["page"]["returned_count"] == len(series["points"])
        points.extend(series["points"])
    assert len(points) == len(raw) == 9757
    assert [p["value"]["value"] for p in points] == [float(r["E_at_int"]) for r in raw]
    assert [p["step_index"]["value"] for p in points] == list(range(1, 9758))
    assert points[0]["source_step_index"]["value"] == 0
    assert points[-1]["physical_time"]["value"] == 2
    empty = read(client, f"{BASE}/{config}/scalar-series/E_at_cumulative?offset=9757")["data"]
    assert empty["points"] == [] and empty["page"]["has_more"] is False
    assert empty["total_point_count"] == 9757


def test_history_default_and_repeated_stage_selection(client):
    default = read(client, f"{BASE}/D_u/entropy-history")["data"]["series"]
    assert len(default) == 4 and all(len(s["points"]) == 2000 for s in default)
    assert all(s["page"]["has_more"] for s in default)
    selected = read(client, f"{BASE}/D_u/entropy-history?series=E_bg_cumulative&series=E_at_cumulative&limit=1")["data"]
    assert [s["series_id"] for s in selected["series"]] == ["E_bg_cumulative", "E_at_cumulative"]


@pytest.mark.parametrize("config", R.CONFIGS)
def test_allocation_partial_and_frozen_representations(client, config):
    response = read(client, f"{BASE}/{config}/allocation")
    assert response["availability"] == "PARTIAL"
    overview = response["data"]
    assert overview["sectors"]["availability"] == overview["front_band"]["availability"] == "AVAILABLE"
    assert overview["cumulative_2d"]["availability"] == "MISSING"
    assert "value" not in overview["cumulative_2d"]
    assert "MISSING_SCIENTIFIC_ASSET" in {i["code"] for i in response["issues"]}
    sectors = read(client, f"{BASE}/{config}/allocation/sectors")["data"]
    band = read(client, f"{BASE}/{config}/allocation/front-band")["data"]
    assert sectors == overview["sectors"]["value"] and band == overview["front_band"]["value"]
    assert sectors["representation_type"] == "ANGULAR_SECTORS" and sectors["sector_count"] == 16
    assert band["representation_type"] == "REGION_SCALAR"
    assert band["result"]["time"]["accumulation"] == "TRAJECTORY_INTEGRATED"
    assert band["region_mask"]["type"] == "CYLINDER_FIXED_FRONT_BAND"
    if config == "D_u":
        assert band["fraction"]["value"] == pytest.approx(.00777687219301986, rel=1e-13)
    else:
        assert band["integrated_value"]["value"] == 0
        assert band["fraction"]["state"] == "NOT_APPLICABLE" and "value" not in band["fraction"]


@pytest.mark.parametrize("suffix", ["cumulative-map", "heatmap", "spatial-map"])
def test_no_cumulative_2d_endpoint(client, suffix):
    response = client.get(f"{BASE}/D_u/allocation/{suffix}")
    assert response.status_code == 404 and response.json["error"]["code"] == "API_ROUTE_NOT_FOUND"


@pytest.mark.parametrize("config", R.CONFIGS)
def test_array01_real_fields_geometry_bins_all_channels(client, config):
    field = read(client, f"{BASE}/{config}/snapshots/1/fields/radial_interior_pi_at")["data"]["field"]
    ref = field["array_ref"]
    path = f"/api/v1/results/{ref['result_id']}/arrays/{ref['descriptor']['array_id']}"
    response = client.get(path)
    value = ApiEnvelope[ScientificArray].model_validate_json(response.data).root.data
    assert response.status_code == 200 and value.descriptor.shape == [31, 128]
    with np.load(Path(R.SCIENTIFIC_ROOT) / R.run_path(config, "snapshots/native_faces_step_00000.npz"), allow_pickle=False) as raw:
        np.testing.assert_array_equal(value.values, raw["radial_interior_pi_at"].ravel(order="C"))
        rid = f"cylinder.{config}.snapshot.1.geometry.angular_interior_x_face"
        geometry = read(client, f"/api/v1/results/{rid}/arrays/angular_interior_x_face")["data"]
        np.testing.assert_array_equal(geometry["values"], raw["angular_interior_x_face"].ravel(order="C"))
    sectors = read(client, f"{BASE}/{config}/allocation/sectors")["data"]
    refs = [sectors["bin_edges"], *[a["array_ref"] for a in sectors["channel_arrays"]]]
    with np.load(Path(R.SCIENTIFIC_ROOT) / R.run_path(config, "spatial_cumulative.npz"), allow_pickle=False) as raw:
        for ref in refs:
            array_id = ref["descriptor"]["array_id"]
            payload = read(client, f"/api/v1/results/{ref['result_id']}/arrays/{array_id}")
            assert payload["registry_revision"]["value"] == R.REGISTRY_REVISION
            np.testing.assert_array_equal(payload["data"]["values"], raw["bins" if array_id == "bin_edges" else array_id])


def test_canonical_owner_dispatch_rejects_fabricated_identity_without_cylinder_read(app, client, monkeypatch):
    adapter = app.extensions["cylinder_service"].adapter
    calls = []
    original = adapter.load_array
    def spy(result, array):
        calls.append((result, array))
        return original(result, array)
    monkeypatch.setattr(adapter, "load_array", spy)
    rid = "cylinder.D_u.snapshot.1.angular_interior_pi_at"
    assert rid in RESULT_IDS
    read(client, f"/api/v1/results/{rid}/arrays/angular_interior_pi_at")
    assert calls == [(rid, "angular_interior_pi_at")]
    unknown = client.get("/api/v1/results/cylinder.D_u.snapshot.1.guessed-file/arrays/guessed-member")
    assert unknown.status_code == 404 and unknown.json["error"]["code"] == "INVALID_RESULT_ID"
    assert len(calls) == 1
    fake_map = client.get("/api/v1/results/cylinder.D_u.sectors/arrays/cumulative_2d")
    assert fake_map.status_code == 404


@pytest.mark.parametrize("config", R.CONFIGS)
def test_metrics_saved_values_original_detectors_and_floor(client, config):
    metrics = read(client, f"{BASE}/{config}/metrics")["data"]
    saved = json.loads((Path(R.SCIENTIFIC_ROOT) / R.run_path(config, "physical_metrics.json")).read_text(encoding="utf-8"))
    assert len(metrics["items"]) == 15
    for slot in metrics["items"]:
        metric = slot["value"]
        key, _, unit = R.METRICS[metric["metric_id"]]
        assert metric["value"]["value"] == saved[key]
        assert metric["result"]["unit"] == unit
        assert metric["detector"]["state"] == "KNOWN"
        if "width" in key and config in ("B_u", "D_u"):
            assert "DETECTOR_LIMITED_SHARPNESS_READING" in {l["code"] for l in metric["result"]["limitations"]}
    selected = read(client, f"{BASE}/{config}/metrics?metric_id=cylinder_front_HF_RMS&snapshot_index=5")["data"]
    assert len(selected["items"]) == 1
    assert client.get(f"{BASE}/{config}/metrics?snapshot_index=1").status_code == 422


@pytest.mark.parametrize("case8", ["A_u", "B_u", "C_u", "D_u"])
@pytest.mark.parametrize("cylinder", R.CONFIGS)
def test_comparison_registry_combinations_preserve_partial_sides(client, case8, cylinder):
    response = read(client, f"{CMP}?case8_config={case8}&cylinder_config={cylinder}")
    ApiEnvelope[CrossFlowComparison].model_validate_json(json.dumps(response))
    assert response["availability"] == "PARTIAL"
    data = response["data"]
    assert data["left"]["config_id"] == case8 and data["right"]["config_id"] == cylinder
    assert data["left"]["allocation"]["availability"] == ("AVAILABLE" if case8 == "D_u" else "MISSING")
    assert data["left"]["budget"]["availability"] == data["left"]["metrics"]["availability"] == "AVAILABLE"
    assert data["left"]["front_band"]["availability"] == "UNSUPPORTED"
    assert "value" not in data["left"]["front_band"]
    assert data["right"]["allocation"]["value"]["representation_type"] == "ANGULAR_SECTORS"
    assert data["right"]["front_band"]["value"]["representation_type"] == "REGION_SCALAR"


def test_comparison_default_semantics_explicit_rules_and_no_ranking(comparison):
    data = comparison["data"]
    assert data["comparison_id"] == "case8-cylinder.D_u.D_u"
    assert data["ranking_policy"] == "NO_UNIFIED_RANKING"
    assert set(data) == {"comparison_id", "left", "right", "comparability", "ranking_policy", "limitations", "evidence_refs"}
    assert data["left"]["protocol"]["final_time"]["value"] == .08
    assert data["right"]["protocol"]["final_time"]["value"] == 2
    assert data["left"]["allocation"]["value"]["result"]["data_origin"] == "DIAGNOSTIC_RERUN"
    assert data["right"]["allocation"]["value"]["result"]["scope"]["boundary_scope"]["value"].startswith("INTERIOR_ONLY")
    assert len(data["left"]["snapshot_refs"]) == 6 and len(data["right"]["snapshot_refs"]) == 5
    rules = data["comparability"]
    assert {(r["left_definition_id"], r["right_definition_id"]) for r in rules} == {
        ("Case8_face_window_fraction", "def.cylinder_front_band_fraction"),
        ("case8_front_high_k_energy", "def.cylinder_front_HF_RMS"),
        ("case8_width", "def.cylinder_front_mean_width"),
        ("E_at_cumulative", "def.Cylinder_E_at_cumulative")}
    assert all(r["status"] == "DESCRIPTIVE_ONLY" and r["reason"] and r["mapping_ref"]["state"] == "NOT_APPLICABLE" for r in rules)
    def check(node):
        if isinstance(node, dict):
            assert not set(node).intersection({"winner", "score", "best", "better", "rank", "stability_score", "localization_rank"})
            for child in node.values(): check(child)
        elif isinstance(node, list):
            for child in node: check(child)
    check(data)
    assert "NO_CYLINDER_CUMULATIVE_2D" in {l["code"] for l in data["limitations"]} or any(
        "cumulative" in l["description"].lower() and "2d" in l["description"].lower() for l in data["limitations"])


def test_comparison_budget_projection_retains_child_value_and_provenance(app, comparison):
    for side, service in ((comparison["data"]["left"], app.extensions["case8_service"]),
                          (comparison["data"]["right"], app.extensions["cylinder_service"])):
        assert len(side["budget"]["value"]["items"]) == 3
        for slot in side["budget"]["value"]["items"]:
            metric = slot["value"]
            header = service.load_scalar_series("D_u", metric["metric_id"], limit=1)
            terminal = service.load_scalar_series("D_u", metric["metric_id"], offset=header.total_point_count-1, limit=1)
            assert metric["value"] == terminal.points[0].value.model_dump(mode="json")
            assert metric["result"] == terminal.result.model_dump(mode="json")
            assert metric["definition_id"] == terminal.definition_id


def test_comparison_evidence_closure_and_array_references(client, comparison):
    data = comparison["data"]
    assert set(data["evidence_refs"]) == set(data["left"]["evidence_refs"]) | set(data["right"]["evidence_refs"])
    assert "ev.missing.cylinder-cumulative2d" in data["evidence_refs"]
    assert "ev.case8.D_u.allocation" in data["evidence_refs"]
    for ref in data["evidence_refs"]:
        record = read(client, f"/api/v1/evidence/{ref}")["data"]
        assert record["evidence_id"] == ref
    # Composite emits references, with real Case8 native-face arrays still
    # reachable through the same canonical ARRAY01 owner dispatch.
    ref = data["left"]["allocation"]["value"]["fields"][0]["array_ref"]
    revision = data["left"]["allocation"]["value"]["fields"][0]["result"]["provenance"]["registry_revision"]
    result = read(client, f"/api/v1/results/{ref['result_id']}/arrays/{ref['descriptor']['array_id']}?registry_revision={revision}")["data"]
    assert result["descriptor"] == ref["descriptor"]


@pytest.mark.parametrize("query,status,code", [
    ("cylinder_config=C_u", 422, "UNSUPPORTED_COMBINATION"), ("case8_config=Z_u", 404, "UNKNOWN_CONFIG"),
    ("cylinder_config=Z_u", 404, "UNKNOWN_CONFIG"), ("q_at=.2", 400, "INVALID_REQUEST"),
    ("normalize=true", 400, "INVALID_REQUEST"), ("sort=front_band", 400, "INVALID_REQUEST"),
    ("winner=true", 400, "INVALID_REQUEST"), ("case8_config=A_u&case8_config=D_u", 400, "INVALID_REQUEST"),
    ("registry_revision=unknown", 409, "REVISION_UNAVAILABLE")])
def test_comparison_invalid_query_rejected(client, query, status, code):
    response = client.get(CMP + "?" + query)
    assert response.status_code == status and response.json["error"]["code"] == code


@pytest.mark.parametrize("query", ["q_at=.2", "time=1", "limit=5001", "limit=1&limit=2", "series=E_at_cumulative&config_id=A_u"])
def test_cylinder_invalid_query_rejected(client, query):
    assert client.get(f"{BASE}/D_u/entropy-history?{query}").status_code == 400


def test_local_missing_child_keeps_other_side_and_budget(app, client, monkeypatch):
    def missing(*args, **kwargs):
        raise system_error("MISSING_SCIENTIFIC_ASSET", "Test-only unavailable child", status=404,
                           availability="MISSING", evidence_refs=["ev.cylinder.D_u.metrics"])
    monkeypatch.setattr(app.extensions["cylinder_service"].adapter, "load_metrics", missing)
    response = read(client, CMP)
    assert response["availability"] == "PARTIAL"
    assert response["data"]["right"]["metrics"]["availability"] == "MISSING"
    assert response["data"]["right"]["budget"]["availability"] == "AVAILABLE"
    assert response["data"]["left"]["metrics"]["availability"] == "AVAILABLE"


def test_front_band_missing_keeps_independent_sectors(app, client, monkeypatch):
    def missing(*args):
        raise system_error("MISSING_SCIENTIFIC_ASSET", "Test-only absent front-band child", status=404,
                           availability="MISSING", evidence_refs=["ev.cylinder.D_u.front-band"])
    monkeypatch.setattr(app.extensions["cylinder_service"].adapter, "load_front_band", missing)
    data = read(client, CMP)["data"]
    assert data["right"]["front_band"]["availability"] == "MISSING"
    assert data["right"]["allocation"]["availability"] == "AVAILABLE"
    assert data["right"]["allocation"]["value"]["representation_type"] == "ANGULAR_SECTORS"


def test_partial_metric_collection_retains_available_metrics(app, client, monkeypatch):
    original = app.extensions["cylinder_service"].adapter.load_metrics
    def partial(*args, **kwargs):
        payload = original(*args, **kwargs).model_dump(mode="python")
        error = system_error("MISSING_SCIENTIFIC_ASSET", "Test-only unavailable individual metric", status=404,
                             availability="MISSING", evidence_refs=["ev.cylinder.D_u.metrics"])
        payload["items"][0] = {"availability": "MISSING", "error": error.body.model_dump(mode="python")}
        return payload
    monkeypatch.setattr(app.extensions["cylinder_service"].adapter, "load_metrics", partial)
    response = read(client, CMP)
    metrics = response["data"]["right"]["metrics"]
    assert metrics["availability"] == "PARTIAL"
    assert len(metrics["value"]["items"]) == 15
    assert metrics["value"]["items"][1]["availability"] == "AVAILABLE"
    assert any(i["message"] == "Test-only unavailable individual metric" for i in response["issues"])


def test_wrong_child_identity_is_server_schema_error(app, client, monkeypatch):
    original = app.extensions["cylinder_service"].adapter.load_metrics
    def wrong(*args, **kwargs):
        payload = original(*args, **kwargs).model_dump(mode="python")
        payload["config_id"] = "A_u"
        for slot in payload["items"]:
            slot["value"]["result"]["config_id"] = "A_u"
        return payload
    monkeypatch.setattr(app.extensions["cylinder_service"].adapter, "load_metrics", wrong)
    response = client.get(CMP)
    assert response.status_code == 500 and response.json["error"]["code"] == "CANONICAL_SCHEMA_MISMATCH"


def test_frozen_model_rejects_shared_ranking_and_side_swaps(comparison):
    data = comparison["data"]
    for extra in ("winner", "score", "rank"):
        with pytest.raises(ValidationError):
            CrossFlowComparison.model_validate({**data, extra: "D_u"})
    with pytest.raises(ValidationError):
        CrossFlowComparison.model_validate({**data, "left": data["right"], "right": data["left"]})


def test_responses_validate_against_actual_openapi(app, client, comparison):
    document = export_openapi(app.extensions["operation_catalog"])
    for operation in app.extensions["operation_catalog"].operations:
        if operation.operation_id not in PATHS and operation.operation_id != "CMP01":
            continue
        payload = comparison if operation.operation_id == "CMP01" else read(client, f"{BASE}/D_u{EXAMPLES[operation.operation_id]}")
        ref = document["paths"][operation.path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        Draft202012Validator({**ref, "components": document["components"]}).validate(payload)


def test_cylinder_revisions_match_registered_owner(client):
    response = read(client, f"{BASE}/D_u/allocation?registry_revision={R.REGISTRY_REVISION}")
    assert response["registry_revision"] == known(R.REGISTRY_REVISION)
    assert response["data_revision"] == known(R.DATA_REVISION)
    assert client.get(f"{BASE}/D_u/snapshots?registry_revision=wrong").status_code == 409
    assert client.get("/api/v1/results/cylinder.D_u.sectors/arrays/channel_at?registry_revision=wrong").status_code == 409
