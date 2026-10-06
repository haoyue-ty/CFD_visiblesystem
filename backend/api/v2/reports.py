from flask import Response, g

from backend.api.catalog import Operation
from backend.models.v2.experiment import V2Envelope, V2FailedEnvelope
from backend.models.v2.report import ReportMetadata
from backend.models.v2.run import RunPath
from backend.services.v2.reports import ReportService


def register_report_operations(catalog, store, client):
    service = ReportService(store, client)
    errors = {400: ('INVALID_REQUEST',), 404: ('UNKNOWN_RUN',),
        409: ('RUN_RESULT_NOT_READY', 'REPORT_NOT_READY'), 429: ('REPORT_BUSY',),
        500: ('INTERNAL_ERROR', 'RUN_OUTPUT_INVALID', 'REPORT_OUTPUT_INVALID', 'CANONICAL_SCHEMA_MISMATCH')}
    def envelope(value):
        return dict(schema_version='2.0.0', request_id=g.request_id, data=value, warnings=[])
    for method, operation, action in [('POST','V2_REPORT_GENERATE',service.generate), ('GET','V2_REPORT_STATUS',service.status)]:
        catalog.register(Operation(method=method, path='/api/v2/reports/{run_id}', operation_id=operation,
            blueprint='v2_reports', service='ReportService', request_model=RunPath,
            response_model=V2Envelope[ReportMetadata], error_response_model=V2FailedEnvelope, documented_errors=errors,
            delivery_phase='V2-P6', handler=lambda q, run_id, action=action: envelope(action(run_id)),
            description='生成或核查自包含、版本化 HTML 报告；只读已验证 AI 缓存，不调用 provider。'))
    def html(query, run_id):
        response = Response(service.html(run_id), content_type='text/html; charset=utf-8')
        response.headers['Content-Security-Policy'] = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Disposition'] = f'inline; filename="ShockPath-{run_id}.html"'
        return response
    catalog.register(Operation(method='GET', path='/api/v2/reports/{run_id}/html', operation_id='V2_REPORT_HTML',
        blueprint='v2_reports', service='ReportService', request_model=RunPath, response_model=None,
        response_media_type='text/html', error_response_model=V2FailedEnvelope, documented_errors=errors,
        delivery_phase='V2-P6', handler=html, description='校验后的独立 HTML；全部 SVG 与数据内嵌。'))
