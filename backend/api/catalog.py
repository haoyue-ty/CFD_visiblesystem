from dataclasses import dataclass, field
import json
import re
from typing import Callable

from flask import Blueprint, Flask, Response, request
from pydantic import BaseModel, ValidationError

from backend.core.errors import system_error


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    operation_id: str
    blueprint: str
    service: str
    request_model: type[BaseModel] | None
    response_model: type[BaseModel] | None
    documented_errors: dict[int, tuple[str, ...]]
    delivery_phase: str
    handler: Callable = field(repr=False, compare=False)
    description: str = ""
    auth_policy: str = "ANONYMOUS"
    cache_policy: str = "NO_STORE"
    request_parser: Callable[[dict[str, str], dict[str, list[str]]], dict] | None = field(default=None, repr=False, compare=False)
    request_body_model: type[BaseModel] | None = None
    success_status: int = 200
    response_media_type: str = "application/json"
    error_response_model: type[BaseModel] | None = None
    request_headers: tuple[str, ...] = ()


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ValueError("Non-finite JSON number")


class OperationCatalog:
    def __init__(self):
        self._operations: list[Operation] = []

    @property
    def operations(self) -> tuple[Operation, ...]:
        return tuple(self._operations)

    def register(self, operation: Operation) -> None:
        if any(item.operation_id == operation.operation_id or (item.method, item.path) == (operation.method, operation.path)
               for item in self._operations):
            raise ValueError("Duplicate operation id or method/path")
        if operation.method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            raise ValueError("Unsupported catalog method")
        if not operation.path.startswith("/api/"):
            raise ValueError("Operations must use the API namespace")
        if operation.response_media_type not in ("application/json", "text/event-stream", "text/html"):
            raise ValueError("Unsupported response media type")
        if type(operation.success_status) is not int or not 200 <= operation.success_status < 300 or operation.success_status == 204:
            raise ValueError("Catalog responses require a body and a success status")
        if operation.success_status in operation.documented_errors:
            raise ValueError("Success status conflicts with documented errors")
        if ((operation.response_media_type == "application/json" and operation.response_model is None)
                or (operation.response_media_type != "application/json" and operation.response_model is not None)):
            raise ValueError("JSON requires a response model; text responses require a Flask Response")
        if operation.request_body_model is not None and operation.method not in ("POST", "PUT", "PATCH"):
            raise ValueError("JSON bodies require POST, PUT or PATCH")
        if operation.request_body_model is not None and "{body}" in operation.path:
            raise ValueError("Path selectors cannot use the body handler argument")
        self._operations.append(operation)

    def bind(self, app: Flask) -> None:
        blueprints: dict[str, Blueprint] = {}
        for operation in self.operations:
            blueprint = blueprints.setdefault(operation.blueprint, Blueprint(operation.blueprint, __name__))

            def view(_op=operation, **path_values):
                query = None
                if _op.request_model is not None:
                    if _op.request_parser is None and any(len(request.args.getlist(key)) != 1 for key in request.args):
                        raise system_error("INVALID_REQUEST", "Duplicate single-value query parameter", status=400)
                    if set(request.args) & set(path_values):
                        raise system_error("INVALID_REQUEST", "Path selectors cannot be overridden by query", status=400)
                    if set(request.args) - set(_op.request_model.model_fields):
                        raise system_error("INVALID_REQUEST", "Unknown query parameter", status=400)
                    try:
                        payload = (_op.request_parser(path_values, request.args.to_dict(flat=False))
                                   if _op.request_parser is not None else {**request.args.to_dict(), **path_values})
                        query = _op.request_model.model_validate(payload)
                    except (ValidationError, ValueError, TypeError):
                        raise system_error("INVALID_REQUEST", "Invalid query parameters", status=400) from None
                elif request.args:
                    raise system_error("INVALID_REQUEST", "This operation accepts no query parameters", status=400)
                handler_values = dict(path_values)
                if _op.request_body_model is not None:
                    if not request.is_json:
                        raise system_error("UNSUPPORTED_MEDIA_TYPE", "Expected a JSON request body", status=415)
                    try:
                        raw_body = request.get_data()
                        payload = json.loads(raw_body, object_pairs_hook=_json_object,
                                             parse_constant=_reject_json_constant)
                        if not isinstance(payload, dict):
                            raise ValueError("Expected a JSON object")
                        # Preserve strict JSON semantics (e.g. arrays for tuples,
                        # ISO dates), while the preflight rejects ambiguous JSON.
                        handler_values["body"] = _op.request_body_model.model_validate_json(raw_body)
                    except ValidationError as error:
                        if _op.error_response_model is not None:
                            from backend.services.v2.experiments import ExperimentError
                            from backend.models.v2.experiment import V2FieldIssue
                            details = [V2FieldIssue(field=(".".join(str(part) for part in item["loc"])[:160] or "body"),
                                                    reason=item["type"]) for item in error.errors()[:32]]
                            raise ExperimentError("INVALID_REQUEST", "请求字段、类型或取值不合法。", 400, details) from None
                        raise system_error("INVALID_REQUEST", "Invalid JSON request body", status=400) from None
                    except (ValueError, TypeError, UnicodeError):
                        raise system_error("INVALID_REQUEST", "Invalid JSON request body", status=400) from None
                value = _op.handler(query, **handler_values)
                if _op.response_media_type != "application/json":
                    if (not isinstance(value, Response) or value.mimetype != _op.response_media_type
                            or value.status_code != _op.success_status):
                        raise TypeError("Handler must return a Response with the declared media type and status")
                    return value
                payload = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
                validated = _op.response_model.model_validate(payload)
                return app.response_class(validated.model_dump_json(), status=_op.success_status,
                                          content_type="application/json; charset=utf-8")

            flask_path = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", r"<\1>", operation.path)
            blueprint.add_url_rule(flask_path, endpoint=operation.operation_id, view_func=view, methods=[operation.method])
        for blueprint in blueprints.values():
            app.register_blueprint(blueprint)
        self.assert_routes(app)

    def assert_routes(self, app: Flask) -> None:
        expected = {(item.method, item.path) for item in self.operations}
        actual = set()
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith("/api/"):
                path = re.sub(r"<(?:(?:[^:>]+):)?([^>]+)>", r"{\1}", rule.rule)
                actual.update((method, path) for method in rule.methods - {"HEAD", "OPTIONS"})
        if actual != expected:
            raise ValueError("Runtime routes differ from operation catalog")
