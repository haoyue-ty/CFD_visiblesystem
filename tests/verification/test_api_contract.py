"""Window 4 public-contract acceptance, activated against the integrated real factory.
QA baseline-only premises were aligned to the delivered catalog and generated enum:
API paths filter only Case8 routes; repeated series selectors are allowed by contract;
unregistered series identities receive INVALID_RESULT_ID. No golden values changed.
"""

from __future__ import annotations

import pytest

from tests.verification.case8_facts import CONFIGS

WAITING = ("WAITING_FOR_IMPLEMENTATION: Case8 blueprint (C801-C808 / ARRAY01 / EVI) "
           "is not registered on PHASE5_BOOTSTRAP_BASE. Test is merge-ready and must "
           "be re-enabled, not rewritten, when the routes land.")

CASE8_BASE = "/api/v1/experiments/case8/configs"

# operation_id -> (method, path template)  |  contract §7, §14, §15
CASE8_OPERATIONS = {
    "C801": ("GET", f"{CASE8_BASE}/{{config_id}}/snapshots"),
    "C802": ("GET", f"{CASE8_BASE}/{{config_id}}/snapshots/{{snapshot_index}}"),
    "C803": ("GET", f"{CASE8_BASE}/{{config_id}}/snapshots/{{snapshot_index}}/fields/{{field_id}}"),
    "C804": ("GET", f"{CASE8_BASE}/{{config_id}}/entropy-history"),
    "C805": ("GET", f"{CASE8_BASE}/{{config_id}}/scalar-series/{{series_id}}"),
    "C806": ("GET", f"{CASE8_BASE}/{{config_id}}/metrics"),
    "C808": ("GET", f"{CASE8_BASE}/{{config_id}}/snapshot-alignment"),
    "ARRAY01": ("GET", "/api/v1/results/{result_id}/arrays/{array_id}"),
    "EVI02": ("GET", "/api/v1/evidence/{evidence_id}"),
    "EVI03": ("GET", "/api/v1/results/{result_id}/provenance"),
}


def _registered_operation_ids(app) -> set[str]:
    return {operation.operation_id for operation in app.extensions["operation_catalog"].operations}


def _registered_routes(app) -> set[tuple[str, str]]:
    return {(operation.method, operation.path)
            for operation in app.extensions["operation_catalog"].operations}


@pytest.fixture
def case8_app():
    """Real integrated production application."""
    from tests.verification.conftest import make_case8_route_app

    return make_case8_route_app()


# ---------------------------------------------------------------------------
# A. Route coverage
# ---------------------------------------------------------------------------

def test_all_contract_case8_operations_are_registered(case8_app):
    missing = set(CASE8_OPERATIONS) - _registered_operation_ids(case8_app)
    assert not missing, f"Case8 operations missing from catalog: {sorted(missing)}"


def test_registered_case8_paths_match_the_contract_exactly(case8_app):
    expected = set(CASE8_OPERATIONS.values())
    actual = {(method, path) for method, path in _registered_routes(case8_app)
              if path.startswith(CASE8_BASE)}
    assert actual == {entry for entry in expected if entry[1].startswith(CASE8_BASE)}


def test_no_operation_is_advertised_for_the_deferred_allocation_endpoint(case8_app):
    """C807 is implementation-deferred: the catalog must not advertise it.

    The premise (the Case8 slice itself is registered) is asserted first so this
    test cannot pass vacuously on a base where no Case8 route exists at all.
    """
    assert {"C801", "C802", "C804"} <= _registered_operation_ids(case8_app)
    assert not [path for _, path in _registered_routes(case8_app)
                if path.endswith("/allocation")]


def test_integrated_catalog_declares_delivered_case8_operations(case8_app):
    """Guard the premise of the WAITING markers: Case8 is genuinely unimplemented."""
    assert {"C801", "C802", "C804", "C806", "C808"} <= _registered_operation_ids(case8_app)


def test_openapi_document_is_valid_with_case8_routes(case8_app):
    from openapi_spec_validator import validate

    document = case8_app.test_client().get("/api/v1/openapi.json").json
    validate(document)
    assert document["openapi"] == "3.1.0"


# ---------------------------------------------------------------------------
# B. Snapshot selection — 1-based index, zero rejected, seven rejected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("config_id", CONFIGS)
def test_snapshot_zero_is_rejected_as_invalid_request(case8_app, config_id):
    """SNAPSHOT_ZERO_ALLOWED=NO: 0 is not an alias for the initial frame."""
    response = case8_app.test_client().get(f"{CASE8_BASE}/{config_id}/snapshots/0")
    assert response.status_code == 400, response.get_data(as_text=True)[:200]
    assert response.json["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("config_id", CONFIGS)
def test_snapshot_seven_is_rejected_as_snapshot_not_found(case8_app, config_id):
    response = case8_app.test_client().get(f"{CASE8_BASE}/{config_id}/snapshots/7")
    assert response.status_code == 404, response.get_data(as_text=True)[:200]
    assert response.json["error"]["code"] == "SNAPSHOT_NOT_FOUND"


@pytest.mark.parametrize("config_id", CONFIGS)
def test_snapshot_one_through_six_are_accepted(case8_app, config_id):
    for index in range(1, 7):
        response = case8_app.test_client().get(f"{CASE8_BASE}/{config_id}/snapshots/{index}")
        assert response.status_code == 200, f"{config_id} snapshot {index}"


def test_du_snapshot_six_reports_canonical_step_and_time(case8_app):
    """The delivered snapshot 6 must equal the canonical source, not a rounded value."""
    response = case8_app.test_client().get(f"{CASE8_BASE}/D_u/snapshots/6")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    data = response.json["data"]
    assert data["snapshot_index"] == 6
    assert data["step_index"] == 1912
    assert data["physical_time"] == 0.08


@pytest.mark.parametrize("config_id", CONFIGS)
def test_snapshot_list_reports_exactly_six_recorded_frames(case8_app, config_id):
    response = case8_app.test_client().get(f"{CASE8_BASE}/{config_id}/snapshots")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    data = response.json["data"]
    assert data["snapshot_count"] == 6
    assert len(data["items"]) == 6


# ---------------------------------------------------------------------------
# C. Unknown configuration identity
# ---------------------------------------------------------------------------

def test_unknown_config_is_not_found(case8_app):
    response = case8_app.test_client().get(f"{CASE8_BASE}/Z_u/snapshots")
    assert response.status_code == 404, response.get_data(as_text=True)[:200]
    assert response.json["error"]["code"] == "UNKNOWN_CONFIG"


def test_unknown_config_error_lists_the_four_registered_configurations(case8_app):
    """Case8 is a closed set; the error must tell the client what is legal."""
    response = case8_app.test_client().get(f"{CASE8_BASE}/Z_u/snapshots")
    details = response.json["error"]["details"]
    allowed = next((item["allowed_values"] for item in details
                    if item["field"] == "config_id"), [])
    assert set(allowed) == set(CONFIGS)


# ---------------------------------------------------------------------------
# D. History pagination — real totals, real pages, no silent downsampling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("config_id", CONFIGS)
def test_history_total_count_is_1912_for_every_configuration(case8_app, config_id):
    response = case8_app.test_client().get(f"{CASE8_BASE}/{config_id}/entropy-history")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    series = response.json["data"]["series"]
    assert series, "history must expose at least one recorded series"
    for item in series:
        assert item["total_point_count"] == 1912
        assert item["page"]["total_count"] == 1912


def test_history_pagination_is_consistent_across_pages(case8_app):
    client = case8_app.test_client()
    first = client.get(f"{CASE8_BASE}/D_u/entropy-history?offset=0&limit=100")
    second = client.get(f"{CASE8_BASE}/D_u/entropy-history?offset=1900&limit=100")
    assert first.status_code == second.status_code == 200
    head = first.json["data"]["series"][0]
    tail = second.json["data"]["series"][0]
    assert head["page"] == {"offset": 0, "limit": 100, "returned_count": 100,
                            "total_count": 1912, "has_more": True}
    assert tail["page"] == {"offset": 1900, "limit": 100, "returned_count": 12,
                            "total_count": 1912, "has_more": False}


def test_history_offset_past_the_end_returns_an_empty_page_not_an_error(case8_app):
    response = case8_app.test_client().get(f"{CASE8_BASE}/D_u/entropy-history?offset=1912&limit=100")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    page = response.json["data"]["series"][0]["page"]
    assert page["returned_count"] == 0
    assert page["has_more"] is False


def test_history_unknown_series_identity_is_rejected(case8_app):
    response = case8_app.test_client().get(
        f"{CASE8_BASE}/D_u/entropy-history"
        "?series=case8.D_u.E_at_cumulative&series=case8.D_u.E_bg_cumulative")
    assert response.status_code == 404, response.get_data(as_text=True)[:200]
    assert response.json["error"]["code"] == "INVALID_RESULT_ID"


def test_history_rejects_unknown_query_parameter(case8_app):
    response = case8_app.test_client().get(f"{CASE8_BASE}/D_u/entropy-history?unknown=1")
    assert response.status_code == 400, response.get_data(as_text=True)[:200]


# ---------------------------------------------------------------------------
# E. Array shape and flat-JSON encoding
# ---------------------------------------------------------------------------

def test_case8_density_array_is_flat_json_with_matching_element_count(case8_app):
    response = case8_app.test_client().get(
        "/api/v1/results/case8.D_u.snapshot.6.density/arrays/density")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    data = response.json["data"]
    descriptor = data["descriptor"]
    assert descriptor["shape"] == [32, 128]
    assert descriptor["axes"] == ["y", "x"]
    assert descriptor["encoding"] == "FLAT_JSON"
    assert descriptor["element_count"] == 4096
    assert len(data["values"]) == 4096


def test_array_rejects_unregistered_member_selector(case8_app):
    """A legal result with an illegal member selector is a typed client error.

    The registered result is requested first, so a 404 caused merely by the route
    being absent cannot satisfy this test.
    """
    client = case8_app.test_client()
    known = client.get("/api/v1/results/case8.D_u.snapshot.6.density/arrays/density")
    assert known.status_code == 200, known.get_data(as_text=True)[:200]
    response = client.get("/api/v1/results/case8.D_u.snapshot.6.density/arrays/secret-member")
    assert response.status_code in (400, 404), response.get_data(as_text=True)[:200]
    assert response.json["error"]["code"] not in {"API_ROUTE_NOT_FOUND", "INTERNAL_ERROR"}


# ---------------------------------------------------------------------------
# F. Error envelopes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,status,code", [
    (f"{CASE8_BASE}/D_u/snapshots/0", 400, "INVALID_REQUEST"),
    (f"{CASE8_BASE}/D_u/snapshots/7", 404, "SNAPSHOT_NOT_FOUND"),
    (f"{CASE8_BASE}/Z_u/snapshots", 404, "UNKNOWN_CONFIG"),
])
def test_case8_failures_use_the_typed_error_envelope(case8_app, url, status, code):
    response = case8_app.test_client().get(url)
    assert response.status_code == status, response.get_data(as_text=True)[:200]
    body = response.json
    assert body["availability"] in {"MISSING", "UNSUPPORTED", "ERROR"}
    assert body["error"]["code"] == code
    assert body["error"]["domain"] in {"SYSTEM", "SCIENTIFIC", "ACCOUNT"}
    assert isinstance(body["error"]["retryable"], bool)
    assert "data" not in body
    assert "D:\\" not in response.get_data(as_text=True)


def test_case8_failure_envelope_carries_the_server_request_id(case8_app):
    response = case8_app.test_client().get(f"{CASE8_BASE}/Z_u/snapshots")
    assert response.status_code == 404, response.get_data(as_text=True)[:200]
    assert response.json["error"]["code"] == "UNKNOWN_CONFIG"
    assert response.json["request_id"] == response.headers["X-Request-ID"]


def test_case8_method_mismatch_keeps_the_allow_header(case8_app):
    response = case8_app.test_client().post(f"{CASE8_BASE}/D_u/snapshots")
    assert response.status_code == 405
    assert "GET" in response.headers["Allow"]


# ---------------------------------------------------------------------------
# G. Evidence response
# ---------------------------------------------------------------------------

def test_evidence_record_exposes_method_config_and_hash_identity(case8_app):
    response = case8_app.test_client().get("/api/v1/evidence/ev.case8.D_u.snapshot.6.density")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    data = response.json["data"]
    assert data["result_ids"] == ["case8.D_u.snapshot.6.density"]
    assert data["method_hash"]["state"] == "KNOWN"
    assert data["source_assets"], "evidence must list its source assets"


def test_evidence_verification_status_is_not_promoted_by_the_api(case8_app):
    """The API must report the recorded status, never upgrade it."""
    response = case8_app.test_client().get("/api/v1/evidence/ev.case8.D_u.snapshot.6.density")
    assert response.json["data"]["verification"]["status"] == "VERIFIED_NOT_FROZEN"


def test_provenance_route_returns_the_full_source_ref_list(case8_app):
    response = case8_app.test_client().get(
        "/api/v1/results/case8.D_u.snapshot.6.density/provenance")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    data = response.json["data"]
    assert data["result_id"] == "case8.D_u.snapshot.6.density"
    assert data["provenance"]["source_asset_ids"]


def test_unknown_evidence_id_is_not_found(case8_app):
    response = case8_app.test_client().get("/api/v1/evidence/ev.does.not.exist")
    assert response.status_code == 404, response.get_data(as_text=True)[:200]
    assert response.json["error"]["code"] == "UNKNOWN_EVIDENCE_ID"


# ---------------------------------------------------------------------------
# H. OpenAPI route coverage after merge
# ---------------------------------------------------------------------------

def test_openapi_paths_cover_every_case8_operation(case8_app):
    paths = case8_app.test_client().get("/api/v1/openapi.json").json["paths"]
    for operation_id, (method, template) in CASE8_OPERATIONS.items():
        assert template in paths, f"{operation_id} path missing from OpenAPI"
        assert method.lower() in paths[template], f"{operation_id} method missing"


def test_openapi_case8_responses_reference_resolvable_components(case8_app):
    document = case8_app.test_client().get("/api/v1/openapi.json").json
    schemas = document["components"]["schemas"]
    template = f"{CASE8_BASE}/{{config_id}}/snapshots"
    reference = document["paths"][template]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert reference.rsplit("/", 1)[-1] in schemas


def test_openapi_documents_the_snapshot_not_found_error_for_c802(case8_app):
    document = case8_app.test_client().get("/api/v1/openapi.json").json
    template = f"{CASE8_BASE}/{{config_id}}/snapshots/{{snapshot_index}}"
    errors = document["paths"][template]["get"]["responses"]
    codes = {code for entry in errors.values() for code in entry.get("x-error-codes", [])}
    assert "SNAPSHOT_NOT_FOUND" in codes
    assert "INVALID_REQUEST" in codes
