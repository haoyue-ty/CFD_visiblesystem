"""Window 2 spectral API acceptance: valid / missing / unsupported / schema validation.

Every success response must carry ``representation``, ``q_at``, ``verification`` and
``provenance`` (and ``mode_index`` for point/eigenmode views) so the Spectral Lab never
guesses what it is looking at. No value is fabricated or interpolated: a MISSING linear
amplitude stays a reason-bearing fact, and PARTIAL validation carries its issue list.
"""
import pytest

from backend import create_app
from fake_spectral_adapter import DATASET_IDS, RUN_IDS, FakeSpectralAdapter

BASE = "/api/v1/spectra"
DATASET = "mock.spectrum.q-0.396"
RUN = "mock.modal-validation.m8_q0.396_eps1e-05"

SPECTRAL_OPERATION_IDS = {"SPEC00", "SPEC01", "SPEC02", "SPEC03", "SPEC04", "SPEC05", "SPEC06"}
REQUIRED_FIELDS = ("representation", "q_at", "verification", "provenance")


def _failure(response, status: int, code: str):
    assert response.status_code == status, response.get_data(as_text=True)
    assert response.headers["Cache-Control"] == "no-store"
    body = response.json
    assert body["availability"] in {"MISSING", "UNSUPPORTED", "ERROR"}
    assert body["error"]["code"] == code
    return body


def _ok(response):
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.json


# --- registration / OpenAPI -------------------------------------------------------

def test_all_spectral_operations_are_registered(app):
    ids = {op.operation_id for op in app.extensions["operation_catalog"].operations}
    assert SPECTRAL_OPERATION_IDS <= ids
    paths = {op.path for op in app.extensions["operation_catalog"].operations}
    assert f"{BASE}/{{dataset_id}}/points" in paths
    assert f"{BASE}/{{dataset_id}}/eigenmodes/{{mode_index}}" in paths
    assert f"{BASE}/validation/{{run_id}}" in paths
    assert f"{BASE}/validation/runs" in paths


def test_spectral_operations_are_in_the_exported_openapi(app):
    document = app.test_client().get("/api/v1/openapi.json").json
    documented = {entry["operationId"] for path in document["paths"].values()
                  for entry in path.values()}
    assert SPECTRAL_OPERATION_IDS <= documented


def test_openapi_paths_and_methods_match_the_catalog(app):
    document = app.test_client().get("/api/v1/openapi.json").json
    spectral = {path for path in document["paths"] if path.startswith(BASE)}
    assert spectral == {
        BASE, f"{BASE}/{{dataset_id}}", f"{BASE}/{{dataset_id}}/points",
        f"{BASE}/{{dataset_id}}/points/{{mode_index}}",
        f"{BASE}/{{dataset_id}}/eigenmodes/{{mode_index}}", f"{BASE}/validation/{{run_id}}",
        f"{BASE}/validation/runs"}


# --- valid ------------------------------------------------------------------------

def test_list_datasets_valid(client):
    body = _ok(client.get(BASE))
    assert body["availability"] == "AVAILABLE"
    assert len(body["data"]) == len(DATASET_IDS)
    assert {item["dataset_id"] for item in body["data"]} == set(DATASET_IDS)
    assert all(item["representation"] == "SPECTRUM_DATASET" for item in body["data"])


def test_dataset_valid_carries_required_fields(client):
    body = _ok(client.get(f"{BASE}/{DATASET}"))
    assert body["availability"] == "AVAILABLE"
    data = body["data"]
    assert data["representation"] == "SPECTRUM_DATASET"
    assert data["q_at"] == 0.396
    assert data["dataset_id"] == DATASET
    assert data["record_count"] == 17
    assert data["eigenvalues_per_block"] == 512
    assert data["saved_vectors_per_side"] == 32
    assert data["mode_indices"] == list(range(17))
    assert data["matrix_availability"] == "MISSING"
    assert all(key in data for key in REQUIRED_FIELDS)
    assert data["verification"]["status"] == "NOT_APPLICABLE"  # MOCK never claims verification
    assert data["provenance"]["registry_revision"] == "mock.registry"


def test_curve_valid_has_seventeen_ordered_points(client):
    body = _ok(client.get(f"{BASE}/{DATASET}/points"))
    data = body["data"]
    assert data["representation"] == "SPECTRUM_CURVE"
    assert data["q_at"] == 0.396
    assert [point["mode_index"] for point in data["points"]] == list(range(17))
    assert all(point["representation"] == "SPECTRUM_POINT" for point in data["points"])


def test_point_valid_carries_mode_index_and_required_fields(client):
    body = _ok(client.get(f"{BASE}/{DATASET}/points/8"))
    data = body["data"]
    assert data["representation"] == "SPECTRUM_POINT"
    assert data["mode_index"] == 8
    assert data["q_at"] == 0.396
    assert data["spectrum_record_id"] == f"{DATASET}.mode-08"
    assert all(key in data for key in REQUIRED_FIELDS)


def test_eigenmode_valid_complex_vector(client):
    body = _ok(client.get(f"{BASE}/{DATASET}/eigenmodes/8", query_string={"side": "RIGHT", "rank": "0"}))
    data = body["data"]
    assert data["representation"] == "EIGENMODE"
    assert data["eigen_representation"] == "COMPLEX_VECTOR"
    assert data["mode_index"] == 8
    assert data["side"] == "RIGHT"
    assert data["rank"] == 0
    assert data["shape"] == [128, 4]
    assert all(key in data for key in REQUIRED_FIELDS)


def test_eigenmode_valid_primitive_profile(client):
    body = _ok(client.get(f"{BASE}/{DATASET}/eigenmodes/4", query_string={
        "representation": "PRIMITIVE_PROFILE", "projection": "AMPLITUDE", "field_component": "density"}))
    data = body["data"]
    assert data["eigen_representation"] == "PRIMITIVE_PROFILE"
    assert data["projection"] == "AMPLITUDE"
    assert data["shape"] == [128]


def test_validation_valid_is_partial_with_issues(client):
    body = _ok(client.get(f"{BASE}/validation/{RUN}"))
    data = body["data"]
    assert data["representation"] == "GROWTH_VALIDATION"
    assert data["q_at"] == 0.396
    assert data["mode_index"] == 8
    assert data["epsilon"] == 1e-5
    assert len(data["time"]) == 33
    assert data["fit_point_count"] == 33
    assert all(key in data for key in REQUIRED_FIELDS)
    # The absent linear amplitude stays a reason-bearing fact; nothing is synthesized.
    assert all(item["state"] == "MISSING" for item in data["linear_amplitude"])
    assert data["growth_rate"]["cfd"]["state"] == "KNOWN"
    assert data["issues"], "PARTIAL validation carries the missing-amplitude issue"


def test_validation_partial_envelope_matches_data_issues(client):
    body = _ok(client.get(f"{BASE}/validation/{RUN}"))
    assert body["availability"] == "PARTIAL"
    assert body["issues"] == body["data"]["issues"]


# --- missing ----------------------------------------------------------------------

def test_unknown_dataset_is_a_typed_404_unknown_spectrum():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    body = _failure(client.get(f"{BASE}/mock.spectrum.q-9.999"), 404, "UNKNOWN_SPECTRUM")
    assert body["error"]["domain"] == "SCIENTIFIC"


def test_missing_asset_is_a_typed_404():
    client = create_app(spectral_adapter=FakeSpectralAdapter("missing")).test_client()
    for path in (f"{BASE}/{DATASET}", f"{BASE}/{DATASET}/points"):
        body = _failure(client.get(path), 404, "MISSING_ASSET")
        assert body["error"]["domain"] == "SCIENTIFIC"


def test_missing_eigenmode_is_a_typed_404():
    client = create_app(spectral_adapter=FakeSpectralAdapter("missing_mode")).test_client()
    body = _failure(client.get(f"{BASE}/{DATASET}/eigenmodes/8"), 404, "MISSING_EIGENMODE")
    assert body["error"]["domain"] == "SCIENTIFIC"


def test_unknown_mode_is_a_typed_404():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    body = _failure(client.get(f"{BASE}/{DATASET}/points/99"), 404, "UNKNOWN_MODE")
    assert body["error"]["domain"] == "SCIENTIFIC"


def test_unknown_validation_run_is_a_typed_404():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    _failure(client.get(f"{BASE}/validation/mock.modal-validation.nope"), 404, "UNKNOWN_SPECTRUM")


# --- unsupported ------------------------------------------------------------------

def test_unsupported_selector_is_a_typed_422():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    body = _failure(client.get(f"{BASE}/{DATASET}/eigenmodes/8", query_string={"rank": "99"}),
                    422, "UNSUPPORTED_PARAMETER")
    assert body["error"]["domain"] == "SCIENTIFIC"


def test_unsupported_component_for_complex_vector_is_rejected():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    _failure(client.get(f"{BASE}/{DATASET}/eigenmodes/8",
                        query_string={"field_component": "density"}), 422, "UNSUPPORTED_PARAMETER")


def test_unsupported_left_primitive_profile_is_rejected():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    _failure(client.get(f"{BASE}/{DATASET}/eigenmodes/8", query_string={
        "side": "LEFT", "representation": "PRIMITIVE_PROFILE",
        "projection": "AMPLITUDE", "field_component": "density"}), 422, "UNSUPPORTED_PARAMETER")


def test_adapter_unsupported_slot_maps_to_422():
    client = create_app(spectral_adapter=FakeSpectralAdapter("unsupported")).test_client()
    _failure(client.get(f"{BASE}/{DATASET}"), 422, "UNSUPPORTED_PARAMETER")


# --- source failure ---------------------------------------------------------------

def test_source_error_is_a_typed_500():
    client = create_app(spectral_adapter=FakeSpectralAdapter("source")).test_client()
    body = _failure(client.get(f"{BASE}/{DATASET}"), 500, "SOURCE_ERROR")
    assert body["error"]["domain"] == "SYSTEM"


# --- transport hygiene / schema validation ----------------------------------------

def test_unknown_query_parameter_is_rejected():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    _failure(client.get(f"{BASE}/{DATASET}", query_string={"guess": "0.5"}), 400, "INVALID_REQUEST")


def test_non_integer_mode_selector_is_rejected():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    _failure(client.get(f"{BASE}/{DATASET}/points/abc"), 400, "INVALID_REQUEST")


def test_undelivered_adapter_reports_feature_not_enabled():
    client = create_app(spectral_adapter=None).test_client()
    _failure(client.get(BASE), 503, "FEATURE_NOT_ENABLED")


def test_revision_mismatch_is_rejected():
    client = create_app(spectral_adapter=FakeSpectralAdapter()).test_client()
    _failure(client.get(f"{BASE}/{DATASET}", query_string={"registry_revision": "some-other-rev"}),
             409, "REVISION_UNAVAILABLE")


@pytest.mark.parametrize("path", [
    BASE, f"{BASE}/{DATASET}", f"{BASE}/{DATASET}/points", f"{BASE}/{DATASET}/points/8",
    f"{BASE}/{DATASET}/eigenmodes/8", f"{BASE}/validation/{RUN}",
])
def test_success_responses_validate_against_the_declared_schema(app, path):
    """A 200 already revalidated the declared response model; re-check it strictly here.

    The catalog builds the response by ``response_model.model_validate`` on the handler
    payload, so a 200 is a schema proof; this re-validates the JSON to guard against a
    later relaxation of the transport layer.
    """
    client = app.test_client()
    response = client.get(path)
    assert response.status_code == 200, response.get_data(as_text=True)

    # Match the concrete runtime request path to its catalog operation.
    resolved = response.request.path
    operations = [op for op in app.extensions["operation_catalog"].operations
                  if op.path.replace("{dataset_id}", DATASET).replace("{run_id}", RUN)
                  .replace("{mode_index}", resolved.rsplit("/", 1)[-1]) == resolved]
    assert operations, resolved
    operations[0].response_model.model_validate(response.json)


# --- SPEC06: validation-run selector list -----------------------------------------

def test_validation_run_list_returns_the_full_registered_registry(app):
    """SPEC06 lists all registered run identities from pinned registry metadata."""
    from backend.registry import spectral_registry as registry
    response = app.test_client().get(f"{BASE}/validation/runs")
    body = _ok(response)
    assert body["availability"] == "AVAILABLE"
    data = body["data"]
    assert data["representation"] == "VALIDATION_RUN_LIST"
    assert data["run_count"] == len(registry.RUNS)
    ids = [run["run_id"] for run in data["runs"]]
    assert ids == list(registry.RUNS)              # recorded order preserved
    assert len(ids) == len(set(ids))               # unique identities
    for run, (_mode, q_at, epsilon, _history) in zip(data["runs"], registry.RUNS.values()):
        assert run["q_at"] == q_at and run["epsilon"] == epsilon


def test_validation_run_list_is_adapter_independent(app):
    """The selector list is registry metadata, so it resolves without an adapter try."""
    body = _ok(app.test_client().get(f"{BASE}/validation/runs"))
    assert body["data"]["run_count"] == 24


def test_validation_run_list_revalidates_against_the_declared_schema(app):
    response = app.test_client().get(f"{BASE}/validation/runs")
    assert response.status_code == 200
    operations = [op for op in app.extensions["operation_catalog"].operations
                  if op.path == f"{BASE}/validation/runs"]
    assert operations and operations[0].operation_id == "SPEC06"
    operations[0].response_model.model_validate(response.json)
