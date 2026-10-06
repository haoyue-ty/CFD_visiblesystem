"""Window 2 contract tests for the Case8 slice API.

All requests go through Flask against the TEST-ONLY fake adapter. No scientific file is
opened, no CFD run is started, and every payload is MOCK.
"""
import re

import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

from backend.core.errors import DomainError
from backend.models import (ApiEnvelope, CapabilityList, ConfigList, EntropyHistory,
                            EvidenceRecord, Experiment, ExperimentList, FailedEnvelope,
                            FieldResponse, FieldSnapshot, MetricCollection, ProjectInfo,
                            ResultProvenance, ScalarSeries, ScientificArray, SnapshotAlignment,
                            SnapshotIndex)
from backend.schemas.openapi import export_openapi
from backend.schemas.requests import RegistryQuery
from fake_case8_adapter import HISTORY_POINTS

BASE = "/api/v1/experiments/case8/configs/D_u"


def envelope(response, model):
    """Parse a success envelope. `model` is the response T, not ApiEnvelope[T].

    Validating the raw body against ``ApiEnvelope[model]`` is what proves the wire shape
    matches the operation's declared response model in the catalog.
    """
    assert response.status_code == 200, response.text
    body = ApiEnvelope[model].model_validate_json(response.data)
    assert body.root.availability == "AVAILABLE"
    assert body.root.issues == []
    return body.root.data


def failure(response, status, code):
    assert response.status_code == status, response.text
    body = FailedEnvelope.model_validate_json(response.data)
    assert body.error.code == code
    assert "data" not in response.json
    assert "D:\\" not in response.text and "Paper" not in response.text
    return body


# --- SYS / REG ------------------------------------------------------------------

def test_sys01_unchanged_by_window2(client):
    envelope(client.get("/api/v1/system"), ProjectInfo)


def test_reg01_lists_six_experiments_without_values(client):
    data = envelope(client.get("/api/v1/experiments"), ExperimentList)
    assert [item.id for item in data.items] == [
        "case8", "gate", "entropy-closure", "spectrum", "modal-validation", "cylinder"]
    assert all(item.delivery_status == "PLANNED" for item in data.items)


def test_reg02_03_04_case8_are_served_from_the_adapter(client):
    experiment = envelope(client.get("/api/v1/experiments/case8"), Experiment)
    assert experiment.delivery_status == "IMPLEMENTED"
    configs = envelope(client.get("/api/v1/experiments/case8/configs"), ConfigList)
    assert [item.id for item in configs.items] == ["A_u", "B_u", "D_u"]
    capabilities = envelope(client.get("/api/v1/experiments/case8/capabilities"), CapabilityList)
    assert [item.task for item in capabilities.items] == ["FLOW"]


def test_reg02_unknown_experiment_is_404_and_planned_family_is_503(client):
    failure(client.get("/api/v1/experiments/gate-typo"), 404, "UNKNOWN_EXPERIMENT")
    failure(client.get("/api/v1/experiments/gate"), 503, "FEATURE_NOT_ENABLED")


def test_registry_revision_is_pinned_not_silently_swapped(client):
    failure(client.get(f"{BASE}/snapshots?registry_revision=other-revision"), 409, "REVISION_UNAVAILABLE")


# --- C801 / C802 / C803 ---------------------------------------------------------

def test_c801_returns_six_recorded_indices(client):
    data = envelope(client.get(f"{BASE}/snapshots"), SnapshotIndex)
    index = data
    assert index.snapshot_count == 6
    assert [item.snapshot_index for item in index.items] == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize("requested", [1, 6])
def test_c802_recorded_snapshot_is_valid(client, requested):
    data = envelope(client.get(f"{BASE}/snapshots/{requested}"),
                    FieldSnapshot)
    assert data.snapshot_index == requested
    assert data.result.time.index_convention == "USER_VISIBLE_1_BASED_RECORDED_INDEX"


def test_c802_sixth_snapshot_matches_frozen_step_and_time(client):
    data = envelope(client.get(f"{BASE}/snapshots/6"), FieldSnapshot)
    assert (data.snapshot_index, data.step_index, data.physical_time) == (6, 1912, 0.08)


@pytest.mark.parametrize("index", [0, -1, "abc", "1.5"])
def test_c802_zero_and_non_integer_indices_are_invalid_request(client, index):
    failure(client.get(f"{BASE}/snapshots/{index}"), 400, "INVALID_REQUEST")


def test_c802_zero_is_never_converted_to_one(client, adapter):
    failure(client.get(f"{BASE}/snapshots/0"), 400, "INVALID_REQUEST")
    assert all(call[0] != "load_snapshot_metadata" for call in adapter.calls)


def test_c802_seventh_index_is_missing_not_unknown(client):
    body = failure(client.get(f"{BASE}/snapshots/7"), 404, "SNAPSHOT_NOT_FOUND")
    assert body.availability == "MISSING"
    assert body.error.target.resource_type == "case8_snapshot"


def test_c802_unknown_field_is_rejected_without_silent_projection(client):
    failure(client.get(f"{BASE}/snapshots/1?field=not-a-field"), 404, "SNAPSHOT_NOT_FOUND")


def test_c802_known_field_projects_only_that_field(client):
    data = envelope(client.get(f"{BASE}/snapshots/1?field=density"),
                    FieldSnapshot)
    assert [field.field_id for field in data.fields] == ["density"]


def test_c803_field_keeps_its_own_header_and_array_reference(client):
    response = client.get(f"{BASE}/snapshots/6/fields/density")
    payload = envelope(response, FieldResponse)
    assert payload.field.field_id == "density"
    assert payload.field.array_ref.descriptor.element_count == 4096
    assert payload.snapshot.snapshot_index == 6


# --- config identity classification ---------------------------------------------

def test_real_registered_c_config_is_distinct_from_unknown_config(client):
    envelope(client.get("/api/v1/experiments/case8/configs/C_u/snapshots"), SnapshotIndex)
    body = failure(client.get("/api/v1/experiments/case8/configs/Z_u/snapshots"), 404, "UNKNOWN_CONFIG")
    assert body.error.details[0].allowed_values == ["A_u", "B_u", "C_u", "D_u"]


# --- C804 / C805 pagination -----------------------------------------------------

def test_c804_declares_full_history_length_for_a_single_point_page(client):
    response = client.get(f"{BASE}/entropy-history?series=E_at_cumulative&offset=0&limit=1")
    series = envelope(response, EntropyHistory).series[0]
    assert series.total_point_count == HISTORY_POINTS
    assert len(series.points) == 1
    assert series.page.returned_count == 1
    assert series.page.has_more is True


def test_c804_default_page_returns_every_recorded_point(client):
    series = envelope(client.get(f"{BASE}/entropy-history"),
                      EntropyHistory).series[0]
    assert len(series.points) == HISTORY_POINTS
    assert series.page.has_more is False


def test_c804_offset_past_end_is_a_valid_empty_page(client):
    series = envelope(client.get(f"{BASE}/entropy-history?offset=1912&limit=10"),
                      EntropyHistory).series[0]
    assert series.points == []
    assert series.page.returned_count == 0
    assert series.page.has_more is False
    assert series.total_point_count == HISTORY_POINTS


def test_c804_source_step_stays_zero_based_while_canonical_step_is_one_based(client):
    series = envelope(client.get(f"{BASE}/entropy-history?offset=0&limit=1"),
                      EntropyHistory).series[0]
    assert series.points[0].step_index.root.value == 1
    assert series.points[0].source_step_index.root.value == 0


def test_c804_repeated_series_is_accepted_and_duplicates_are_not(client):
    payload = envelope(client.get(f"{BASE}/entropy-history?series=a&series=b"),
                       EntropyHistory)
    assert [series.series_id for series in payload.series] == ["a", "b"]
    failure(client.get(f"{BASE}/entropy-history?offset=1&offset=2"), 400, "INVALID_REQUEST")
    failure(client.get(f"{BASE}/entropy-history?limit=6000"), 400, "INVALID_REQUEST")
    failure(client.get(f"{BASE}/entropy-history?unknown=1"), 400, "INVALID_REQUEST")


def test_c805_series_comes_from_the_path_not_a_repeated_query(client):
    payload = envelope(client.get(f"{BASE}/scalar-series/E_at_cumulative?offset=1900&limit=12"),
                       ScalarSeries)
    assert payload.series_id == "E_at_cumulative"
    assert payload.page.offset == 1900 and len(payload.points) == 12
    assert payload.total_point_count == HISTORY_POINTS
    failure(client.get(f"{BASE}/scalar-series/E_at_cumulative?series=other"), 400, "INVALID_REQUEST")


# --- C806 / C808 ----------------------------------------------------------------

def test_c806_metrics_are_delivered_with_definition_and_detector(client):
    payload = envelope(client.get(f"{BASE}/metrics"), MetricCollection)
    metric = payload.items[0].root.value
    assert metric.definition_id == "mock.definition"
    assert metric.detector.root.value.definition == "Test-only detector"


def test_c808_pinned_requires_snapshot_and_nearest_forbids_it(client):
    pinned = envelope(client.get(f"{BASE}/snapshot-alignment?scalar_step=1912&policy=PINNED&snapshot_index=6"),
                      SnapshotAlignment)
    assert pinned.signed_time_delta == pytest.approx(0.08 - 1912 * 0.08 / 1911)
    failure(client.get(f"{BASE}/snapshot-alignment?scalar_step=1&policy=PINNED"), 400, "INVALID_REQUEST")
    failure(client.get(f"{BASE}/snapshot-alignment?scalar_step=1&snapshot_index=2"), 400, "INVALID_REQUEST")
    failure(client.get(f"{BASE}/snapshot-alignment"), 400, "INVALID_REQUEST")


# --- ARRAY01 --------------------------------------------------------------------

def test_array01_returns_flat_values_matching_the_descriptor(client):
    response = client.get("/api/v1/results/mock.case8.D_u.snapshot.6.density/arrays/density")
    array = envelope(response, ScientificArray)
    assert len(array.values) == array.descriptor.element_count == 4096
    assert array.result.result_id == "mock.case8.D_u.snapshot.6.density"


def test_array01_has_no_free_file_or_dtype_parameters(client):
    failure(client.get("/api/v1/results/mock.case8.D_u.snapshot.6.density/arrays/density?dtype=float32"),
            400, "INVALID_REQUEST")
    failure(client.get("/api/v1/results/mock.case8.D_u.snapshot.6.density/arrays/density?path=C:/x.npz"),
            400, "INVALID_REQUEST")


# --- EVI02 / EVI03 ---------------------------------------------------------------

def test_evi02_evidence_detail_and_evi03_provenance(client):
    record = envelope(client.get("/api/v1/evidence/mock.evidence.adapter"),
                      EvidenceRecord)
    assert record.evidence_id == "mock.evidence.adapter"
    assert record.result_ids == [record.result_contexts[0].result_id]
    failure(client.get("/api/v1/evidence/not-mock"), 404, "UNKNOWN_EVIDENCE_ID")

    provenance = envelope(client.get("/api/v1/results/mock.case8.D_u.snapshot.6.density/provenance"),
                          ResultProvenance)
    assert provenance.provenance.evidence_refs == ["mock.evidence.adapter"]
    failure(client.get("/api/v1/results/mock.missing/provenance"), 404, "INVALID_RESULT_ID")


# --- routing / envelope hygiene ---------------------------------------------------

def test_404_and_405_are_json_in_the_api_namespace(client):
    body = failure(client.get("/api/v1/nope"), 404, "API_ROUTE_NOT_FOUND")
    assert body.availability == "MISSING" and body.error.domain == "SYSTEM"
    response = client.post(f"{BASE}/snapshots")
    assert response.status_code == 405
    assert response.json["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["Allow"]


def test_every_response_is_no_store_with_a_server_request_id(client):
    response = client.get(f"{BASE}/snapshots", headers={"X-Request-ID": "untrusted"})
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"] != "untrusted"
    assert response.json["request_id"] == response.headers["X-Request-ID"]


def test_undelivered_adapter_reports_feature_not_enabled():
    from backend import create_app
    client = create_app(case8_adapter=None).test_client()
    failure(client.get(f"{BASE}/snapshots"), 503, "FEATURE_NOT_ENABLED")


# --- OpenAPI coverage ------------------------------------------------------------

IMPLEMENTED = {"SYS01", "DOC01", "REG01", "REG02", "REG03", "REG04", "C801", "C802",
               "C803", "C804", "C805", "C806", "C808", "ARRAY01", "EVI01", "EVI02", "EVI03", "EVI04",
               # Phase 6B Window 3 delivered the four allocation operations.
               "ALLOC01", "ALLOC02", "ALLOC03", "ALLOC04",
               # Phase 7B Window 2 delivered the spectral dataset/curve/record/eigenmode/validation ops.
               # Phase 7B Window 3 added SPEC06 (the registered validation-run identities).
               "SPEC00", "SPEC01", "SPEC02", "SPEC03", "SPEC04", "SPEC05", "SPEC06",
               # Phase 8 Window 2 declares Cylinder/composite routes even when
               # this isolated Case8 fixture disables the Cylinder adapter.
               "CYL01", "CYL02", "CYL03", "CYL04", "CYL05", "CYL06", "CYL07", "CYL08", "CYL09", "CMP01",
               "CONTENT01", "CONTENT02", "CONTENT03",
               # Phase 9B Window 2 declares the frozen Closure API even when
               # this isolated Case8 fixture disables the Closure adapter.
               "CLO01", "CLO02", "CLO03", "CLO04", "CLO05"}


def test_openapi_operations_match_the_catalog_and_runtime_routes(app):
    catalog = app.extensions["operation_catalog"]
    document = export_openapi(catalog)
    validate(document)
    # This freezes the V1 contract. V2 product operations have their own
    # independent DTO/error contracts and tests; all runtime routes still
    # participate in the catalog equality check below.
    assert {item.operation_id for item in catalog.operations if item.path.startswith("/api/v1/")} == IMPLEMENTED
    documented = {entry["operationId"] for name, path in document["paths"].items() if name.startswith("/api/v1/")
                  for entry in path.values()}
    assert documented == IMPLEMENTED
    catalog.assert_routes(app)
    # C807 stays CONTRACT_DEFINED / IMPLEMENTATION_DEFERRED, so it must not be advertised.
    assert "C807" not in documented
    # Window 3 routes live under /api/v1/allocations/*; nothing advertises C807's {base}/allocation.
    assert not any(path.startswith("/api/v1/experiments/case8/configs/") and path.endswith("/allocation")
                   for path in document["paths"])


def test_openapi_paths_and_methods_match_the_catalog_exactly(app):
    catalog = app.extensions["operation_catalog"]
    document = export_openapi(catalog)
    expected = {(item.method.lower(), item.path) for item in catalog.operations}
    actual = {(method, path) for path, entry in document["paths"].items() for method in entry}
    assert actual == expected
    assert app.test_client().get("/api/v1/openapi.json").json == document


@pytest.mark.parametrize("path,method", [
    ("/api/v1/experiments", "get"),
    ("/api/v1/experiments/case8/configs/{config_id}/snapshots/{snapshot_index}", "get"),
    ("/api/v1/results/{result_id}/arrays/{array_id}", "get"),
])
def test_openapi_declares_path_parameters_as_required(app, path, method):
    document = export_openapi(app.extensions["operation_catalog"])
    names = re.findall(r"\{([^}]+)\}", path)
    parameters = {item["name"]: item for item in document["paths"][path][method].get("parameters", [])}
    for name in names:
        assert parameters[name]["in"] == "path" and parameters[name]["required"] is True


def test_documented_errors_are_real_contract_codes(app):
    from backend.core.errors import SCIENTIFIC_CODES, SERVER_SIDE_CODES, SYSTEM_CODES
    known = SYSTEM_CODES | SCIENTIFIC_CODES | SERVER_SIDE_CODES | {
        "INVALID_EMAIL", "UNAUTHENTICATED", "INVALID_CREDENTIALS", "CSRF_FAILED",
        "METHOD_NOT_ALLOWED", "UNSUPPORTED_MEDIA_TYPE", "API_ROUTE_NOT_FOUND",
        "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ", "REVISION_UNAVAILABLE",
        "ACCOUNT_ALREADY_EXISTS", "INVALID_OR_EXPIRED_CODE", "RATE_LIMITED",
        "MAIL_SERVICE_UNAVAILABLE", "ACCOUNT_STORE_UNAVAILABLE", "UNKNOWN_EVIDENCE_ID",
        "UNKNOWN_ASSET_ID", "UNKNOWN_DEFINITION_ID"}
    for operation in app.extensions["operation_catalog"].operations:
        if not operation.path.startswith("/api/v1/"):
            continue
        for status, codes in operation.documented_errors.items():
            assert codes, operation.operation_id
            for code in codes:
                assert code in known, f"{operation.operation_id} documents unknown {code}"
            assert 200 <= status < 600


# --- response schema conformance --------------------------------------------------

@pytest.mark.parametrize("url", [
    "/api/v1/system",
    "/api/v1/experiments",
    "/api/v1/experiments/case8",
    "/api/v1/experiments/case8/configs",
    "/api/v1/experiments/case8/capabilities",
    f"{BASE}/snapshots",
    f"{BASE}/snapshots/6",
    f"{BASE}/snapshots/6/fields/density",
    f"{BASE}/entropy-history?limit=2",
    f"{BASE}/scalar-series/E_at_cumulative?limit=2",
    f"{BASE}/metrics",
    f"{BASE}/snapshot-alignment?scalar_step=1912&policy=PINNED&snapshot_index=6",
    "/api/v1/results/mock.case8.D_u.snapshot.6.density/arrays/density",
    "/api/v1/evidence/mock.evidence.adapter",
    "/api/v1/results/mock.case8.D_u.snapshot.6.density/provenance",
])
def test_responses_validate_against_the_exported_openapi_schema(app, url):
    """Every success body must satisfy the OpenAPI schema the frontend will generate from."""
    document = export_openapi(app.extensions["operation_catalog"])
    matcher = app.url_map.bind("localhost")
    endpoint, _ = matcher.match(url.split("?")[0])
    # Blueprint-qualified endpoint is "<blueprint>.<operation_id>".
    operation_id = endpoint.rsplit(".", 1)[-1]
    assert operation_id in IMPLEMENTED, operation_id

    response = app.test_client().get(url)
    assert response.status_code == 200, response.text
    entry = next(item for path in document["paths"].values() for item in path.values()
                 if item["operationId"] == operation_id)
    schema = entry["responses"]["200"]["content"]["application/json"]["schema"]
    Draft202012Validator({**schema, "components": document["components"]}).validate(response.json)


def test_openapi_declares_a_documented_error_schema_too(app):
    document = export_openapi(app.extensions["operation_catalog"])
    for operation in app.extensions["operation_catalog"].operations:
        entry = document["paths"][operation.path][operation.method.lower()]
        for status, codes in operation.documented_errors.items():
            declared = entry["responses"][str(status)]
            assert declared["x-error-codes"] == list(codes)
            expected = "/V2FailedEnvelope" if operation.path.startswith("/api/v2/") else "/FailedEnvelope"
            assert declared["content"]["application/json"]["schema"]["$ref"].endswith(expected)


def test_service_revalidates_adapter_output_before_the_handler_sees_it():
    class LooseAdapter:
        def list_configs(self):
            return {"experiment_id": "case8", "items": [], "absolute_source_path": "D:\\secret"}

    from backend import create_app
    app = create_app(case8_adapter=LooseAdapter())
    with pytest.raises(Exception):
        app.extensions["case8_service"].list_configs()


def test_fake_adapter_is_confined_to_the_test_tree():
    """The fake must never reach the production composition root."""
    from backend.services import Case8Service
    import backend.registry as registry
    assert "fake_case8_adapter" not in dir(registry)
    assert Case8Service(None).adapter is None
    with pytest.raises(DomainError) as error:
        Case8Service(None).list_snapshots("D_u")
    assert error.value.status == 503 and error.value.body.code == "FEATURE_NOT_ENABLED"


def test_client_never_supplies_a_scientific_path(app):
    """No operation accepts a path/root/file parameter, by catalog construction."""
    catalog = app.extensions["operation_catalog"]
    forbidden = {"path", "file", "root", "source_path", "absolute_path", "member", "npz"}
    for operation in catalog.operations:
        if operation.request_model is None:
            continue
        assert not (set(operation.request_model.model_fields) & forbidden), operation.operation_id
    assert RegistryQuery.model_fields.keys() == {"registry_revision"}
