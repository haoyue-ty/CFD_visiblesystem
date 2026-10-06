from flask import g

from backend.api.catalog import Operation
from backend.models.v2.experiment import V2Envelope, V2FailedEnvelope
from backend.models.v2.comparison import CompareRunsRequest, RunComparison
from backend.models.v2.sweep import SweepRequest, CreateSweepRequest, SweepPreview, SweepRecord, SweepPath, SweepList, SweepListQuery
from backend.services.v2.comparison import ComparisonService
from backend.services.v2.sweeps import SweepService, preview


def register_comparison_operations(catalog, store):
    comparisons, sweeps = ComparisonService(store), SweepService(store)
    def envelope(value):
        return dict(schema_version="2.0.0", request_id=g.request_id, data=value, warnings=[])
    errors = {400: ("INVALID_REQUEST",), 404: ("UNKNOWN_RUN", "UNKNOWN_SWEEP"),
        409: ("RUN_RESULT_NOT_READY", "COMPARISON_TIME_UNAVAILABLE", "COMPARISON_DEFINITION_MISMATCH",
              "SWEEP_CONFIRMATION_CONFLICT", "IDEMPOTENCY_CONFLICT", "CAPABILITY_REVISION_CONFLICT"),
        413: ("INVALID_REQUEST",), 415: ("UNSUPPORTED_MEDIA_TYPE",),
        422: ("UNSUPPORTED_PARAMETER", "UNSUPPORTED_COMBINATION"),
        429: ("SWEEP_QUEUE_FULL",), 503: ("RUN_SERVICE_UNAVAILABLE",),
        500: ("RUN_OUTPUT_INVALID", "INTERNAL_ERROR", "CANONICAL_SCHEMA_MISMATCH")}
    for method, path, op, query, body, response, handler, status in (
        ("POST", "/api/v2/comparisons", "V2_COMPARE_RUNS", None, CompareRunsRequest, RunComparison,
         lambda q, body: envelope(comparisons.compare(body)), 200),
        ("POST", "/api/v2/sweeps/preview", "V2_PREVIEW_SWEEP", None, SweepRequest, SweepPreview,
         lambda q, body: envelope(preview(body)), 200),
        ("POST", "/api/v2/sweeps", "V2_CREATE_SWEEP", None, CreateSweepRequest, SweepRecord,
         lambda q, body: envelope(sweeps.create(body)), 202),
        ("GET", "/api/v2/sweeps", "V2_LIST_SWEEPS", SweepListQuery, None, SweepList,
         lambda q: envelope(sweeps.list(q)), 200),
        ("GET", "/api/v2/sweeps/{sweep_id}", "V2_GET_SWEEP", SweepPath, None, SweepRecord,
         lambda q, sweep_id: envelope(sweeps.get(sweep_id)), 200),
        ("POST", "/api/v2/sweeps/{sweep_id}/cancel", "V2_CANCEL_SWEEP", SweepPath, None, SweepRecord,
         lambda q, sweep_id: envelope(sweeps.cancel(sweep_id)), 200),
    ):
        catalog.register(Operation(method=method, path=path, operation_id=op, blueprint="v2_comparison",
            service="ComparisonService" if op == "V2_COMPARE_RUNS" else "SweepService",
            request_model=query, request_body_model=body, response_model=V2Envelope[response],
            error_response_model=V2FailedEnvelope, documented_errors=errors, delivery_phase="V2-P7",
            handler=handler, success_status=status, description="同条件科学对比与预算受控的串行 q_aa/q_at 扫描。"))
