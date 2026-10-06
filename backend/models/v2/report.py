from typing import Literal

from backend.models.v2.experiment import V2Model


class ReportMetadata(V2Model):
    run_id: str
    status: Literal["NOT_GENERATED", "READY", "STALE"]
    result_hash: str
    report_version: str
    renderer_sha256: str
    scientific_context_hash: str
    report_id: str | None = None
    created_at: str | None = None
    html_sha256: str | None = None
    size_bytes: int | None = None
    ai_status: Literal["AVAILABLE", "UNAVAILABLE"]
    ai_reason: str | None = None
    ai_model: str | None = None
    ai_prompt_version: str | None = None
    ai_content_sha256: str | None = None
    html_url: str | None = None
