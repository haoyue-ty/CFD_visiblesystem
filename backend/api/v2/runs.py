import json
import threading
import time

from flask import Response, g, request

from backend.api.catalog import Operation
from backend.models.v2.experiment import V2Envelope, V2FailedEnvelope
from backend.models.v2.run import (
    CreateRunRequest, RunRecord, RunList, RunListQuery, RunPath, RunHistoryQuery,
    RunEventsQuery, RunSnapshotQuery, RunHistory, RunSnapshots, RunDensity,
)
from backend.services.v2.experiments import ExperimentError
from backend.services.v2.runs import RunService
from backend.services.v2.results import ScientificResultService
from backend.models.v2.result import (ScientificRunResult, RunEvidence, RunFieldQuery, ScientificField,
                                     NativeFaceArray, ViewContextQuery, RunViewContext)


def register_run_operations(catalog, store):
    service = RunService(store)
    scientific = ScientificResultService(store)
    slots = threading.BoundedSemaphore(store.settings.max_sse_connections)

    def envelope(value):
        return {"schema_version": "2.0.0", "request_id": g.request_id, "data": value, "warnings": []}

    def stream(query, run_id):
        record = store.get(run_id)
        header = request.headers.get("Last-Event-ID")
        if header is not None and (not header.isascii() or not header.isdecimal() or len(header) > 10):
            raise ExperimentError("INVALID_REQUEST", "事件游标不合法。", 400)
        after = max(query.after, int(header) if header is not None else 0)
        if after > record.last_event_id:
            raise ExperimentError("INVALID_REQUEST", "事件游标超出当前记录。", 400)
        if not slots.acquire(blocking=False):
            raise ExperimentError("EVENT_STREAM_LIMIT", "事件连接已满，请使用状态查询并稍后重连。", 429, retryable=True)
        released = False

        def release():
            nonlocal released
            if not released:
                released = True
                slots.release()

        def generate():
            cursor, began, last_heartbeat = after, time.monotonic(), 0.0
            try:
                yield "retry: 2000\n\n"
                while time.monotonic() - began < 30:
                    for event in store.events(run_id, cursor):
                        cursor = event["id"]
                        yield f"id: {cursor}\nevent: run\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                    if time.monotonic() - last_heartbeat > 10:
                        yield ": heartbeat\n\n"
                        last_heartbeat = time.monotonic()
                    time.sleep(.5)
            finally:
                release()
        response = Response(generate(), mimetype="text/event-stream",
                            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})
        response.call_on_close(release)
        return response

    errors = {400: ("INVALID_REQUEST",), 404: ("UNKNOWN_RUN", "SNAPSHOT_NOT_FOUND"),
              409: ("CONFIG_CONFIRMATION_CONFLICT", "IDEMPOTENCY_CONFLICT", "RUN_RESULT_NOT_READY", "CAPABILITY_REVISION_CONFLICT"),
              413: ("INVALID_REQUEST",), 415: ("UNSUPPORTED_MEDIA_TYPE",),
              422: ("UNSUPPORTED_PARAMETER", "UNSUPPORTED_COMBINATION"),
              429: ("RUN_QUEUE_FULL", "EVENT_STREAM_LIMIT"), 503: ("RUN_SERVICE_UNAVAILABLE",),
              500: ("INTERNAL_ERROR", "RUN_OUTPUT_INVALID", "CANONICAL_SCHEMA_MISMATCH")}
    for method, path, op, query, body, response, handler, status, media in (
        ("POST", "/api/v2/runs", "V2_CREATE_RUN", None, CreateRunRequest, V2Envelope[RunRecord],
         lambda q, body: envelope(store.create(body)), 202, "application/json"),
        ("GET", "/api/v2/runs", "V2_LIST_RUNS", RunListQuery, None, V2Envelope[RunList],
         lambda q: envelope(store.list(q)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}", "V2_GET_RUN", RunPath, None, V2Envelope[RunRecord],
         lambda q, run_id: envelope(store.get(run_id)), 200, "application/json"),
        ("POST", "/api/v2/runs/{run_id}/cancel", "V2_CANCEL_RUN", RunPath, None, V2Envelope[RunRecord],
         lambda q, run_id: envelope(store.cancel(run_id)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}/events", "V2_RUN_EVENTS", RunEventsQuery, None, None,
         stream, 200, "text/event-stream"),
        ("GET", "/api/v2/runs/{run_id}/history", "V2_RUN_HISTORY", RunHistoryQuery, None, V2Envelope[RunHistory],
         lambda q, run_id: envelope(service.history(q)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}/snapshots", "V2_RUN_SNAPSHOTS", RunPath, None, V2Envelope[RunSnapshots],
         lambda q, run_id: envelope(service.snapshots(run_id)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}/snapshot/{snapshot_id}", "V2_RUN_DENSITY", RunSnapshotQuery, None, V2Envelope[RunDensity],
         lambda q, run_id, snapshot_id: envelope(service.density(run_id, snapshot_id)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}/result", "V2_RUN_RESULT", RunPath, None, V2Envelope[ScientificRunResult],
         lambda q, run_id: envelope(scientific.result(run_id)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}/evidence", "V2_RUN_EVIDENCE", RunPath, None, V2Envelope[RunEvidence],
         lambda q, run_id: envelope(scientific.evidence(run_id)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}/snapshot/{snapshot_id}/field", "V2_RUN_FIELD", RunFieldQuery, None, V2Envelope[ScientificField],
         lambda q, run_id, snapshot_id: envelope(scientific.field(q)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}/snapshot/{snapshot_id}/faces", "V2_RUN_FACES", RunSnapshotQuery, None, V2Envelope[list[NativeFaceArray]],
         lambda q, run_id, snapshot_id: envelope(scientific.faces(q)), 200, "application/json"),
        ("GET", "/api/v2/runs/{run_id}/snapshot/{snapshot_id}/view-context", "V2_RUN_VIEW_CONTEXT", ViewContextQuery, None, V2Envelope[RunViewContext],
         lambda q, run_id, snapshot_id: envelope(scientific.context(q)), 200, "application/json"),
    ):
        catalog.register(Operation(method=method, path=path, operation_id=op, blueprint="v2_runs", service="RunService",
                                   request_model=query, request_body_model=body, response_model=response,
                                   error_response_model=V2FailedEnvelope, documented_errors=errors,
                                   delivery_phase="V2-P4" if op in ("V2_RUN_RESULT", "V2_RUN_EVIDENCE", "V2_RUN_FIELD", "V2_RUN_FACES", "V2_RUN_VIEW_CONTEXT") else "V2-P3", handler=handler, success_status=status,
                                   response_media_type=media, request_headers=("Last-Event-ID",) if media == "text/event-stream" else (),
                                   description="持久运行、单 worker 队列、真实进度与 Density。"))
