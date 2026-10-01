"""CYL01–09: thin HTTP bindings to the accepted Window 1 service."""
from backend.api.case8 import make_parser
from backend.api.catalog import Operation
from backend.api.registry import envelope, check_registry_revision
from backend.core.errors import system_error
from backend.models import (ApiEnvelope, EntropyHistory, FieldResponse, FieldSnapshot,
                            MetricCollection, ScalarSeries, SnapshotIndex)
from backend.models.cylinder import AllocationResult, CylinderAllocationOverview
from backend.registry.cylinder_registry import require_config
from backend.schemas.requests import (ConfigQuery, FieldQuery, HistoryQuery, MetricQuery,
                                      ScalarSeriesQuery, SnapshotQuery)


def register_cylinder_operations(catalog, project, service):
    base = "/api/v1/experiments/cylinder/configs/{config_id}"

    def respond(query, method, model, config_id, *args, **kwargs):
        if hasattr(query, "snapshot_index") and query.snapshot_index is not None and query.snapshot_index < 1:
            raise system_error("INVALID_REQUEST", "Snapshot index must be 1-based", status=400)
        require_config(config_id)
        check_registry_revision(query, project)
        payload = getattr(service, method)(config_id, *args, **kwargs)
        issues = []
        if isinstance(payload, CylinderAllocationOverview):
            for slot in (payload.sectors, payload.front_band, payload.cumulative_2d):
                if slot.root.availability == "PARTIAL":
                    issues.extend(slot.root.issues)
                elif slot.root.availability != "AVAILABLE":
                    issues.append(slot.root.error)
        return envelope(payload, project, ApiEnvelope[model],
                        availability="PARTIAL" if issues else "AVAILABLE", issues=issues)

    def snapshot(query, config_id, snapshot_index):
        response = respond(query, "load_snapshot_metadata", FieldSnapshot, config_id, query.snapshot_index)
        if query.field is not None:
            selected = [f for f in response.root.data.fields if f.field_id == query.field]
            if not selected:
                raise system_error("MISSING_SCIENTIFIC_ASSET", "Saved snapshot field is absent", status=404,
                                   availability="MISSING", evidence_refs=response.root.data.result.provenance.evidence_refs)
            response.root.data = response.root.data.model_copy(update={"fields": selected})
        return response

    bindings = [
        ("CYL01", "/snapshots", ConfigQuery, SnapshotIndex,
         lambda q, config_id: respond(q, "list_snapshots", SnapshotIndex, config_id), make_parser(ConfigQuery)),
        ("CYL02", "/snapshots/{snapshot_index}", SnapshotQuery, FieldSnapshot, snapshot,
         make_parser(SnapshotQuery, integers=("snapshot_index",), optional=("field",))),
        ("CYL03", "/snapshots/{snapshot_index}/fields/{field_id}", FieldQuery, FieldResponse,
         lambda q, config_id, snapshot_index, field_id: respond(q, "load_field", FieldResponse, config_id, q.snapshot_index, q.field_id),
         make_parser(FieldQuery, integers=("snapshot_index",))),
        ("CYL04", "/entropy-history", HistoryQuery, EntropyHistory,
         lambda q, config_id: respond(q, "load_entropy_history", EntropyHistory, config_id,
                                     series=tuple(q.series) or None, offset=q.offset, limit=q.limit),
         make_parser(HistoryQuery, repeated="series", integers=("offset", "limit"))),
        ("CYL05", "/scalar-series/{series_id}", ScalarSeriesQuery, ScalarSeries,
         lambda q, config_id, series_id: respond(q, "load_scalar_series", ScalarSeries, config_id, q.series_id,
                                                offset=q.offset, limit=q.limit),
         make_parser(ScalarSeriesQuery, integers=("offset", "limit"))),
        ("CYL06", "/allocation", ConfigQuery, CylinderAllocationOverview,
         lambda q, config_id: respond(q, "load_allocation_overview", CylinderAllocationOverview, config_id), make_parser(ConfigQuery)),
        ("CYL07", "/allocation/sectors", ConfigQuery, AllocationResult,
         lambda q, config_id: respond(q, "load_sectors", AllocationResult, config_id), make_parser(ConfigQuery)),
        ("CYL08", "/allocation/front-band", ConfigQuery, AllocationResult,
         lambda q, config_id: respond(q, "load_front_band", AllocationResult, config_id), make_parser(ConfigQuery)),
        ("CYL09", "/metrics", MetricQuery, MetricCollection,
         lambda q, config_id: respond(q, "load_metrics", MetricCollection, config_id,
                                     metric_id=q.metric_id, snapshot_index=q.snapshot_index),
         make_parser(MetricQuery, integers=("snapshot_index",), optional=("metric_id",))),
    ]
    errors = {400: ("INVALID_REQUEST",), 404: ("UNKNOWN_CONFIG", "SNAPSHOT_NOT_FOUND", "INVALID_RESULT_ID", "MISSING_SCIENTIFIC_ASSET"),
              405: ("METHOD_NOT_ALLOWED",), 409: ("REVISION_UNAVAILABLE", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ"),
              422: ("UNSUPPORTED_COMBINATION",), 500: ("CANONICAL_SCHEMA_MISMATCH", "SOURCE_READ_ERROR", "INTERNAL_ERROR"),
              503: ("FEATURE_NOT_ENABLED",)}
    for identity, suffix, query, model, handler, parser in bindings:
        catalog.register(Operation(method="GET", path=base + suffix, operation_id=identity,
            blueprint="cylinder", service="CylinderService", request_model=query, response_model=ApiEnvelope[model],
            documented_errors=errors, delivery_phase="Alpha", handler=handler, request_parser=parser,
            description="Saved native Cylinder result; cumulative 2D remains MISSING."))
