"""Pydantic serialization/validation schemas to OpenAPI 3.1 components."""
import re
from typing import Literal

from pydantic import BaseModel

from backend.api.catalog import OperationCatalog
from backend.models import CORE_MODELS, CanonicalModel, FailedEnvelope


class OpenAPIDocument(CanonicalModel):
    openapi: Literal["3.1.0"]
    jsonSchemaDialect: str
    info: dict
    paths: dict
    components: dict


def export_openapi(catalog: OperationCatalog) -> dict:
    components: dict[str, dict] = {}

    def add_component(name: str, schema: dict):
        if name in components and components[name] != schema:
            raise ValueError(f"Conflicting JSON Schema component: {name}")
        components[name] = schema

    def register_model(model: type[BaseModel], mode: str = "serialization") -> dict:
        # Input schemas occupy their own namespace, preserving response identity.
        prefix = "Input_" if mode == "validation" else ""
        schema = model.model_json_schema(mode=mode, ref_template=f"#/components/schemas/{prefix}{{model}}")
        for name, definition in schema.pop("$defs", {}).items():
            add_component(prefix + name, definition)
        name = prefix + re.sub(r"[^a-zA-Z0-9_.-]", "_", model.__name__)
        add_component(name, schema)
        return {"$ref": f"#/components/schemas/{name}"}

    for model in CORE_MODELS:
        register_model(model)
    error_ref = register_model(FailedEnvelope)
    paths: dict = {}
    for operation in catalog.operations:
        response_ref = (register_model(operation.response_model) if operation.response_model is not None
                        else {"type": "string"})
        entry = {
            "operationId": operation.operation_id,
            "description": operation.description,
            "tags": [operation.blueprint],
            "x-delivery-phase": operation.delivery_phase,
            "x-service": operation.service,
            "x-auth-policy": operation.auth_policy,
            "x-cache-policy": operation.cache_policy,
            "responses": {str(operation.success_status): {"description": "Success", "content": {
                operation.response_media_type: {"schema": response_ref}}}},
        }
        for status, codes in operation.documented_errors.items():
            operation_error_ref = register_model(operation.error_response_model) if operation.error_response_model else error_ref
            entry["responses"][str(status)] = {
                "description": ", ".join(codes), "x-error-codes": list(codes),
                "content": {"application/json": {"schema": operation_error_ref}},
            }
        if operation.request_model is not None:
            query_ref = register_model(operation.request_model, "validation")
            query_schema = components[query_ref["$ref"].rsplit("/", 1)[-1]]
            required = query_schema.get("required", [])
            # Path fields are declared in the same request model as query fields.
            path_fields = re.findall(r"\{([^}]+)\}", operation.path)
            entry["parameters"] = [{"name": name, "in": "path" if name in path_fields else "query",
                                    "required": name in path_fields or name in required, "schema": prop}
                                   for name, prop in query_schema.get("properties", {}).items()]
            if set(path_fields) - set(query_schema.get("properties", {})):
                raise ValueError("Path selectors must be declared by the request model")
        elif re.findall(r"\{([^}]+)\}", operation.path):
            raise ValueError("Path selectors must be declared by the request model")
        if operation.request_body_model is not None:
            entry["requestBody"] = {"required": True, "content": {"application/json": {
                "schema": register_model(operation.request_body_model, "validation")}}}
        for name in operation.request_headers:
            entry.setdefault("parameters", []).append({"name": name, "in": "header", "required": False,
                                                       "schema": {"type": "string", "pattern": "^[0-9]{1,10}$"}})
        paths.setdefault(operation.path, {})[operation.method.lower()] = entry
    return OpenAPIDocument(
        openapi="3.1.0", jsonSchemaDialect="https://json-schema.org/draft/2020-12/schema",
        info={"title": "ShockPath Bootstrap", "version": "1.0.0"},
        paths=paths, components={"schemas": components},
    ).model_dump(mode="json")
