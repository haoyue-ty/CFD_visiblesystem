"""Window 3 allocation API acceptance: valid / missing / unsupported (+ source failure).

Every success response must carry ``representation_type`` so the frontend never guesses
face vs cell from array shape or field identity.
"""
import pytest

from backend import create_app
from fake_allocation_adapter import FakeAllocationAdapter

BASE = "/api/v1/allocations"
RESULT_ID = FakeAllocationAdapter.FACE_RESULT_ID

ALLOCATION_OPERATION_IDS = {"ALLOC01", "ALLOC02", "ALLOC03", "ALLOC04"}


def _failure(response, status: int, code: str):
    assert response.status_code == status, response.get_data(as_text=True)
    assert response.headers["Cache-Control"] == "no-store"
    body = response.json
    assert body["availability"] in {"MISSING", "UNSUPPORTED", "ERROR"}
    assert body["error"]["code"] == code
    return body


# --- registration / OpenAPI -------------------------------------------------------

def test_four_allocation_operations_are_registered(app):
    ids = {op.operation_id for op in app.extensions["operation_catalog"].operations}
    assert ALLOCATION_OPERATION_IDS <= ids
    assert "/api/v1/allocations/comparison" in {
        op.path for op in app.extensions["operation_catalog"].operations}


def test_allocation_operations_are_in_the_exported_openapi(app):
    document = app.test_client().get("/api/v1/openapi.json").json
    documented = {entry["operationId"] for path in document["paths"].values()
                  for entry in path.values()}
    assert ALLOCATION_OPERATION_IDS <= documented


# --- valid ------------------------------------------------------------------------

def test_metadata_valid_returns_representation_type(client):
    response = client.get(f"{BASE}/{RESULT_ID}/metadata")
    assert response.status_code == 200
    body = response.json
    assert body["availability"] == "AVAILABLE"
    assert body["data"]["representation_type"] == "FACE_FIELD"
    assert body["data"]["wire_representation"] == "FACE_FIELD"


def test_array_valid_returns_representation_type(client):
    response = client.get(f"{BASE}/{RESULT_ID}/arrays/{FakeAllocationAdapter.ARRAY_ID}")
    assert response.status_code == 200
    body = response.json
    assert body["availability"] == "AVAILABLE"
    assert body["data"]["representation_type"] == "FACE_FIELD"


def test_summary_valid_returns_representation_type(client):
    response = client.get(f"{BASE}/{RESULT_ID}/summary")
    assert response.status_code == 200
    body = response.json
    assert body["availability"] == "AVAILABLE"
    assert body["data"]["measure"]["includes_spatial_measure"] is False


def test_comparison_valid_returns_representation_type(client):
    response = client.get(f"{BASE}/comparison", query_string={"experiment_id": "gate"})
    assert response.status_code == 200
    body = response.json
    assert body["availability"] == "AVAILABLE"
    assert body["data"]["representation_type"] == "CELL_FIELD"
    assert body["data"]["entries"][0]["representation_type"] == "CELL_FIELD"


# --- missing ----------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    f"{BASE}/{RESULT_ID}/metadata",
    f"{BASE}/{RESULT_ID}/arrays/{FakeAllocationAdapter.ARRAY_ID}",
    f"{BASE}/{RESULT_ID}/summary",
])
def test_missing_asset_is_a_typed_404(path):
    client = create_app(allocation_adapter=FakeAllocationAdapter("missing")).test_client()
    body = _failure(client.get(path), 404, "MISSING_ASSET")
    assert body["error"]["domain"] == "SCIENTIFIC"


def test_missing_asset_on_comparison():
    client = create_app(allocation_adapter=FakeAllocationAdapter("missing")).test_client()
    _failure(client.get(f"{BASE}/comparison", query_string={"experiment_id": "gate"}),
             404, "MISSING_ASSET")


# --- unsupported ------------------------------------------------------------------

def test_unsupported_representation_is_a_typed_422():
    client = create_app(allocation_adapter=FakeAllocationAdapter("unsupported")).test_client()
    body = _failure(client.get(f"{BASE}/{RESULT_ID}/metadata"), 422, "UNSUPPORTED_REPRESENTATION")
    assert body["error"]["domain"] == "SCIENTIFIC"


def test_unsupported_representation_on_array_summary_and_comparison():
    client = create_app(allocation_adapter=FakeAllocationAdapter("unsupported")).test_client()
    _failure(client.get(f"{BASE}/{RESULT_ID}/arrays/{FakeAllocationAdapter.ARRAY_ID}"),
             422, "UNSUPPORTED_REPRESENTATION")
    _failure(client.get(f"{BASE}/{RESULT_ID}/summary"), 422, "UNSUPPORTED_REPRESENTATION")
    _failure(client.get(f"{BASE}/comparison", query_string={"experiment_id": "gate"}),
             422, "UNSUPPORTED_REPRESENTATION")


# --- source failure ---------------------------------------------------------------

def test_source_error_is_a_typed_500():
    client = create_app(allocation_adapter=FakeAllocationAdapter("source")).test_client()
    _failure(client.get(f"{BASE}/{RESULT_ID}/metadata"), 500, "SOURCE_ERROR")


# --- transport hygiene ------------------------------------------------------------

def test_unknown_query_parameter_is_rejected():
    client = create_app(allocation_adapter=FakeAllocationAdapter()).test_client()
    response = client.get(f"{BASE}/{RESULT_ID}/metadata", query_string={"guess": "face"})
    _failure(response, 400, "INVALID_REQUEST")


def test_undelivered_adapter_reports_feature_not_enabled():
    client = create_app(allocation_adapter=None).test_client()
    _failure(client.get(f"{BASE}/{RESULT_ID}/metadata"), 503, "FEATURE_NOT_ENABLED")


def test_revision_mismatch_is_rejected():
    from backend import create_app as _create
    app = _create(allocation_adapter=FakeAllocationAdapter())
    client = app.test_client()
    response = client.get(f"{BASE}/{RESULT_ID}/metadata",
                          query_string={"registry_revision": "some-other-rev"})
    _failure(response, 409, "REVISION_UNAVAILABLE")
