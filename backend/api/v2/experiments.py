from flask import g

from backend.ai.config_parser import parse_natural_language
from backend.api.catalog import Operation
from backend.models.v2.experiment import (
    ExperimentConfigDraft, LiveCases, NaturalLanguageRequest, V2Envelope, V2FailedEnvelope,
    ValidateExperimentRequest, ValidatedExperiment,
)
from backend.registry.v2.cases import case8
from backend.services.v2.experiments import validate_experiment


def register_experiment_operations(catalog, ai_client, execution_available=lambda: False):
    def envelope(value):
        return {"schema_version": "2.0.0", "request_id": g.request_id, "data": value, "warnings": []}

    def cases():
        live = case8()
        if execution_available():
            live = live.model_copy(update={"execution_available": True, "execution_status": "LIVE_AVAILABLE",
                                           "limitations": ["已开放后台串行运行；按真实步数展示进度。", *live.limitations[1:]]})
        return LiveCases(cases=[live], natural_language_available=ai_client.available)

    def validate(body):
        return validate_experiment(body).model_copy(update={"execution_available": execution_available()})

    def parse(body):
        draft = parse_natural_language(body, ai_client)
        if draft.validated:
            draft.validated = draft.validated.model_copy(update={"execution_available": execution_available()})
        return draft

    errors = {400: ("INVALID_REQUEST",), 413: ("INVALID_REQUEST",), 409: ("CAPABILITY_REVISION_CONFLICT",),
              422: ("UNSUPPORTED_PARAMETER", "UNSUPPORTED_COMBINATION"), 415: ("UNSUPPORTED_MEDIA_TYPE",),
              500: ("INTERNAL_ERROR", "CANONICAL_SCHEMA_MISMATCH")}
    for path, op_id, body_model, response_model, handler, op_errors in (
        ("/api/v2/cases", "V2_CASES", None, V2Envelope[LiveCases],
         lambda query: envelope(cases()),
         {400: ("INVALID_REQUEST",), 500: ("INTERNAL_ERROR",)}),
        ("/api/v2/experiments/validate", "V2_VALIDATE_EXPERIMENT", ValidateExperimentRequest,
         V2Envelope[ValidatedExperiment], lambda query, body: envelope(validate(body)), errors),
        ("/api/v2/experiments/parse-natural-language", "V2_PARSE_EXPERIMENT", NaturalLanguageRequest,
         V2Envelope[ExperimentConfigDraft], lambda query, body: envelope(parse(body)),
         {**errors, 502: ("AI_INVALID_OUTPUT",), 503: ("AI_UNAVAILABLE",)}),
    ):
        catalog.register(Operation(
            method="POST" if body_model else "GET", path=path, operation_id=op_id,
            blueprint="v2_experiments", service="LiveExperimentService", request_model=None,
            request_body_model=body_model, response_model=response_model, error_response_model=V2FailedEnvelope,
            documented_errors=op_errors, delivery_phase="V2-P1", handler=handler,
            description="Case 8 配置创建与验证；不创建 Run、不启动 CFD。",
        ))
