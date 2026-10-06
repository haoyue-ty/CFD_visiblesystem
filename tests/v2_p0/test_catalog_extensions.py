"""Exercise future V2 transports without exposing placeholder product routes."""
import pytest
from datetime import date
from flask import Flask, Response, g
from openapi_spec_validator import validate
from pydantic import BaseModel, ConfigDict

from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import register_error_handlers
from backend.schemas.openapi import export_openapi


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    value: float


class Selector(BaseModel):
    run_id: str


class Reply(BaseModel):
    value: float


def make_operation(**updates):
    values = dict(method="POST", path="/api/v2/test", operation_id="TEST", blueprint="test",
                  service="test", request_model=None, request_body_model=Body,
                  response_model=Reply, success_status=202,
                  documented_errors={400: ("INVALID_REQUEST",), 415: ("UNSUPPORTED_MEDIA_TYPE",)},
                  delivery_phase="V2-P0-TEST", handler=lambda query, *, body: Reply(value=body.value))
    return Operation(**(values | updates))


def bind(operation):
    app = Flask(__name__)
    @app.before_request
    def identity():
        g.request_id = "catalog-test"
    register_error_handlers(app)
    catalog = OperationCatalog()
    catalog.register(operation)
    catalog.bind(app)
    return app.test_client(), catalog


def test_json_body_and_202_contract():
    client, catalog = bind(make_operation())
    response = client.post("/api/v2/test", json={"value": 1.5})
    assert response.status_code == 202 and response.json == {"value": 1.5}
    document = export_openapi(catalog)
    validate(document)
    entry = document["paths"]["/api/v2/test"]["post"]
    assert "parameters" not in entry
    assert entry["requestBody"]["required"] is True
    assert set(entry["responses"]) == {"202", "400", "415"}


def test_strict_json_body_preserves_json_specific_types():
    class JSONBody(BaseModel):
        model_config = ConfigDict(strict=True, extra="forbid")
        coordinates: tuple[float, float]
        observed_on: date

    def handler(query, *, body):
        assert body.coordinates == (1.0, 2.0) and body.observed_on == date(2026, 10, 2)
        return Reply(value=body.coordinates[0])

    client, catalog = bind(make_operation(request_body_model=JSONBody, handler=handler))
    response = client.post("/api/v2/test", json={"coordinates": [1.0, 2.0], "observed_on": "2026-10-02"})
    assert response.status_code == 202 and response.json == {"value": 1.0}
    validate(export_openapi(catalog))


@pytest.mark.parametrize("data,content_type,status", [
    ('{"value": 1}', "text/plain", 415),
    ('', "application/json", 400),
    ('{', "application/json", 400),
    ('null', "application/json", 400),
    ('[]', "application/json", 400),
    ('{"value":"1"}', "application/json", 400),
    ('{"value":NaN}', "application/json", 400),
    ('{"value":1e999}', "application/json", 400),
    ('{"value":1,"other":2}', "application/json", 400),
    ('{"value":1,"value":2}', "application/json", 400),
])
def test_body_rejected_before_handler(data, content_type, status):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid input reached handler")
    client, _ = bind(make_operation(handler=forbidden))
    response = client.post("/api/v2/test", data=data, content_type=content_type)
    assert response.status_code == status
    assert response.json["error"]["code"] == ("UNSUPPORTED_MEDIA_TYPE" if status == 415 else "INVALID_REQUEST")


def test_body_does_not_override_path_or_query():
    client, catalog = bind(make_operation(path="/api/v2/test/{run_id}", request_model=Selector,
        handler=lambda query, *, run_id, body: Reply(value=body.value if run_id == query.run_id else -1)))
    assert client.post("/api/v2/test/run-1", json={"value": 2}).status_code == 202
    assert client.post("/api/v2/test/run-1?run_id=run-2", json={"value": 2}).status_code == 400
    assert client.post("/api/v2/test/run-1", json={"value": 2, "run_id": "run-2"}).status_code == 400
    entry = export_openapi(catalog)["paths"]["/api/v2/test/{run_id}"]["post"]
    assert entry["parameters"][0]["in"] == "path"
    assert "requestBody" in entry


@pytest.mark.parametrize("media,payload", [("text/event-stream", "id: 1\ndata: queued\n\n"),
                                          ("text/html", "<html>report</html>")])
def test_text_response_is_not_json_serialized(media, payload):
    def handler(query):
        return Response(iter([payload]), mimetype=media)
    client, catalog = bind(make_operation(method="GET", request_body_model=None, response_model=None,
                                         success_status=200, response_media_type=media, handler=handler))
    response = client.get("/api/v2/test", buffered=False)
    assert response.status_code == 200 and response.mimetype == media
    assert response.get_data(as_text=True) == payload
    document = export_openapi(catalog)
    validate(document)
    assert document["paths"]["/api/v2/test"]["get"]["responses"]["200"]["content"][media]["schema"] == {"type": "string"}


def test_wrong_text_transport_is_a_server_error():
    client, _ = bind(make_operation(method="GET", request_body_model=None, response_model=None,
        response_media_type="text/event-stream", handler=lambda query: {"value": 2}))
    assert client.get("/api/v2/test").status_code == 500


@pytest.mark.parametrize("media,status", [("text/html", 200), ("text/event-stream", 500)])
def test_text_mime_or_error_status_cannot_be_promoted_to_success(media, status):
    client, _ = bind(make_operation(method="GET", request_body_model=None, response_model=None,
        success_status=200, response_media_type="text/event-stream",
        handler=lambda query: Response("failure", mimetype=media, status=status)))
    response = client.get("/api/v2/test")
    assert response.status_code == 500 and response.json["error"]["code"] == "INTERNAL_ERROR"


@pytest.mark.parametrize("updates", [
    {"success_status": 204}, {"success_status": 400}, {"success_status": 4000}, {"success_status": 202.0},
    {"response_model": None}, {"response_media_type": "text/html"},
    {"response_media_type": "image/png"}, {"method": "GET"},
    {"documented_errors": {202: ("INVALID_REQUEST",)}},
    {"path": "/api/v2/test/{body}"},
])
def test_invalid_operation_metadata_fails_at_registration(updates):
    with pytest.raises(ValueError):
        OperationCatalog().register(make_operation(**updates))


def test_v1_openapi_and_types_remain_identical(app):
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert export_openapi(app.extensions["operation_catalog"]) == json.loads(
        (root / "config/openapi.json").read_text(encoding="utf-8"))
    # P1 adds product routes; the saved combined contract must remain reproducible.
    assert all(op.error_response_model is None for op in app.extensions["operation_catalog"].operations
               if op.path.startswith("/api/v1/"))
