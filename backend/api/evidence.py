"""EVI02–EVI04: evidence detail, result provenance and public source-asset DTOs.

Evidence reads stay available even when numeric delivery is blocked by source drift:
a successful evidence load is not a certification that the result is displayable.
"""
from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import system_error
from backend.models import (ApiEnvelope, EvidenceRecord, ProjectInfo, ResultProvenance,
                            known)
from backend.schemas.requests import IdentityQuery, ProvenanceQuery, RegistryQuery


def _envelope(payload, project: ProjectInfo, response_model):
    return response_model.model_validate({
        "schema_version": "1.0.0", "request_id": g.request_id,
        "registry_revision": known(project.registry_revision),
        "data_revision": known(project.data_revision),
        "availability": "AVAILABLE", "data": payload, "issues": [],
    })


def _revision(query: RegistryQuery, project: ProjectInfo) -> None:
    if query.registry_revision is not None and query.registry_revision != project.registry_revision:
        raise system_error("REVISION_UNAVAILABLE", "Requested registry revision is unavailable", status=409)


def _path_parser(*path_names: str):
    def parse(path: dict[str, str], query: dict[str, list[str]]) -> dict:
        for key, values in query.items():
            if key != "registry_revision":
                raise ValueError("Unknown query parameter")
            if len(values) != 1:
                raise ValueError("Duplicate single-value query parameter")
        payload = {name: path[name] for name in path_names}
        if "registry_revision" in query:
            payload["registry_revision"] = query["registry_revision"][0]
        return payload

    return parse


def register_evidence_operations(catalog: OperationCatalog, project: ProjectInfo, service, allocation_service=None) -> None:
    def evidence_record(query: IdentityQuery, evidence_id: str):
        _revision(query, project)
        identity = query.evidence_id or evidence_id
        selected = allocation_service if allocation_service and allocation_service.owns_evidence(identity) else service
        return _envelope(selected.load_evidence(identity), project,
                         ApiEnvelope[EvidenceRecord])

    def provenance(query: ProvenanceQuery, result_id: str):
        _revision(query, project)
        selected = allocation_service if allocation_service and allocation_service.owns_result(query.result_id) else service
        return _envelope(selected.load_provenance(query.result_id), project,
                         ApiEnvelope[ResultProvenance])

    catalog.register(Operation(
        method="GET", path="/api/v1/evidence/{evidence_id}", operation_id="EVI02", blueprint="evidence",
        service="EvidenceService", request_model=IdentityQuery,
        response_model=ApiEnvelope[EvidenceRecord],
        documented_errors={400: ("INVALID_REQUEST",), 404: ("UNKNOWN_EVIDENCE_ID", "MISSING_ASSET"),
                           405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE",),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "SOURCE_ERROR", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ", "INTERNAL_ERROR"),
                           503: ("FEATURE_NOT_ENABLED",)},
        delivery_phase="Alpha", handler=evidence_record, request_parser=_path_parser("evidence_id"),
        description="Full method/config/assets/hashes/freeze/processing/verification evidence record."))
    catalog.register(Operation(
        method="GET", path="/api/v1/results/{result_id}/provenance", operation_id="EVI03",
        blueprint="evidence", service="EvidenceService", request_model=ProvenanceQuery,
        response_model=ApiEnvelope[ResultProvenance],
        documented_errors={400: ("INVALID_REQUEST",), 404: ("INVALID_RESULT_ID", "MISSING_ASSET"),
                           405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE",),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "SOURCE_ERROR", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ", "INTERNAL_ERROR"),
                           503: ("FEATURE_NOT_ENABLED",)},
        delivery_phase="Alpha", handler=provenance, request_parser=_path_parser("result_id"),
        description="Provenance for any scientific result, listing every contributing source reference."))
