from flask import g
from backend.ai.analysis import ScientificAIService
from backend.api.catalog import Operation
from backend.models.v2.ai import AIChatRequest, AIAnalysis
from backend.models.v2.run import RunPath
from backend.models.v2.experiment import V2Envelope, V2FailedEnvelope


def register_ai_operations(catalog, store, client):
    service = ScientificAIService(store, client)
    def envelope(value):
        return {"schema_version": "2.0.0", "request_id": g.request_id, "data": value, "warnings": []}
    errors = {400: ("INVALID_REQUEST",), 404: ("UNKNOWN_RUN", "SNAPSHOT_NOT_FOUND"),
        409: ("RUN_RESULT_NOT_READY",), 413: ("INVALID_REQUEST", "AI_INPUT_LIMIT"),
        415: ("UNSUPPORTED_MEDIA_TYPE",), 429: ("AI_BUSY", "AI_BUDGET_LIMIT"),
        500: ("INTERNAL_ERROR", "RUN_OUTPUT_INVALID", "AI_CACHE_INVALID", "CANONICAL_SCHEMA_MISMATCH"),
        502: ("AI_INVALID_OUTPUT",), 503: ("AI_UNAVAILABLE",)}
    catalog.register(Operation(method="POST", path="/api/v2/ai/runs/{run_id}/interpret", operation_id="V2_AI_INTERPRET",
        blueprint="v2_ai", service="ScientificAIService", request_model=RunPath,
        response_model=V2Envelope[AIAnalysis], error_response_model=V2FailedEnvelope, documented_errors=errors,
        delivery_phase="V2-P5", handler=lambda q, run_id: envelope(service.interpret(run_id)),
        description="基于已验证科学结果的证据约束解读；按结果、prompt 和模型缓存。"))
    catalog.register(Operation(method="POST", path="/api/v2/ai/chat", operation_id="V2_AI_CHAT",
        blueprint="v2_ai", service="ScientificAIService", request_model=None, request_body_model=AIChatRequest,
        response_model=V2Envelope[AIAnalysis], error_response_model=V2FailedEnvelope, documented_errors=errors,
        delivery_phase="V2-P5", handler=lambda q, body: envelope(service.chat(body)),
        description="绑定 Run 和后端重算 view-context 的无工具科研问答。"))
