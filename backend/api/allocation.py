"""ALLOC01-ALLOC04: allocation metadata, array, summary and comparison.

Blueprint -> AllocationService -> AllocationAdapterProtocol -> controlled registry
-> READ_ONLY source. Nothing here opens a source, infers face vs cell, or accepts a
user-supplied path/dtype/member.

Every allocation response carries ``representation_type`` so the frontend never has
to guess whether it is looking at a native face map or an integrated cell map.
"""
from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.api.case8 import make_parser
from backend.core.errors import system_error
from backend.models import ApiEnvelope, ProjectInfo, known
from backend.models.allocation import (AllocationArrayResponse, AllocationComparison,
                                       AllocationMetadata, AllocationSummary)
from backend.schemas.requests import (AllocationArrayQuery, AllocationComparisonQuery,
                                      AllocationQuery, RegistryQuery)

ALLOCATION_BASE = "/api/v1/allocations"


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


def register_allocation_operations(catalog: OperationCatalog, project: ProjectInfo, service) -> None:
    def metadata(query: AllocationQuery, result_id: str):
        _revision(query, project)
        return _envelope(service.describe_capability(result_id), project,
                         ApiEnvelope[AllocationMetadata])

    def array(query: AllocationArrayQuery, result_id: str, array_id: str):
        _revision(query, project)
        return _envelope(service.load_array_view(result_id, array_id), project,
                         ApiEnvelope[AllocationArrayResponse])

    def summary(query: AllocationQuery, result_id: str):
        _revision(query, project)
        return _envelope(service.load_summary_metrics(result_id), project,
                         ApiEnvelope[AllocationSummary])

    def comparison(query: AllocationComparisonQuery):
        _revision(query, project)
        return _envelope(service.load_comparison(query.experiment_id,
                                                representation_type=query.representation_type),
                         project, ApiEnvelope[AllocationComparison])

    common_errors = {
        400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",),
        404: ("MISSING_ASSET", "INVALID_RESULT_ID"),
        409: ("REVISION_UNAVAILABLE",),
        422: ("UNSUPPORTED_REPRESENTATION", "UNSUPPORTED_COMBINATION"),
        500: ("SOURCE_ERROR", "CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR"),
        503: ("FEATURE_NOT_ENABLED",),
    }

    allocation_parser = make_parser(AllocationQuery)
    array_parser = make_parser(AllocationArrayQuery)
    comparison_parser = make_parser(AllocationComparisonQuery,
                                    optional=("experiment_id", "representation_type"))

    catalog.register(Operation(
        method="GET", path=f"{ALLOCATION_BASE}/{{result_id}}/metadata", operation_id="ALLOC01",
        blueprint="allocation", service="AllocationService", request_model=AllocationQuery,
        response_model=ApiEnvelope[AllocationMetadata], documented_errors=common_errors,
        delivery_phase="Alpha", handler=metadata, request_parser=allocation_parser,
        description="Registered allocation identity, measure, convention and mask refs; no values."))
    catalog.register(Operation(
        method="GET", path=f"{ALLOCATION_BASE}/{{result_id}}/arrays/{{array_id}}", operation_id="ALLOC02",
        blueprint="allocation", service="AllocationService", request_model=AllocationArrayQuery,
        response_model=ApiEnvelope[AllocationArrayResponse], documented_errors=common_errors,
        delivery_phase="Alpha", handler=array, request_parser=array_parser,
        description="Flat C-order values for one allocation field, with its representation_type."))
    catalog.register(Operation(
        method="GET", path=f"{ALLOCATION_BASE}/{{result_id}}/summary", operation_id="ALLOC03",
        blueprint="allocation", service="AllocationService", request_model=AllocationQuery,
        response_model=ApiEnvelope[AllocationSummary], documented_errors=common_errors,
        delivery_phase="Alpha", handler=summary, request_parser=allocation_parser,
        description="Budget/inside/outside summary, measure and cumulative curve slot."))
    catalog.register(Operation(
        method="GET", path=f"{ALLOCATION_BASE}/comparison", operation_id="ALLOC04",
        blueprint="allocation", service="AllocationService", request_model=AllocationComparisonQuery,
        response_model=ApiEnvelope[AllocationComparison], documented_errors=common_errors,
        delivery_phase="Alpha", handler=comparison, request_parser=comparison_parser,
        description="Shared extent/colour basis and per-variant allocation refs; no normalised values."))
