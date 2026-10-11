"""Catalog-registered finite export selectors; never accept client filesystem paths."""
from flask import g, send_file

from backend.api.catalog import Operation
from backend.models.v2.experiment import V2Envelope, V2FailedEnvelope
from backend.models.v2.export import ExportQuery, ExportMetadata, RunExports
from backend.models.v2.run import RunPath
from backend.services.v2.exports import ExportService


def register_export_operations(catalog, store, client):
    service = ExportService(store, client)
    errors = {400: ("INVALID_REQUEST",), 404: ("UNKNOWN_RUN",),
        409: ("RUN_RESULT_NOT_READY", "EXPORT_NOT_READY", "PDF_UNAVAILABLE"),
        413: ("EXPORT_CACHE_LIMIT",), 422: ("EXPORT_UNSUPPORTED_CASE",),
        429: ("EXPORT_BUSY", "EXPORT_SERVICE_BUSY", "REPORT_BUSY"),
        503: ("PDF_UNAVAILABLE", "EXPORT_TIMEOUT", "EXPORT_STORAGE_UNAVAILABLE"),
        500: ("INTERNAL_ERROR", "RUN_OUTPUT_INVALID", "EXPORT_OUTPUT_INVALID", "EXPORT_GENERATION_FAILED", "REPORT_OUTPUT_INVALID", "CANONICAL_SCHEMA_MISMATCH")}

    def envelope(value):
        return dict(schema_version="2.0.0", request_id=g.request_id, data=value, warnings=[])

    def download(query, run_id, kind):
        stream, filename, size, checksum = service.download(run_id, kind, query.format)
        media = {"zip": "application/zip", "html": "text/html", "pdf": "application/pdf"}[query.format]
        try:
            response = send_file(stream, mimetype=media, download_name=filename, as_attachment=True,
                                 conditional=False, etag=False)
        except Exception:
            stream.close()
            raise
        response.content_length = size
        response.headers["X-Export-SHA256"] = checksum
        response.headers["X-Content-Type-Options"] = "nosniff"
        if query.format == "html":
            response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:"
        response.call_on_close(stream.close)
        return response

    for method, path, operation, model, response, handler, media in (
        ("GET", "/api/v2/runs/{run_id}/exports", "V2_EXPORT_STATUS", RunPath, V2Envelope[RunExports],
         lambda q, run_id: envelope(service.status(run_id)), "application/json"),
        ("POST", "/api/v2/runs/{run_id}/exports/{kind}", "V2_EXPORT_GENERATE", ExportQuery, V2Envelope[ExportMetadata],
         lambda q, run_id, kind: envelope(service.generate(run_id, kind, q.format)), "application/json"),
        ("GET", "/api/v2/runs/{run_id}/exports/{kind}/download", "V2_EXPORT_DOWNLOAD", ExportQuery, None, download, "application/zip"),
    ):
        catalog.register(Operation(method=method, path=path, operation_id=operation, blueprint="v2_exports",
            service="ExportService", request_model=model, response_model=response, handler=handler,
            error_response_model=V2FailedEnvelope, documented_errors=errors, delivery_phase="V2.5-B",
            response_media_type=media, response_media_types=("text/html", "application/pdf") if response is None else (),
            description="从已验证完成 Run 生成并流式下载独立缓存；raw / visualization / report，report 可选 zip / html / pdf。"))
    return service
