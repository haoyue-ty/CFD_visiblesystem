from flask import Flask, g, request
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from backend.models import ErrorBody, FailedEnvelope, unresolved


class DomainError(Exception):
    """Typed error from registry/service/adapter, safe for public serialization."""
    def __init__(self, status: int, availability: str, body: ErrorBody):
        super().__init__(body.message)
        self.status = status
        self.availability = availability
        self.body = body


def system_error(code: str, message: str, *, status: int = 500,
                 availability: str = "ERROR", retryable: bool = False) -> DomainError:
    body = ErrorBody(domain="SYSTEM", code=code, message=message,
                     target={"resource_type": "api", "identity": unresolved("No registered resource identity")},
                     retryable=retryable, details=[], evidence_refs=[])
    return DomainError(status, availability, body)


def register_error_handlers(app: Flask) -> None:
    def domain_response(error: DomainError):
        envelope = FailedEnvelope(
            schema_version="1.0.0", request_id=g.request_id,
            registry_revision=unresolved("Registry not resolved for this failure"),
            data_revision=unresolved("Data not resolved for this failure"),
            availability=error.availability, error=error.body, issues=[],
        )
        return app.response_class(envelope.model_dump_json(), status=error.status,
                                  content_type="application/json; charset=utf-8")

    app.register_error_handler(DomainError, domain_response)

    @app.errorhandler(HTTPException)
    def http_error(error):
        if not (request.path == "/api" or request.path.startswith("/api/")):
            return error
        codes = {404: ("API_ROUTE_NOT_FOUND", "MISSING"), 405: ("METHOD_NOT_ALLOWED", "ERROR"),
                 400: ("INVALID_REQUEST", "ERROR"), 415: ("UNSUPPORTED_MEDIA_TYPE", "ERROR")}
        code, availability = codes.get(error.code, ("INTERNAL_ERROR", "ERROR"))
        response = domain_response(system_error(code, error.name, status=error.code, availability=availability))
        if error.code == 405:
            response.headers["Allow"] = ", ".join(error.valid_methods or [])
        return response

    @app.errorhandler(ValidationError)
    def output_error(error):
        app.logger.error("Canonical validation failed request_id=%s", g.request_id)
        return domain_response(system_error("CANONICAL_SCHEMA_MISMATCH", "Canonical response validation failed"))

    @app.errorhandler(Exception)
    def internal_error(error):
        app.logger.error("Unhandled error request_id=%s type=%s", g.request_id, type(error).__name__)
        return domain_response(system_error("INTERNAL_ERROR", "Internal server error"))
