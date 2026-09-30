from dataclasses import dataclass, field
import re
from typing import Callable

from flask import Blueprint, Flask, request
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
    response_model: type[BaseModel]
    documented_errors: dict[int, tuple[str, ...]]
    delivery_phase: str
    handler: Callable = field(repr=False, compare=False)
    description: str = ""
    auth_policy: str = "ANONYMOUS"
    cache_policy: str = "NO_STORE"
    request_parser: Callable[[dict[str, str], dict[str, list[str]]], dict] | None = field(default=None, repr=False, compare=False)


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
                value = _op.handler(query, **path_values)
                payload = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
                validated = _op.response_model.model_validate(payload)
                return app.response_class(validated.model_dump_json(), content_type="application/json; charset=utf-8")

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
