from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import system_error
from backend.models import ApiEnvelope, ProjectInfo, known
from backend.schemas.openapi import OpenAPIDocument, export_openapi
from backend.schemas.requests import RegistryQuery


def register_system_operations(catalog: OperationCatalog, project: ProjectInfo) -> None:
    def system(query: RegistryQuery):
        if query.registry_revision is not None and query.registry_revision != project.registry_revision:
            raise system_error("REVISION_UNAVAILABLE", "Requested registry revision is unavailable", status=409)
        return ApiEnvelope[ProjectInfo].model_validate({
            "schema_version": "1.0.0", "request_id": g.request_id,
            "registry_revision": known(project.registry_revision), "data_revision": known(project.data_revision),
            "availability": "AVAILABLE", "data": project, "issues": [],
        })

    catalog.register(Operation(
        method="GET", path="/api/v1/system", operation_id="SYS01", blueprint="system_registry",
        service="RegistryService", request_model=RegistryQuery, response_model=ApiEnvelope[ProjectInfo],
        documented_errors={400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE",),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR")},
        delivery_phase="Alpha", handler=system, description="Project metadata and current experiment delivery status; accounts disabled.",
    ))
    catalog.register(Operation(
        method="GET", path="/api/v1/openapi.json", operation_id="DOC01", blueprint="system_registry",
        service="ContractExporter", request_model=None, response_model=OpenAPIDocument,
        documented_errors={400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",), 500: ("INTERNAL_ERROR",)},
        delivery_phase="Alpha", handler=lambda query: export_openapi(catalog), description="Native OpenAPI 3.1 document, without ApiEnvelope.",
    ))
