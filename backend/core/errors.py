from flask import Flask, g, request
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from backend.models import ErrorBody, FailedEnvelope, unresolved

# Error codes that are typed for the public contract. Anything not listed is a bug.
SYSTEM_CODES = frozenset({
    "INVALID_REQUEST", "API_ROUTE_NOT_FOUND", "METHOD_NOT_ALLOWED", "UNSUPPORTED_MEDIA_TYPE",
    "REVISION_UNAVAILABLE", "INTERNAL_ERROR", "FEATURE_NOT_ENABLED",
})
SCIENTIFIC_CODES = frozenset({
    "UNKNOWN_EXPERIMENT", "UNKNOWN_CONFIG", "INVALID_RESULT_ID", "SNAPSHOT_NOT_FOUND",
    "UNKNOWN_EVIDENCE_ID", "UNKNOWN_ASSET_ID", "MISSING_SCIENTIFIC_ASSET",
    "UNSUPPORTED_REPRESENTATION", "MISSING_ASSET",
    "UNSUPPORTED_COMBINATION", "SOURCE_READ_ERROR", "CANONICAL_SCHEMA_MISMATCH",
    "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ",
    # Phase 7B Window 2 spectral contract codes (frozen 06 §10/§11).
    "UNKNOWN_SPECTRUM", "UNKNOWN_MODE", "MISSING_EIGENMODE", "UNSUPPORTED_PARAMETER",
})
# Failures here are server-side by definition: the adapter or the canonical contract is at fault.
SERVER_SIDE_CODES = frozenset({
    "SOURCE_READ_ERROR", "SOURCE_ERROR", "CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR",
    "FEATURE_NOT_ENABLED",
})


class DomainError(Exception):
    """Typed error from registry/service/adapter, safe for public serialization."""
    def __init__(self, status: int, availability: str, body: ErrorBody):
        super().__init__(body.message)
        self.status = status
        self.availability = availability
        self.body = body


def system_error(code: str, message: str, *, status: int = 500,
                 availability: str = "ERROR", retryable: bool = False,
                 resource_type: str = "api", identity=None,
                 details: list | None = None, evidence_refs: list | None = None,
                 domain: str = "SYSTEM") -> DomainError:
    """Construct a typed, contract-listed failure without leaking internal detail.

    `identity` is an already-built Fact dict (see `unresolved`/`known`), so a known
    target identity and an unknown one stay distinguishable in the wire payload.
    """
    if code in SCIENTIFIC_CODES:
        # Scientific codes are always reported under the SCIENTIFIC domain.
        domain = "SCIENTIFIC"
    body = ErrorBody(
        domain=domain, code=code, message=message,
        target={"resource_type": resource_type,
                "identity": identity if identity is not None else unresolved("No registered resource identity")},
        retryable=retryable, details=details or [], evidence_refs=evidence_refs or [],
    )
    return DomainError(status, availability, body)


def missing_resource(code: str, message: str, *, resource_type: str, identity) -> DomainError:
    """404 MISSING: the identity is recognized by the registry but has no data."""
    return system_error(code, message, status=404, availability="MISSING",
                        resource_type=resource_type, identity=identity, domain="SCIENTIFIC")


def unsupported_combination(message: str, *, resource_type: str, identity,
                            details: list | None = None, evidence_refs: list | None = None) -> DomainError:
    """422 UNSUPPORTED: syntactically valid but outside the verified combination set."""
    return system_error("UNSUPPORTED_COMBINATION", message, status=422, availability="UNSUPPORTED",
                        resource_type=resource_type, identity=identity, details=details,
                        evidence_refs=evidence_refs, domain="SCIENTIFIC")


def missing_asset(message: str, *, resource_type: str, identity,
                  details: list | None = None, evidence_refs: list | None = None) -> DomainError:
    """404 MISSING_ASSET: a recognized allocation identity whose saved asset is absent."""
    return system_error("MISSING_ASSET", message, status=404, availability="MISSING",
                        resource_type=resource_type, identity=identity, details=details,
                        evidence_refs=evidence_refs, domain="SCIENTIFIC")


def unsupported_representation(message: str, *, resource_type: str, identity,
                               details: list | None = None,
                               evidence_refs: list | None = None) -> DomainError:
    """422 UNSUPPORTED_REPRESENTATION: allocation cannot be rendered as the requested form."""
    return system_error("UNSUPPORTED_REPRESENTATION", message, status=422, availability="UNSUPPORTED",
                        resource_type=resource_type, identity=identity, details=details,
                        evidence_refs=evidence_refs, domain="SCIENTIFIC")


def source_error(message: str, *, retryable: bool = False, resource_type: str = "allocation",
                 identity=None, evidence_refs: list | None = None) -> DomainError:
    """500 SOURCE_ERROR: the controlled allocation source could not be read faithfully."""
    return system_error("SOURCE_ERROR", message, status=500, retryable=retryable,
                        resource_type=resource_type, identity=identity,
                        evidence_refs=evidence_refs, domain="SYSTEM")


def unknown_spectrum(message: str, *, resource_type: str = "spectrum", identity=None,
                     details: list | None = None, evidence_refs: list | None = None) -> DomainError:
    """404 UNKNOWN_SPECTRUM: the requested spectrum dataset identity is not registered."""
    return system_error("UNKNOWN_SPECTRUM", message, status=404, availability="MISSING",
                        resource_type=resource_type, identity=identity, details=details,
                        evidence_refs=evidence_refs, domain="SCIENTIFIC")


def unknown_mode(message: str, *, resource_type: str = "spectrum", identity=None,
                 details: list | None = None, evidence_refs: list | None = None) -> DomainError:
    """404 UNKNOWN_MODE: the requested Fourier mode index is not a registered block."""
    return system_error("UNKNOWN_MODE", message, status=404, availability="MISSING",
                        resource_type=resource_type, identity=identity, details=details,
                        evidence_refs=evidence_refs, domain="SCIENTIFIC")


def missing_eigenmode(message: str, *, resource_type: str = "eigenmode", identity=None,
                      details: list | None = None, evidence_refs: list | None = None) -> DomainError:
    """404 MISSING_EIGENMODE: the eigenmode selection is registered but its saved vector/profile is absent."""
    return system_error("MISSING_EIGENMODE", message, status=404, availability="MISSING",
                        resource_type=resource_type, identity=identity, details=details,
                        evidence_refs=evidence_refs, domain="SCIENTIFIC")


def unsupported_parameter(message: str, *, resource_type: str = "spectrum", identity=None,
                          details: list | None = None, evidence_refs: list | None = None) -> DomainError:
    """422 UNSUPPORTED_PARAMETER: a syntactically valid selector outside the verified parameter set."""
    return system_error("UNSUPPORTED_PARAMETER", message, status=422, availability="UNSUPPORTED",
                        resource_type=resource_type, identity=identity, details=details,
                        evidence_refs=evidence_refs, domain="SCIENTIFIC")


def register_error_handlers(app: Flask) -> None:
    def domain_response(error: DomainError):
        if request.path.startswith("/api/v2/"):
            from backend.api.v2.errors import v2_error_response
            from backend.services.v2.experiments import ExperimentError
            return v2_error_response(app, ExperimentError(error.body.code, error.body.message,
                                     error.status, retryable=error.body.retryable))
        envelope = FailedEnvelope(
            schema_version="1.0.0", request_id=g.request_id,
            registry_revision=unresolved("Registry not resolved for this failure"),
            data_revision=unresolved("Data not resolved for this failure"),
            availability=error.availability, error=error.body, issues=[],
        )
        return app.response_class(envelope.model_dump_json(), status=error.status,
                                  content_type="application/json; charset=utf-8")

    app.register_error_handler(DomainError, domain_response)
    from backend.api.v2.errors import v2_error_response
    from backend.services.v2.experiments import ExperimentError
    app.register_error_handler(ExperimentError, lambda error: v2_error_response(app, error))

    @app.errorhandler(HTTPException)
    def http_error(error):
        if not (request.path == "/api" or request.path.startswith("/api/")):
            return error
        codes = {404: ("API_ROUTE_NOT_FOUND", "MISSING"), 405: ("METHOD_NOT_ALLOWED", "ERROR"),
                 400: ("INVALID_REQUEST", "ERROR"), 415: ("UNSUPPORTED_MEDIA_TYPE", "ERROR"),
                 413: ("INVALID_REQUEST", "ERROR")}
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
