"""C801–C806 and C808 for the Case8 functional vertical slice.

Blueprint → Case8Service → Case8AdapterProtocol → controlled registry → READ_ONLY source.
Nothing here opens a CSV/NPZ, calls ``np.load`` or assembles a scientific path.

C807 (D_u cumulative allocation) stays CONTRACT_DEFINED / IMPLEMENTATION_DEFERRED and is
deliberately not registered, so the operation catalog cannot advertise an unimplemented
endpoint.
"""
from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.core.errors import missing_resource, system_error, unsupported_combination
from backend.models import (ApiEnvelope, EntropyHistory, FieldResponse, FieldSnapshot,
                            MetricCollection, ProjectInfo, ScalarSeries, SnapshotAlignment,
                            SnapshotIndex, known, unresolved)
from backend.schemas.requests import (AlignmentQuery, ConfigQuery, FieldQuery,
                                      HistoryQuery, MetricQuery, RegistryQuery,
                                      ScalarSeriesQuery, SnapshotQuery)


def _envelope(payload, project: ProjectInfo, response_model):
    return response_model.model_validate({
        "schema_version": "1.0.0", "request_id": g.request_id,
        "registry_revision": known(project.registry_revision),
        "data_revision": known(project.data_revision),
        "availability": "AVAILABLE", "data": payload, "issues": [],
    })


def _revision(query: RegistryQuery, project: ProjectInfo) -> None:
    if query.registry_revision is not None and query.registry_revision != project.registry_revision:
        raise system_error("REVISION_UNAVAILABLE", "Requested registry revision is unavailable", status=409)


def _registered_config(config_id: str) -> str:
    """Case8 keeps four canonical configs; C_u is a known unsupported combination."""
    if config_id == "C_u":
        raise unsupported_combination(
            "C_u is not a verified Case8 configuration",
            resource_type="case8_config", identity=known(config_id),
            details=[{"field": "config_id", "issue": "Outside the verified combination set",
                      "allowed_values": ["A_u", "B_u", "D_u"]}])
    if config_id not in ("A_u", "B_u", "D_u"):
        raise missing_resource("UNKNOWN_CONFIG", "Unknown Case8 configuration identity",
                               resource_type="case8_config",
                               identity=unresolved("Not present in the registry index"))
    return config_id


def make_parser(model, *, repeated: str | None = None, integers: tuple[str, ...] = (),
                optional: tuple[str, ...] = ()):
    """Build a query parser that mirrors the contract's wire rules.

    Rejects unknown keys and duplicate single-value keys, converts declared integer keys and
    keeps registry_revision optional. Path values are always override-protected upstream.
    """

    def parse(path: dict[str, str], query: dict[str, list[str]]) -> dict:
        for key, values in query.items():
            if key not in model.model_fields:
                raise ValueError("Unknown query parameter")
            if key != repeated and len(values) != 1:
                raise ValueError("Duplicate single-value query parameter")
        payload: dict = {}
        if repeated is not None and repeated in query:
            # Repeated keys are the only way to select several series at once.
            payload[repeated] = list(query[repeated])
        for name in optional:
            if name in query and name != repeated:
                payload[name] = query[name][0]
        for name in integers:
            if name in query:
                payload[name] = int(query[name][0])
        for name in path:
            if name in model.model_fields and name not in payload:
                payload[name] = int(path[name]) if name in integers else path[name]
        if "registry_revision" in query:
            payload["registry_revision"] = query["registry_revision"][0]
        return payload

    return parse


def register_case8_operations(catalog: OperationCatalog, project: ProjectInfo, service) -> None:
    config_base = "/api/v1/experiments/case8/configs/{config_id}"

    def snapshots(query: ConfigQuery, config_id: str):
        _revision(query, project)
        return _envelope(service.list_snapshots(_registered_config(config_id)), project,
                         ApiEnvelope[SnapshotIndex])

    def snapshot(query: SnapshotQuery, config_id: str, snapshot_index: str):
        _revision(query, project)
        config_id = _registered_config(config_id)
        # User-visible 1-based recorded index: 0 is invalid syntax, never an initial-state alias.
        if query.snapshot_index < 1:
            raise system_error("INVALID_REQUEST", "Snapshot index must be 1-based", status=400)
        snapshot_value = service.load_snapshot_metadata(config_id, query.snapshot_index)
        if query.field is not None:
            selected = [item for item in snapshot_value.fields if item.field_id == query.field]
            if not selected:
                raise missing_resource("SNAPSHOT_NOT_FOUND",
                                       "Requested field is not recorded in this snapshot",
                                       resource_type="case8_field",
                                       identity=known(f"{config_id}.snapshot.{query.snapshot_index}.{query.field}"))
            snapshot_value = snapshot_value.model_copy(update={"fields": selected})
        return _envelope(snapshot_value, project, ApiEnvelope[FieldSnapshot])

    def field(query: FieldQuery, config_id: str, snapshot_index: str, field_id: str):
        _revision(query, project)
        config_id = _registered_config(config_id)
        if query.snapshot_index < 1:
            raise system_error("INVALID_REQUEST", "Snapshot index must be 1-based", status=400)
        return _envelope(service.load_field(config_id, query.snapshot_index, query.field_id),
                         project, ApiEnvelope[FieldResponse])

    def entropy_history(query: HistoryQuery, config_id: str):
        _revision(query, project)
        selected = tuple(query.series) if query.series else None
        return _envelope(
            service.load_entropy_history(_registered_config(config_id), series=selected,
                                         offset=query.offset, limit=query.limit),
            project, ApiEnvelope[EntropyHistory])

    def scalar_series(query: ScalarSeriesQuery, config_id: str, series_id: str):
        _revision(query, project)
        return _envelope(
            service.load_scalar_series(_registered_config(config_id), query.series_id,
                                       offset=query.offset, limit=query.limit),
            project, ApiEnvelope[ScalarSeries])

    def metrics(query: MetricQuery, config_id: str):
        _revision(query, project)
        return _envelope(
            service.load_metrics(_registered_config(config_id), metric_id=query.metric_id,
                                 snapshot_index=query.snapshot_index),
            project, ApiEnvelope[MetricCollection])

    def snapshot_alignment(query: AlignmentQuery, config_id: str):
        _revision(query, project)
        config_id = _registered_config(config_id)
        if query.policy == "PINNED" and query.snapshot_index is None:
            raise system_error("INVALID_REQUEST", "PINNED alignment requires snapshot_index", status=400)
        if query.policy == "NEAREST_RECORDED" and query.snapshot_index is not None:
            raise system_error("INVALID_REQUEST",
                               "NEAREST_RECORDED alignment forbids snapshot_index", status=400)
        return _envelope(
            service.load_snapshot_alignment(config_id, scalar_step=query.scalar_step,
                                            policy=query.policy,
                                            snapshot_index=query.snapshot_index),
            project, ApiEnvelope[SnapshotAlignment])

    history_parser = make_parser(HistoryQuery, repeated="series", integers=("offset", "limit"))
    scalar_parser = make_parser(ScalarSeriesQuery, integers=("offset", "limit"))
    path_only = make_parser(ConfigQuery)
    snapshot_parser = make_parser(SnapshotQuery, integers=("snapshot_index",), optional=("field",))
    field_parser = make_parser(FieldQuery, integers=("snapshot_index",))
    metric_parser = make_parser(MetricQuery, integers=("snapshot_index",), optional=("metric_id",))
    alignment_parser = make_parser(AlignmentQuery, integers=("scalar_step", "snapshot_index"),
                                   optional=("policy",))

    common_errors = {400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",),
                     500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "INTERNAL_ERROR"),
                     503: ("FEATURE_NOT_ENABLED",)}

    catalog.register(Operation(
        method="GET", path=f"{config_base}/snapshots", operation_id="C801", blueprint="case8",
        service="Case8Service", request_model=ConfigQuery, response_model=ApiEnvelope[SnapshotIndex],
        documented_errors={**common_errors, 404: ("UNKNOWN_CONFIG",), 422: ("UNSUPPORTED_COMBINATION",),
                           409: ("REVISION_UNAVAILABLE",)},
        delivery_phase="Alpha", handler=snapshots, request_parser=path_only,
        description="Six recorded snapshot headers with refs only; no field values."))
    catalog.register(Operation(
        method="GET", path=f"{config_base}/snapshots/{{snapshot_index}}", operation_id="C802",
        blueprint="case8", service="Case8Service", request_model=SnapshotQuery,
        response_model=ApiEnvelope[FieldSnapshot],
        documented_errors={**common_errors, 404: ("UNKNOWN_CONFIG", "SNAPSHOT_NOT_FOUND"),
                           422: ("UNSUPPORTED_COMBINATION",), 409: ("REVISION_UNAVAILABLE",)},
        delivery_phase="Alpha", handler=snapshot, request_parser=snapshot_parser,
        description="Recorded snapshot metadata by 1-based index; no time interpolation."))
    catalog.register(Operation(
        method="GET", path=f"{config_base}/snapshots/{{snapshot_index}}/fields/{{field_id}}",
        operation_id="C803", blueprint="case8", service="Case8Service", request_model=FieldQuery,
        response_model=ApiEnvelope[FieldResponse],
        documented_errors={**common_errors, 404: ("UNKNOWN_CONFIG", "SNAPSHOT_NOT_FOUND"),
                           409: ("REVISION_UNAVAILABLE",)},
        delivery_phase="Alpha", handler=field, request_parser=field_parser,
        description="Real field header, spatial domain and array reference for ARRAY01 retrieval."))
    catalog.register(Operation(
        method="GET", path=f"{config_base}/entropy-history", operation_id="C804", blueprint="case8",
        service="Case8Service", request_model=HistoryQuery, response_model=ApiEnvelope[EntropyHistory],
        documented_errors={**common_errors, 404: ("UNKNOWN_CONFIG",), 409: ("REVISION_UNAVAILABLE",)},
        delivery_phase="Alpha", handler=entropy_history, request_parser=history_parser,
        description="1912 accepted-step entropy history; each selected series keeps its own source."))
    catalog.register(Operation(
        method="GET", path=f"{config_base}/scalar-series/{{series_id}}", operation_id="C805",
        blueprint="case8", service="Case8Service", request_model=ScalarSeriesQuery,
        response_model=ApiEnvelope[ScalarSeries],
        documented_errors={**common_errors, 404: ("UNKNOWN_CONFIG",), 409: ("REVISION_UNAVAILABLE",)},
        delivery_phase="Alpha", handler=scalar_series, request_parser=scalar_parser,
        description="One semantic scalar series; display names never identify a scientific quantity."))
    catalog.register(Operation(
        method="GET", path=f"{config_base}/metrics", operation_id="C806", blueprint="case8",
        service="Case8Service", request_model=MetricQuery, response_model=ApiEnvelope[MetricCollection],
        documented_errors={**common_errors, 404: ("UNKNOWN_CONFIG",), 409: ("REVISION_UNAVAILABLE",)},
        delivery_phase="Alpha", handler=metrics, request_parser=metric_parser,
        description="Width/RMS/HF metrics with definitions and detector scope."))
    catalog.register(Operation(
        method="GET", path=f"{config_base}/snapshot-alignment", operation_id="C808", blueprint="case8",
        service="Case8Service", request_model=AlignmentQuery, response_model=ApiEnvelope[SnapshotAlignment],
        documented_errors={**common_errors, 404: ("UNKNOWN_CONFIG",), 409: ("REVISION_UNAVAILABLE",)},
        delivery_phase="Alpha", handler=snapshot_alignment, request_parser=alignment_parser,
        description="Scalar step to recorded frame alignment with both times exposed."))
