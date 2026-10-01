"""REG01–REG04: experiment registry metadata.

Blueprint → Service → adapter. This module never opens a scientific file and never
assembles a source path; registry selection stays inside the adapter seam.
"""
from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import missing_resource, system_error
from backend.models import (ApiEnvelope, CapabilityList, ConfigList, Experiment,
                            ExperimentList, ProjectInfo, known, unresolved)
from backend.schemas.requests import ExperimentPath, RegistryQuery


def envelope(data, project: ProjectInfo, response_model, *, availability: str = "AVAILABLE", issues=None):
    """Bind data into the ApiEnvelope variant matching the declared response model."""
    return response_model.model_validate({
        "schema_version": "1.0.0", "request_id": g.request_id,
        "registry_revision": known(project.registry_revision),
        "data_revision": known(project.data_revision),
        "availability": availability, "data": data, "issues": issues or [],
    })


def check_registry_revision(query: RegistryQuery, project: ProjectInfo) -> None:
    if query.registry_revision is not None and query.registry_revision != project.registry_revision:
        raise system_error("REVISION_UNAVAILABLE", "Requested registry revision is unavailable", status=409)


def require_delivered(experiment_id: str) -> None:
    """Only Case8 is IMPLEMENTED in the first slice; other families stay PLANNED (503)."""
    if experiment_id != "case8":
        raise system_error("FEATURE_NOT_ENABLED",
                           "This experiment is not delivered in the Case8 slice", status=503)


def register_registry_operations(catalog: OperationCatalog, project: ProjectInfo, service, cylinder_service=None) -> None:
    def delivered(identity):
        if identity not in {ref.experiment_id for ref in project.experiments}:
            raise missing_resource("UNKNOWN_EXPERIMENT", "Unknown experiment identity",
                                   resource_type="experiment", identity=unresolved("Not present in the registry index"))
        if identity == "cylinder" and cylinder_service is not None:
            return cylinder_service
        require_delivered(identity)
        return service

    def experiments(query: RegistryQuery):
        check_registry_revision(query, project)
        items = [delivered(ref.experiment_id).describe_experiment() if ref.experiment_id in ("case8", "cylinder") and ref.delivery_status == "IMPLEMENTED" else Experiment.model_validate({
            "schema_version": "1.0.0", "id": ref.experiment_id, "name": ref.name,
            "scientific_family": ref.experiment_id, "description": f"{ref.name} experiment",
            "capabilities": [], "available_configs": [], "status": "UNSUPPORTED",
            "delivery_status": ref.delivery_status, "limitations": [],
            "evidence_refs": [], "related_experiment_ids": [],
        }) for ref in project.experiments]
        return envelope(ExperimentList(items=items), project, ApiEnvelope[ExperimentList])

    def experiment(query: ExperimentPath, experiment_id: str):
        check_registry_revision(query, project)
        # Contract section 5 precedence: identity 404 precedes the delivery-status 503,
        # otherwise an undelivered family would masquerade as an unknown one.
        if experiment_id not in {ref.experiment_id for ref in project.experiments}:
            raise missing_resource("UNKNOWN_EXPERIMENT", "Unknown experiment identity",
                                   resource_type="experiment",
                                   identity=unresolved("Not present in the registry index"))
        return envelope(delivered(experiment_id).describe_experiment(), project, ApiEnvelope[Experiment])

    def configs(query: ExperimentPath, experiment_id: str):
        check_registry_revision(query, project)
        return envelope(delivered(experiment_id).list_configs(), project, ApiEnvelope[ConfigList])

    def capabilities(query: ExperimentPath, experiment_id: str):
        check_registry_revision(query, project)
        return envelope(delivered(experiment_id).describe_capabilities(), project, ApiEnvelope[CapabilityList])

    catalog.register(Operation(
        method="GET", path="/api/v1/experiments", operation_id="REG01", blueprint="system_registry",
        service="RegistryService", request_model=RegistryQuery, response_model=ApiEnvelope[ExperimentList],
        documented_errors={400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE",),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR")},
        delivery_phase="Alpha", handler=experiments,
        description="Canonical experiment metadata including delivered Case8 and Cylinder."))
    catalog.register(Operation(
        method="GET", path="/api/v1/experiments/{experiment_id}", operation_id="REG02", blueprint="system_registry",
        service="RegistryService", request_model=ExperimentPath, response_model=ApiEnvelope[Experiment],
        documented_errors={400: ("INVALID_REQUEST",), 404: ("UNKNOWN_EXPERIMENT",), 405: ("METHOD_NOT_ALLOWED",),
                           409: ("REVISION_UNAVAILABLE",), 500: ("CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR"),
                           503: ("FEATURE_NOT_ENABLED",)},
        delivery_phase="Alpha", handler=experiment,
        description="Registered experiment metadata for a delivered family."))
    catalog.register(Operation(
        method="GET", path="/api/v1/experiments/{experiment_id}/configs", operation_id="REG03",
        blueprint="system_registry", service="RegistryService", request_model=ExperimentPath,
        response_model=ApiEnvelope[ConfigList],
        documented_errors={400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE",),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR"), 503: ("FEATURE_NOT_ENABLED",)},
        delivery_phase="Alpha", handler=configs, description="Registered configs for a delivered experiment."))
    catalog.register(Operation(
        method="GET", path="/api/v1/experiments/{experiment_id}/capabilities", operation_id="REG04",
        blueprint="system_registry", service="RegistryService", request_model=ExperimentPath,
        response_model=ApiEnvelope[CapabilityList],
        documented_errors={400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE",),
                           500: ("CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR"), 503: ("FEATURE_NOT_ENABLED",)},
        delivery_phase="Alpha", handler=capabilities,
        description="Capability-driven tabs and controls supplied by the registry, not hard-coded clients."))
