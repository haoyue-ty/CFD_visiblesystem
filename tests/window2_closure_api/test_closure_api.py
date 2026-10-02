"""CLO01–05 HTTP acceptance against all five real frozen runs, read-only."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

from backend import create_app
from backend.adapters.entropy_closure import EntropyClosureAdapter
from backend.core.errors import system_error
from backend.models import ApiEnvelope, FailedEnvelope
from backend.models.closure import ClosureHistory, ClosureRunRegistry, EntropyClosureRun, RefinementSummary
from backend.registry import closure_registry as R
from backend.schemas.openapi import export_openapi
from backend.schemas.requests import ClosureHistoryQuery, HistoryQuery
from backend.services.closure_resources import EVIDENCE_IDS, RESULT_IDS

BASE = "/api/v1/experiments/entropy-closure"
PATHS = {
    "CLO01": f"{BASE}/runs", "CLO02": f"{BASE}/runs/{{run_id}}",
    "CLO03": f"{BASE}/runs/{{run_id}}/stage-history", "CLO04": f"{BASE}/runs/{{run_id}}/step-history",
    "CLO05": f"{BASE}/refinement",
}
MODELS = dict(zip(PATHS, (ClosureRunRegistry, EntropyClosureRun, ClosureHistory, ClosureHistory, RefinementSummary)))


@pytest.fixture(scope="module")
def app():
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def read(client, path, model=None):
    response = client.get(path)
    assert response.status_code == 200, response.json
    if model:
        ApiEnvelope[model].model_validate_json(response.data)
    assert response.json["availability"] == "AVAILABLE"
    assert response.json["issues"] == []
    return response.json["data"]


def failure(client, path, status, code):
    response = client.get(path)
    assert response.status_code == status, response.json
    body = FailedEnvelope.model_validate_json(response.data)
    assert body.error.code == code
    assert "data" not in response.json
    assert "D:/Paper" not in response.text and "D:\\Paper" not in response.text
    return body


@pytest.fixture(scope="module")
def registry(client):
    return read(client, PATHS["CLO01"], ClosureRunRegistry)


def test_clo01_exactly_five_complete_frozen_runs(registry):
    assert tuple(run["run_id"] for run in registry["runs"]) == R.RUN_IDS
    assert registry["experiment_id"] == "entropy-closure"
    assert len(registry["runs"]) == 5
    assert sum(run["stage_point_count"] for run in registry["runs"]) == 196677
    assert sum(run["step_point_count"] for run in registry["runs"]) == 65559


@pytest.mark.parametrize("run_id", R.RUN_IDS)
def test_clo02_all_five_identity_cfl_terminal_and_zero_channel(client, registry, run_id):
    run = read(client, f"{BASE}/runs/{run_id}", EntropyClosureRun)
    assert run == next(item for item in registry["runs"] if item["run_id"] == run_id)
    assert run["config"]["id"] == run_id
    assert {p["name"]: p["value"]["value"] for p in run["config"]["parameters"]} == {
        key: R.RUNS[run_id][key] for key in ("CFL", "q_aa", "q_at")}
    raw = json.loads((Path(R.SCIENTIFIC_ROOT) / R.run_path(run_id, "run_summary.json")).read_text())
    assert {m["value"]["metric_id"]: m["value"]["value"]["value"] for m in run["terminal_summary"]} == {
        field: raw[field] for field in R.TERMINAL_FIELDS}
    assert all(ref in RESULT_IDS for ref in run["stage_series_refs"] + run["step_series_refs"])
    assert run["evidence_refs"] == run["config"]["evidence_refs"] == [R.evidence_id(run_id, "run")]
    assert all(m["value"]["result"]["provenance"]["evidence_refs"] == run["evidence_refs"] for m in run["terminal_summary"])


@pytest.fixture(scope="module")
def source_rows():
    cache = {}
    def load(run_id, group):
        key = run_id, group
        if key not in cache:
            with (Path(R.SCIENTIFIC_ROOT) / R.run_path(run_id, f"{group}_closure.csv")).open(newline="") as stream:
                cache[key] = list(csv.DictReader(stream))
        return cache[key]
    return load


@pytest.mark.parametrize("run_id", R.RUN_IDS)
@pytest.mark.parametrize("group,granularity,columns", [("stage", "PER_STAGE", R.STAGE_SERIES), ("step", "PER_STEP", R.STEP_SERIES)])
def test_clo03_clo04_saved_rows_source_clock_stage_indices_and_totals(client, source_rows, run_id, group, granularity, columns):
    rows = source_rows(run_id, group)
    step_rows = source_rows(run_id, "step")
    count = R.RUNS[run_id][f"{group}_rows"]
    assert len(rows) == count
    # First, stage-boundary crossing, middle, terminal, and empty pages.
    for offset in (0, 2, count // 2, count - 4, count, count + 5):
        history = read(client, f"{BASE}/runs/{run_id}/{group}-history?offset={offset}&limit=4", ClosureHistory)
        assert history["run_id"] == run_id and history["granularity"] == granularity
        assert history["evidence_refs"] == [R.evidence_id(run_id, group)]
        assert [s["series_id"] for s in history["series"]] == list(columns)
        for series in history["series"]:
            assert series["total_point_count"] == series["page"]["total_count"] == count
            expected = rows[offset:offset + 4]
            assert series["page"] == {"offset": offset, "limit": 4, "returned_count": len(expected),
                                       "total_count": count, "has_more": offset + len(expected) < count}
            assert series["result"]["time"]["sampling"] == granularity
            assert series["result"]["config_id"] == run_id
            assert series["result"]["provenance"]["evidence_refs"] == series["result"]["verification"]["evidence_refs"] == history["evidence_refs"]
            assert series["source_column"] == series["series_id"]
            for point, row, ordinal in zip(series["points"], expected, range(offset, offset + len(expected))):
                assert point["point_index"] == ordinal
                assert point["value"]["value"] == float(row[series["series_id"]])
                assert point["step_index"]["value"] == point["source_step_index"]["value"] == int(row["step"])
                endpoint = step_rows[int(row["step"]) - 1]
                assert point["interval"]["value"] == {"start": float(endpoint["time_n"]), "end": float(endpoint["time_np1"])}
                assert point["physical_time"]["value"] == float(row["t_stage_or_step_time" if group == "stage" else "time_np1"])
                if group == "stage":
                    assert point["source_stage_index"]["value"] == int(row["stage"])
                    assert point["stage_index"]["value"] == int(row["stage"]) - 1
                    assert point["physical_time"]["value"] == float(endpoint["time_n"])
                elif "_stage" in series["series_id"]:
                    assert point["source_stage_index"]["value"] == int(series["series_id"][-1])
                    assert point["stage_index"]["value"] == int(series["series_id"][-1]) - 1
                else:
                    assert point["stage_index"]["state"] == point["source_stage_index"]["state"] == "NOT_APPLICABLE"
            if group == "step":
                assert series["aggregation"] == ("CUMULATIVE" if series["series_id"] == "R_time_cumulative" else
                                                  "STEP_INCREMENT" if series["series_id"].startswith("E_") or series["series_id"] in ("DeltaS", "R_time_step") else "NONE")


def test_default_history_query_uses_existing_bounds_and_complete_series(client):
    for field in ("offset", "limit"):
        assert ClosureHistoryQuery.model_fields[field].default == HistoryQuery.model_fields[field].default
        assert ClosureHistoryQuery.model_fields[field].metadata == HistoryQuery.model_fields[field].metadata
    for group, columns in (("stage", R.STAGE_SERIES), ("step", R.STEP_SERIES)):
        data = read(client, f"{BASE}/runs/{R.RUN_IDS[0]}/{group}-history")
        assert [s["series_id"] for s in data["series"]] == list(columns)
        assert all(len(s["points"]) == 2000 and s["page"]["has_more"] for s in data["series"])


def test_clo05_four_du_recorded_refinement_points_existing_slopes(client):
    summary = read(client, PATHS["CLO05"], RefinementSummary)
    assert summary["run_ids"] == list(R.RUN_IDS[:4])
    assert summary["evidence_refs"] == [R.REFINEMENT_EVIDENCE]
    assert len(summary["metrics_by_run"]) == 4
    for item in summary["metrics_by_run"]:
        raw = R.RUNS[item["run_id"]]["terminal_summary"]
        metrics = {m["value"]["metric_id"]: m["value"] for m in item["metrics"]}
        assert metrics["R_total"]["value"]["value"] == raw["R_total"]
        assert metrics["dt_eff"]["value"]["value"] == raw["dt_eff"]
    slopes = [m["value"]["value"]["value"] for item in summary["metrics_by_run"] for m in item["metrics"]
              if m["value"]["metric_id"].startswith("pairwise_slope")]
    assert slopes == [row["slope"] for row in R.SOURCE_MAP["refinement"]["pairwise_slopes"]]
    assert summary["refinement_slope"]["value"]["value"]["value"] == R.SOURCE_MAP["refinement"]["global_slope"]
    assert "FULLY_DISCRETE_DIAGNOSTIC" in {lim["code"] for lim in summary["limitations"]}


@pytest.mark.parametrize("suffix", ["", "/stage-history", "/step-history"])
@pytest.mark.parametrize("run_id", ["B_u-cfl-0.1", "D_u-cfl-0.03", "B_u-cfl-0.2", "D_u-cfl-0.005"])
def test_recognized_invalid_combinations_are_422(client, suffix, run_id):
    body = failure(client, f"{BASE}/runs/{run_id}{suffix}", 422, "UNSUPPORTED_COMBINATION")
    assert body.error.domain == "SCIENTIFIC" and body.availability == "UNSUPPORTED"


@pytest.mark.parametrize("suffix", ["", "/stage-history", "/step-history"])
@pytest.mark.parametrize("run_id", ["random-run", "not-registered-123", "C_u-cfl-0.05"])
def test_random_ids_are_404(client, suffix, run_id):
    failure(client, f"{BASE}/runs/{run_id}{suffix}", 404, "INVALID_RESULT_ID")


@pytest.mark.parametrize("group", ["stage", "step"])
@pytest.mark.parametrize("query", ["series=G", "granularity=PER_STEP", "sampling=PER_STAGE", "stage=1", "stage_index=0",
                                  "step=1", "step_index=1", "CFL=0.1", "cfl=0.1", "config=B_u", "config_id=B_u",
                                  "run_id=B_u-cfl-0.05", "offset=-1", "offset=1.5", "limit=0", "limit=5001",
                                  "limit=two", "offset=0&offset=1", "limit=1&limit=2", "formula=G%2BD_total"])
def test_no_client_semantic_identity_or_pagination_override(client, group, query):
    failure(client, f"{BASE}/runs/{R.RUN_IDS[0]}/{group}-history?{query}", 400, "INVALID_REQUEST")


@pytest.mark.parametrize("suffix", ["spatial", "fields", "snapshots", "trajectory", "arbitrary-cfl", "run-new", "allocation", "spectrum"])
def test_no_spatial_or_unfrozen_routes(client, suffix):
    for prefix in (BASE, f"{BASE}/runs/{R.RUN_IDS[0]}"):
        failure(client, f"{prefix}/{suffix}", 404, "API_ROUTE_NOT_FOUND")


def test_real_registry_activation_tabs_and_unsupported_capabilities(client):
    system = read(client, "/api/v1/system")
    assert next(ref for ref in system["experiments"] if ref["experiment_id"] == "entropy-closure")["delivery_status"] == "IMPLEMENTED"
    experiment = read(client, BASE)
    assert experiment["delivery_status"] == "IMPLEMENTED"
    listing = read(client, "/api/v1/experiments")
    assert next(ref for ref in listing["items"] if ref["id"] == "entropy-closure") == experiment
    configs = read(client, f"{BASE}/configs")
    assert [config["id"] for config in configs["items"]] == list(R.RUN_IDS)
    caps = read(client, f"{BASE}/capabilities")["items"]
    assert caps == experiment["capabilities"]
    assert [c["tab_policy"]["tab_id"] for c in caps if c["tab_policy"]["visible_for_family"]] == [
        "overview", "semi-discrete", "fully-discrete", "evidence"]
    assert {c["task"]: c["status"] for c in caps} == {
        "overview": "SUPPORTED", "semi-discrete": "SUPPORTED", "fully-discrete": "SUPPORTED", "evidence": "SUPPORTED",
        "flow": "MISSING", "allocation": "UNSUPPORTED", "spectrum": "UNSUPPORTED"}
    for cap in caps:
        assert all(ref in RESULT_IDS for ref in cap["result_refs"])
        assert all(ref in EVIDENCE_IDS for ref in cap["evidence_refs"])
        assert cap["tab_policy"]["unsupported_deep_link_behavior"] == "EXPLAIN"
        for control in cap["controls"]:
            assert control["name"] == "run" and control["allowed_values"] == list(R.RUN_IDS)


@pytest.mark.parametrize("evidence_id", sorted(EVIDENCE_IDS))
def test_all_evidence_groups_and_result_provenance_resolve(client, evidence_id):
    record = read(client, f"/api/v1/evidence/{evidence_id}?registry_revision={R.REGISTRY_REVISION}")
    assert record["evidence_id"] == evidence_id and record["source_assets"] and record["definitions"]
    assert record["experiment_id"]["value"] == "entropy-closure"
    assert record["method_hash"]["value"] == R.METHOD_HASH
    assert record["freeze_reference"]["state"] == "KNOWN"
    assert all(ref in RESULT_IDS for ref in record["result_ids"])
    rid = record["result_ids"][0]
    provenance = read(client, f"/api/v1/results/{rid}/provenance?registry_revision={R.REGISTRY_REVISION}")
    assert provenance["result_id"] == rid
    assert provenance["provenance"]["registry_revision"] == R.REGISTRY_REVISION
    assert provenance["evidence_records"][0] == record
    failure(client, f"/api/v1/results/{rid}/arrays/guessed-spatial", 404, "INVALID_RESULT_ID")


@pytest.mark.parametrize("operation", PATHS)
def test_source_missing_is_typed_scientific_error(tmp_path, operation):
    client = create_app(closure_adapter=EntropyClosureAdapter(tmp_path)).test_client()
    body = failure(client, PATHS[operation].replace("{run_id}", R.RUN_IDS[0]), 404, "MISSING_SCIENTIFIC_ASSET")
    assert body.error.domain == "SCIENTIFIC" and body.availability == "MISSING"


def test_adapter_disabled_and_schema_mismatch_fail_closed(client, app, monkeypatch):
    disabled = create_app(closure_adapter=None).test_client()
    failure(disabled, PATHS["CLO01"], 503, "FEATURE_NOT_ENABLED")
    system = read(disabled, "/api/v1/system")
    assert next(ref for ref in system["experiments"] if ref["experiment_id"] == "entropy-closure")["delivery_status"] == "PLANNED"
    adapter = app.extensions["closure_service"].adapter
    monkeypatch.setattr(adapter, "load_stage_history", lambda run_id, **kw: adapter.load_step_history(run_id, limit=1))
    failure(client, f"{BASE}/runs/{R.RUN_IDS[0]}/stage-history?limit=1", 500, "CANONICAL_SCHEMA_MISMATCH")


@pytest.mark.parametrize("code,status", [("SOURCE_DATA_DRIFT", 409), ("SOURCE_CHANGED_DURING_READ", 409), ("SOURCE_READ_ERROR", 500)])
def test_typed_source_failures_are_documented(client, app, monkeypatch, code, status):
    def fail(*args, **kwargs):
        raise system_error(code, "Injected read failure", status=status)
    monkeypatch.setattr(app.extensions["closure_service"].adapter, "load_run", fail)
    body = failure(client, f"{BASE}/runs/{R.RUN_IDS[0]}", status, code)
    assert body.error.domain == "SCIENTIFIC"
    operation = next(o for o in app.extensions["operation_catalog"].operations if o.operation_id == "CLO02")
    assert code in operation.documented_errors[status]


def test_exact_five_openapi_operations_export_equality_and_wire_schema(app, client):
    document = export_openapi(app.extensions["operation_catalog"])
    validate(document)
    assert document["openapi"] == "3.1.0"
    assert document == client.get("/api/v1/openapi.json").json
    assert document == json.loads((R.ROOT / "config/openapi.json").read_text(encoding="utf-8"))
    actual = {entry["get"]["operationId"]: path for path, entry in document["paths"].items() if path.startswith(BASE)}
    assert actual == PATHS
    for operation, path in PATHS.items():
        entry = document["paths"][path]["get"]
        names = {p["name"] for p in entry["parameters"]}
        assert names == {"registry_revision"} | ({"run_id"} if "{run_id}" in path else set()) | (
            {"offset", "limit"} if operation in ("CLO03", "CLO04") else set())
        schema = entry["responses"]["200"]["content"]["application/json"]["schema"]
        schema = {**schema, "$defs": document["components"]["schemas"]}
        encoded = json.dumps(schema).replace("#/components/schemas/", "#/$defs/")
        response = client.get(path.replace("{run_id}", R.RUN_IDS[0]) + ("?limit=1" if operation in ("CLO03", "CLO04") else ""))
        assert response.status_code == 200
        Draft202012Validator(json.loads(encoded)).validate(response.json)
        ApiEnvelope[MODELS[operation]].model_validate_json(response.data)
    baseline = json.loads(subprocess.check_output(["git", "show", "5d6ceb4:config/openapi.json"]))
    assert all(document["components"]["schemas"].get(key) == value for key, value in baseline["components"]["schemas"].items())


def test_generated_types_are_repeatable_and_contain_exact_operations(tmp_path):
    generated = R.ROOT / "frontend/src/types/generated/api.d.ts"
    cli = R.ROOT / "frontend/node_modules/openapi-typescript/bin/cli.js"
    assert cli.is_file(), "Install locked frontend dependencies before contract acceptance"
    output = tmp_path / "api.d.ts"
    subprocess.run(["node", str(cli), str(R.ROOT / "config/openapi.json"), "-o", str(output)], check=True, capture_output=True)
    assert output.read_bytes() == generated.read_bytes()
    first = hashlib.sha256(output.read_bytes()).hexdigest()
    subprocess.run(["node", str(cli), str(R.ROOT / "config/openapi.json"), "-o", str(output)], check=True, capture_output=True)
    assert hashlib.sha256(output.read_bytes()).hexdigest() == first
    source = output.read_text(encoding="utf-8")
    for identity, path in PATHS.items():
        assert path in source and f"{identity}:" in source
    for name in ("ClosureRunRegistry", "EntropyClosureRun", "ClosureHistory", "RefinementSummary"):
        assert f"{name}:" in source


def test_scientific_sources_and_window1_adapter_bytes_preserved():
    before = json.loads((R.ROOT / "docs/handoffs/phase9/WINDOW1_SOURCE_BEFORE.json").read_text())
    assert all(Path(path).stat().st_size == item["size_bytes"] and hashlib.sha256(Path(path).read_bytes()).hexdigest() == item["sha256"]
               for path, item in before.items())
    name = "backend/adapters/entropy_closure.py"
    accepted = subprocess.check_output(["git", "show", f"31341e7:{name}"]).decode()
    # Phase11 only removes the invented composite evidence hash. All scientific
    # parsing, numeric outputs, arithmetic checks and freeze bindings stay exact.
    accepted = accepted.replace(
        '        data_inputs = sorted((asset["asset_id"], asset["sha256"]) for path, asset in R.ASSETS.items() if path in deps and path not in R.IMPORTED_METHODS)\n'
        '        digest = hashlib.sha256(json.dumps(data_inputs, separators=(",", ":")).encode()).hexdigest()\n', '')
    accepted = accepted.replace('"data_hash": known(digest)',
        '"data_hash": unresolved("No authoritative composite data hash recorded")')
    assert (R.ROOT / name).read_text() == accepted
    for name in ("backend/registry/closure_registry.py", "backend/models/closure.py",
                 "data/closure/source_manifest.json", "docs/handoffs/phase9/PHASE9_CLOSURE_SOURCE_MAP.json"):
        assert (R.ROOT / name).read_bytes() == subprocess.check_output(["git", "show", f"31341e7:{name}"])
    assert not [name for name in sys.modules if name == "solver" or name.startswith("solver.")]
