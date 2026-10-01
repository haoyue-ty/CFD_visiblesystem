import hashlib
import json
from pathlib import Path, PureWindowsPath

import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

from backend import create_app
from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import DomainError
from backend.core.settings import Settings
from backend.models import ApiEnvelope, CapabilityList, ConfigList, FailedEnvelope, ProjectInfo
from backend.schemas.openapi import export_openapi
from backend.schemas.requests import RegistryQuery


def test_system_envelope(app):
    response = app.test_client().get('/api/v1/system', headers={"X-Request-ID": "untrusted"})
    assert response.status_code == 200
    envelope = ApiEnvelope[ProjectInfo].model_validate_json(response.data)
    assert envelope.root.request_id == response.headers["X-Request-ID"] != "untrusted"
    assert envelope.root.data.account_extension.enabled is False
    assert all(item.delivery_status == ("IMPLEMENTED" if item.experiment_id == "case8" else "PLANNED") for item in envelope.root.data.experiments)


@pytest.mark.parametrize("url,status,code", [
    ("/api/v1/system?unknown=x", 400, "INVALID_REQUEST"),
    ("/api/v1/system?registry_revision=a&registry_revision=b", 400, "INVALID_REQUEST"),
    ("/api/v1/system?registry_revision=missing", 409, "REVISION_UNAVAILABLE"),
    ("/api/v1/not-a-route", 404, "API_ROUTE_NOT_FOUND"),
    ("/api/not-a-route", 404, "API_ROUTE_NOT_FOUND"),
])
def test_safe_errors(app, url, status, code):
    response = app.test_client().get(url)
    assert response.status_code == status
    body = FailedEnvelope.model_validate_json(response.data)
    assert body.error.code == code
    assert "data" not in response.json
    assert "D:\\" not in response.text


def test_method_error_keeps_allow(app):
    response = app.test_client().post("/api/v1/system")
    assert response.status_code == 405
    assert response.json["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["Allow"]


def test_openapi_valid_and_all_references_resolve(app):
    catalog = app.extensions["operation_catalog"]
    document = export_openapi(catalog)
    validate(document)
    assert app.test_client().get("/api/v1/openapi.json").json == document
    assert document["openapi"] == "3.1.0"
    assert "availability" not in document

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "$ref":
                    assert item.startswith("#/components/schemas/")
                    assert item.rsplit("/", 1)[-1] in document["components"]["schemas"]
                elif key == "$defs":
                    pytest.fail("Unconverted $defs")
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(document)
    response = app.test_client().get("/api/v1/system").json
    ref = document["paths"]["/api/v1/system"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    Draft202012Validator({**ref, "components": document["components"]}).validate(response)
    catalog.assert_routes(app)


class FakeAdapter:
    """Software-only fake: no scientific file I/O and no fabricated numeric result."""
    def list_configs(self):
        return ConfigList(experiment_id="case8", items=[])

    def describe_capabilities(self):
        return CapabilityList(experiment_id="case8", items=[])


def test_fake_adapter_injection_and_independent_apps():
    first = create_app(case8_adapter=FakeAdapter())
    second = create_app(case8_adapter=None)
    assert first.extensions["case8_service"].list_configs().experiment_id == "case8"
    assert first.extensions["case8_service"].describe_capabilities().items == []
    with pytest.raises(DomainError) as error:
        second.extensions["case8_service"].list_configs()
    assert error.value.status == 503 and error.value.body.code == "FEATURE_NOT_ENABLED"


def test_window2_can_register_api_against_fake_adapter():
    def configure(catalog, service):
        catalog.register(Operation(method="GET", path="/api/v1/test/configs", operation_id="TEST_CONFIGS",
                                   blueprint="test_case8", service="Case8Service", request_model=RegistryQuery,
                                   response_model=ConfigList, documented_errors={}, delivery_phase="TEST",
                                   handler=lambda query: service.list_configs()))
    app = create_app(case8_adapter=FakeAdapter(), configure_catalog=configure)
    assert app.test_client().get("/api/v1/test/configs").json == {"experiment_id": "case8", "items": []}
    validate(export_openapi(app.extensions["operation_catalog"]))


@pytest.mark.parametrize("url,expected", [
    ("/api/v1/test/configs/D_u/snapshots/1?offset=2&series=a&series=b", 200),
    ("/api/v1/test/configs/D_u/snapshots/0", 400),
    ("/api/v1/test/configs/D_u/snapshots/1?offset=1&offset=2", 400),
    ("/api/v1/test/configs/D_u/snapshots/1?unknown=1", 400),
    ("/api/v1/test/configs/D_u/snapshots/1?snapshot_index=2", 400),
])
def test_catalog_explicit_numeric_and_repeated_parser(url, expected):
    from backend.models import ID, NonNegativeInt, PositiveInt
    class Selectors(RegistryQuery):
        config_id: ID
        snapshot_index: PositiveInt
        offset: NonNegativeInt = 0
        series: list[ID] = []

    def parse(path, query):
        for key, values in query.items():
            if key != "series" and len(values) != 1:
                raise ValueError("Duplicate single-value query")
        payload = {**path, "snapshot_index": int(path["snapshot_index"]),
                   "offset": int(query.get("offset", ["0"])[0]), "series": query.get("series", [])}
        if "registry_revision" in query:
            payload["registry_revision"] = query["registry_revision"][0]
        return payload

    def configure(catalog, service):
        catalog.register(Operation(method="GET", path="/api/v1/test/configs/{config_id}/snapshots/{snapshot_index}",
                                   operation_id="TEST_SELECTORS", blueprint="selectors", service="test",
                                   request_model=Selectors, response_model=ConfigList, documented_errors={400: ("INVALID_REQUEST",)},
                                   delivery_phase="TEST", request_parser=parse, handler=lambda query, **path: service.list_configs()))
    app = create_app(case8_adapter=FakeAdapter(), configure_catalog=configure)
    assert app.test_client().get(url).status_code == expected
    validate(export_openapi(app.extensions["operation_catalog"]))


def test_adapter_bad_output_is_not_client_400():
    class BadAdapter:
        def list_configs(self):
            return {"experiment_id": "case8", "items": [], "absolute_source_path": "hidden"}
    def configure(catalog, service):
        catalog.register(Operation(method="GET", path="/api/v1/test/configs", operation_id="TEST_BAD",
                                   blueprint="bad", service="Case8Service", request_model=None,
                                   response_model=ConfigList, documented_errors={}, delivery_phase="TEST",
                                   handler=lambda query: service.list_configs()))
    app = create_app(case8_adapter=BadAdapter(), configure_catalog=configure)
    response = app.test_client().get("/api/v1/test/configs")
    assert response.status_code == 500
    assert response.json["error"]["code"] == "CANONICAL_SCHEMA_MISMATCH"
    assert "hidden" not in response.text


def test_component_conflicts_fail_instead_of_overwriting(app):
    from pydantic import create_model
    first = create_model("Conflict", first=(str, ...))
    second = create_model("Conflict", second=(str, ...))
    catalog = OperationCatalog()
    for index, model in enumerate((first, second)):
        catalog.register(Operation(method="GET", path=f"/api/v1/conflict{index}", operation_id=f"CONFLICT{index}",
                                   blueprint="test", service="test", request_model=None, response_model=model,
                                   documented_errors={}, delivery_phase="TEST", handler=lambda query: {}))
    with pytest.raises(ValueError, match="Conflicting"):
        export_openapi(catalog)


def test_frozen_docs_hashes_unchanged():
    freeze = json.loads(Path("docs/PHASE4_TECHNICAL_FOUNDATION_FREEZE.json").read_text(encoding="utf-8"))
    assert (freeze["status"], freeze["version"]) == ("FROZEN", "1.0.1")
    for item in freeze["documents"]:
        document = Path("docs") / PureWindowsPath(item["path"]).name
        assert hashlib.sha256(document.read_bytes()).hexdigest() == item["sha256"].lower()


def test_accounts_cannot_be_enabled():
    with pytest.raises(ValueError, match="disabled"):
        create_app(Settings(enable_accounts=True))


def test_factory_never_opens_configured_scientific_paths():
    app = create_app(Settings(scientific_data_root="Z:/must-not-read", inventory_path="Z:/must-not-read/inventory.json",
                              canonical_registry_path="Z:/must-not-read/registry.json"))
    assert app.test_client().get("/api/v1/system").status_code == 200
