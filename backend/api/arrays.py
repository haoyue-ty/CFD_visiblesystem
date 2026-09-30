"""ARRAY01: registered scientific arrays only.

The result/array pair must match a registry entry and the adapter owns decoding; there is
no user-supplied path, dtype, NPZ member or downsample parameter, and no free file read.
"""
from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import system_error
from backend.models import ApiEnvelope, ProjectInfo, ScientificArray, known
from backend.schemas.requests import ArrayQuery


def parse_array(path: dict[str, str], query: dict[str, list[str]]) -> dict:
    for key, values in query.items():
        if key not in ArrayQuery.model_fields:
            raise ValueError("Unknown query parameter")
        if len(values) != 1:
            raise ValueError("Duplicate single-value query parameter")
    payload = {name: path[name] for name in ("result_id", "array_id")}
    if "registry_revision" in query:
        payload["registry_revision"] = query["registry_revision"][0]
    return payload


def register_array_operations(catalog: OperationCatalog, project: ProjectInfo, service) -> None:
    def scientific_array(query: ArrayQuery, result_id: str, array_id: str):
        if query.registry_revision is not None and query.registry_revision != project.registry_revision:
            raise system_error("REVISION_UNAVAILABLE", "Requested registry revision is unavailable", status=409)
        array = service.load_array(query.result_id, query.array_id)
        # The response envelope carries the array's own ScientificResult, so a caller cannot
        # confuse the outer transport health with the scientific certification of the values.
        return ApiEnvelope[ScientificArray].model_validate({
            "schema_version": "1.0.0", "request_id": g.request_id,
            "registry_revision": known(project.registry_revision),
            "data_revision": known(project.data_revision),
            "availability": "AVAILABLE", "data": array, "issues": [],
        })

    catalog.register(Operation(
        method="GET", path="/api/v1/results/{result_id}/arrays/{array_id}", operation_id="ARRAY01",
        blueprint="scientific_arrays", service="ResultArrayService", request_model=ArrayQuery,
        response_model=ApiEnvelope[ScientificArray],
        documented_errors={400: ("INVALID_REQUEST",), 404: ("INVALID_RESULT_ID",),
                           405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE",),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "INTERNAL_ERROR"),
                           503: ("FEATURE_NOT_ENABLED",)},
        delivery_phase="Alpha", handler=scientific_array, request_parser=parse_array,
        description="Flat C-order array values for one registered result/array pair."))
