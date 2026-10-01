"""CONTENT01–03 only; qualitative states are interpreted by the frontend."""
import re

from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import system_error
from backend.models import ApiEnvelope, known
from backend.models.content import MechanismContent, SceneList, ScenePreset
from backend.schemas.requests import RegistryQuery, SceneQuery
from backend.services.content import ContentService


def _scene_parser(path: dict[str, str], query: dict[str, list[str]]) -> dict:
    # Integer identity on the wire; no float, sign or whitespace aliases.
    if not re.fullmatch(r"[1-7]", path["scene_id"]):
        raise ValueError("Scene identity must be one of 1..7")
    if set(query) - {"registry_revision"} or any(len(values) != 1 for values in query.values()):
        raise ValueError("Invalid query parameters")
    return {"scene_id": int(path["scene_id"]),
            **{name: values[0] for name, values in query.items()}}


def register_content_operations(catalog: OperationCatalog, service: ContentService) -> None:
    def envelope(query, payload_type, load):
        if query.registry_revision is not None and query.registry_revision != service.registry_revision:
            raise system_error("REVISION_UNAVAILABLE", "Requested content revision is unavailable", status=409)
        return ApiEnvelope[payload_type].model_validate({
            "schema_version": "1.0.0", "request_id": g.request_id,
            "registry_revision": known(service.registry_revision), "data_revision": known(service.data_revision),
            "availability": "AVAILABLE", "data": load(), "issues": [],
        })

    def scene(query: SceneQuery, scene_id: str):
        return envelope(query, ScenePreset, lambda: service.get_scene(query.scene_id))

    errors = {400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",),
              409: ("REVISION_UNAVAILABLE",),
              500: ("CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR")}
    for path, identity, request_model, response_model, handler, parser, description in (
        ("/api/v1/explore/scenes", "CONTENT01", RegistryQuery, SceneList,
         lambda query: envelope(query, SceneList, service.list_scenes), None,
         "All seven frozen scenes in order; child resource availability never removes scene metadata."),
        ("/api/v1/explore/scenes/{scene_id}", "CONTENT02", SceneQuery, ScenePreset,
         scene, _scene_parser,
         "Frozen scene 1..7 with real registered targets; any other scene identity is 400 INVALID_REQUEST."),
        ("/api/v1/mechanism", "CONTENT03", RegistryQuery, MechanismContent,
         lambda query: envelope(query, MechanismContent, service.load_mechanism), None,
         "SCHEMATIC mechanism, including combination and entropy-variable mapping; STRICT_1D/WEAKLY_2D "
         "are frontend display states. No epsilon query, state-vector input or numerical flux evaluation."),
    ):
        catalog.register(Operation(
            method="GET", path=path, operation_id=identity, blueprint="system_registry",
            service="ContentService", request_model=request_model, response_model=ApiEnvelope[response_model],
            documented_errors=errors, delivery_phase="Full", handler=handler,
            request_parser=parser, description=description,
        ))
