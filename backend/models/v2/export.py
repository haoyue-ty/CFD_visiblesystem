"""Export status is independent of immutable scientific results."""
from typing import Literal

from pydantic import Field

from backend.models.v2.experiment import V2Model
from backend.models.v2.run import RunPath

ExportKind = Literal["raw", "visualization", "report"]
ExportState = Literal["NOT_GENERATED", "GENERATING", "READY", "FAILED"]


class ExportPath(RunPath):
    kind: ExportKind


class ExportQuery(ExportPath):
    format: Literal["zip", "html", "pdf"] = "zip"


class ExportCapability(V2Model):
    formats: list[str]
    unavailable_formats: dict[str, str] = Field(default_factory=dict)
    retryable_formats: list[str] = Field(default_factory=list)


class ExportMetadata(V2Model):
    kind: ExportKind
    status: ExportState = "NOT_GENERATED"
    formats: list[str] = Field(default_factory=list)
    generated_at: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    download_urls: dict[str, str] = Field(default_factory=dict)
    unavailable_formats: dict[str, str] = Field(default_factory=dict)
    error_code: str | None = None
    reason: str | None = None


class RunExports(V2Model):
    run_id: str
    available: bool
    reason: str | None
    source_result_hash: str | None
    exporter_version: str
    capabilities: dict[ExportKind, ExportCapability]
    exports: dict[ExportKind, ExportMetadata]
