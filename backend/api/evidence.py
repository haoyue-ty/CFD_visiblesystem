"""EVI02–EVI04: evidence detail, result provenance and public source-asset DTOs.

Evidence reads stay available even when numeric delivery is blocked by source drift:
a successful evidence load is not a certification that the result is displayable.
"""
from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import system_error
from backend.models import (ApiEnvelope, EvidenceRecord, EvidenceIndex, SourceAsset, ProjectInfo, ResultProvenance,
                            known)
from backend.api.case8 import make_parser
from backend.schemas.requests import EvidenceQuery, IdentityQuery, ProvenanceQuery, RegistryQuery


def _envelope(payload, project: ProjectInfo, response_model):
    provenance = (payload.provenance if isinstance(payload, ResultProvenance) else
                  payload.result_contexts[0].provenance if isinstance(payload, EvidenceRecord) and payload.result_contexts else None)
    return response_model.model_validate({
        "schema_version": "1.0.0", "request_id": g.request_id,
        "registry_revision": known(provenance.registry_revision if provenance else project.registry_revision),
        "data_revision": known(provenance.data_revision if provenance else project.data_revision),
        "availability": "AVAILABLE", "data": payload, "issues": [],
    })


def _revision(query: RegistryQuery, project: ProjectInfo, service, identity) -> None:
    revision = getattr(service, "revision_for", lambda _: project.registry_revision)(identity)
    if query.registry_revision is not None and query.registry_revision != revision:
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


def register_evidence_operations(catalog: OperationCatalog, project: ProjectInfo, service, allocation_service=None, evidence_service=None) -> None:
    def evidence_record(query: IdentityQuery, evidence_id: str):
        identity = query.evidence_id or evidence_id
        selected = evidence_service if evidence_service and evidence_service.owns_evidence(identity) else allocation_service if allocation_service and allocation_service.owns_evidence(identity) else service
        _revision(query, project, selected, identity)
        return _envelope(selected.load_evidence(identity), project,
                         ApiEnvelope[EvidenceRecord])

    def provenance(query: ProvenanceQuery, result_id: str):
        selected = evidence_service if evidence_service and evidence_service.owns_result(query.result_id) else allocation_service if allocation_service and allocation_service.owns_result(query.result_id) else service
        _revision(query, project, selected, query.result_id)
        return _envelope(selected.load_provenance(query.result_id), project,
                         ApiEnvelope[ResultProvenance])

    def index(query: EvidenceQuery):
        if query.registry_revision is not None and query.registry_revision != evidence_service.registry_revision:
            raise system_error("REVISION_UNAVAILABLE", "Requested evidence registry revision is unavailable", status=409)
        center_project = project.model_copy(update={"registry_revision": evidence_service.registry_revision,
                                                    "data_revision": evidence_service.data_revision})
        return _envelope(evidence_service.list_evidence(query), center_project, ApiEnvelope[EvidenceIndex])

    def asset(query: IdentityQuery, asset_id: str):
        if query.registry_revision is not None and query.registry_revision != evidence_service.registry_revision:
            raise system_error("REVISION_UNAVAILABLE", "Requested evidence registry revision is unavailable", status=409)
        center_project = project.model_copy(update={"registry_revision": evidence_service.registry_revision,
                                                    "data_revision": evidence_service.data_revision})
        return _envelope(evidence_service.load_asset(asset_id), center_project, ApiEnvelope[SourceAsset])

    if evidence_service is not None:
        catalog.register(Operation(
            method="GET", path="/api/v1/evidence", operation_id="EVI01", blueprint="evidence",
            service="EvidenceService", request_model=EvidenceQuery, response_model=ApiEnvelope[EvidenceIndex],
            documented_errors={400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE",),
                               500: ("CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR")}, delivery_phase="Alpha",
            handler=index, request_parser=make_parser(EvidenceQuery, integers=("offset", "limit"), optional=("section", "experiment_id", "status")),
            description="Server-filtered CURRENT/GAPS/HISTORY evidence metadata; default limit 50, maximum 200. Frozen status filter is VerificationStatus; no arbitrary query fields."))
        catalog.register(Operation(
            method="GET", path="/api/v1/assets/{asset_id}", operation_id="EVI04", blueprint="evidence",
            service="EvidenceService", request_model=IdentityQuery, response_model=ApiEnvelope[SourceAsset],
            documented_errors={400: ("INVALID_REQUEST",), 404: ("UNKNOWN_ASSET_ID",), 405: ("METHOD_NOT_ALLOWED",),
                               409: ("REVISION_UNAVAILABLE",), 500: ("CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR")},
            delivery_phase="Alpha", handler=asset, request_parser=_path_parser("asset_id"),
            description="Registered public source-asset explanation and live hash facts. No file contents, locator or download."))

    catalog.register(Operation(
        method="GET", path="/api/v1/evidence/{evidence_id}", operation_id="EVI02", blueprint="evidence",
        service="EvidenceService", request_model=IdentityQuery,
        response_model=ApiEnvelope[EvidenceRecord],
        documented_errors={400: ("INVALID_REQUEST",), 404: ("UNKNOWN_EVIDENCE_ID", "MISSING_ASSET", "MISSING_SCIENTIFIC_ASSET"),
                           405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ"),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "SOURCE_ERROR", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ", "INTERNAL_ERROR"),
                           503: ("FEATURE_NOT_ENABLED",)},
        delivery_phase="Alpha", handler=evidence_record, request_parser=_path_parser("evidence_id"),
        description="Full method/config/assets/hashes/freeze/processing/verification evidence record."))
    catalog.register(Operation(
        method="GET", path="/api/v1/results/{result_id}/provenance", operation_id="EVI03",
        blueprint="evidence", service="EvidenceService", request_model=ProvenanceQuery,
        response_model=ApiEnvelope[ResultProvenance],
        documented_errors={400: ("INVALID_REQUEST",), 404: ("INVALID_RESULT_ID", "MISSING_ASSET", "MISSING_SCIENTIFIC_ASSET"),
                           405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ"),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "SOURCE_ERROR", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ", "INTERNAL_ERROR"),
                           503: ("FEATURE_NOT_ENABLED",)},
        delivery_phase="Alpha", handler=provenance, request_parser=_path_parser("result_id"),
        description="Provenance for any scientific result, listing every contributing source reference."))
