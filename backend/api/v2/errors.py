from flask import g, request

from backend.models.v2.experiment import V2ErrorBody, V2ErrorTarget, V2FailedEnvelope
from backend.services.v2.experiments import ExperimentError


def v2_error_response(app, error: ExperimentError):
    resource = ("run" if error.code == "UNKNOWN_RUN" or request.path.startswith("/api/v2/runs") else
                "sweep" if request.path.startswith("/api/v2/sweeps") else
                "comparison" if request.path.startswith("/api/v2/comparisons") else "experiment")
    target = V2ErrorTarget(resource_type=resource)
    envelope = V2FailedEnvelope(request_id=g.request_id, error=V2ErrorBody(
        code=error.code, message=error.message, retryable=error.retryable, details=error.details,
        target=target,
    ))
    return app.response_class(envelope.model_dump_json(), status=error.status,
                              content_type="application/json; charset=utf-8")
