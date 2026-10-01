"""Frozen CLO01–05 bindings to the accepted Closure scientific service."""
from backend.api.case8 import make_parser
from backend.api.catalog import Operation
from backend.api.registry import check_registry_revision, envelope
from backend.models import ApiEnvelope
from backend.models.closure import ClosureHistory, ClosureRunRegistry, EntropyClosureRun, RefinementSummary
from backend.schemas.requests import ClosureHistoryQuery, ClosureRunQuery, RegistryQuery


def register_closure_operations(catalog, project, service):
    base = "/api/v1/experiments/entropy-closure"

    def respond(query, method, model, *args, **kwargs):
        check_registry_revision(query, project)
        return envelope(getattr(service, method)(*args, **kwargs), project, ApiEnvelope[model])

    bindings = [
        ("CLO01", "/runs", RegistryQuery, ClosureRunRegistry,
         lambda q: respond(q, "list_runs", ClosureRunRegistry), make_parser(RegistryQuery)),
        ("CLO02", "/runs/{run_id}", ClosureRunQuery, EntropyClosureRun,
         lambda q, run_id: respond(q, "load_run", EntropyClosureRun, run_id), make_parser(ClosureRunQuery)),
        ("CLO03", "/runs/{run_id}/stage-history", ClosureHistoryQuery, ClosureHistory,
         lambda q, run_id: respond(q, "load_stage_history", ClosureHistory, run_id, offset=q.offset, limit=q.limit),
         make_parser(ClosureHistoryQuery, integers=("offset", "limit"))),
        ("CLO04", "/runs/{run_id}/step-history", ClosureHistoryQuery, ClosureHistory,
         lambda q, run_id: respond(q, "load_step_history", ClosureHistory, run_id, offset=q.offset, limit=q.limit),
         make_parser(ClosureHistoryQuery, integers=("offset", "limit"))),
        ("CLO05", "/refinement", RegistryQuery, RefinementSummary,
         lambda q: respond(q, "load_refinement", RefinementSummary), make_parser(RegistryQuery)),
    ]
    descriptions = {
        "CLO01": "Exactly five frozen config/CFL runs; no Cartesian combination expansion.",
        "CLO02": "Saved entropy closure run with its bound CFL, protocol and terminal metrics.",
        "CLO03": "Fixed PER_STAGE saved columns; source stages 1/2/3 map to 0/1/2; preserve original clock.",
        "CLO04": "Fixed PER_STEP saved columns and intervals; step increments and recorded cumulative residual remain distinct.",
        "CLO05": "Four frozen D_u refinement points and existing slopes; fully-discrete diagnostic, no refit.",
    }
    errors = {
        400: ("INVALID_REQUEST",),
        404: ("INVALID_RESULT_ID", "MISSING_SCIENTIFIC_ASSET"),
        405: ("METHOD_NOT_ALLOWED",),
        409: ("REVISION_UNAVAILABLE", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ"),
        422: ("UNSUPPORTED_COMBINATION",),
        500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "INTERNAL_ERROR"),
        503: ("FEATURE_NOT_ENABLED",),
    }
    for identity, suffix, query, model, handler, parser in bindings:
        catalog.register(Operation(
            method="GET", path=base + suffix, operation_id=identity, blueprint="closure",
            service="ClosureService", request_model=query, response_model=ApiEnvelope[model],
            documented_errors=errors, delivery_phase="Alpha", handler=handler,
            request_parser=parser, description=descriptions[identity]))
