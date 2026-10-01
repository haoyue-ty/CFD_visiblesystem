"""CMP01: frozen server-side comparison; registry configurations only."""
from backend.api.case8 import make_parser
from backend.api.catalog import Operation
from backend.api.registry import check_registry_revision, envelope
from backend.models import ApiEnvelope
from backend.models.crossflow import CrossFlowComparison
from backend.schemas.requests import ComparisonQuery


def register_crossflow_operations(catalog, project, service):
    def comparison(query):
        check_registry_revision(query, project)
        value, issues = service.load_comparison(query.case8_config, query.cylinder_config)
        return envelope(value, project, ApiEnvelope[CrossFlowComparison],
                        availability="PARTIAL" if issues else "AVAILABLE", issues=issues)

    catalog.register(Operation(method="GET", path="/api/v1/comparisons/case8-cylinder", operation_id="CMP01",
        blueprint="crossflow", service="ComparisonService", request_model=ComparisonQuery,
        response_model=ApiEnvelope[CrossFlowComparison], documented_errors={400: ("INVALID_REQUEST",),
            404: ("UNKNOWN_CONFIG",), 405: ("METHOD_NOT_ALLOWED",),
            409: ("REVISION_UNAVAILABLE", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ"),
            422: ("UNSUPPORTED_COMBINATION",), 500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "INTERNAL_ERROR"),
            503: ("FEATURE_NOT_ENABLED",)}, delivery_phase="Alpha", handler=comparison,
        request_parser=make_parser(ComparisonQuery, optional=("case8_config", "cylinder_config")),
        description="Typed Case8/Cylinder children with explicit comparability and NO_UNIFIED_RANKING."))
