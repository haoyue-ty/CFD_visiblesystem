"""Evidence-bound AI prose. Scientific numbers are rendered from server facts."""
from typing import Annotated, Literal
from pydantic import Field
from backend.models.v2.experiment import V2Model
from backend.models.v2.result import FieldName, RunViewContext

Text = Annotated[str, Field(min_length=1, max_length=1200)]
Ref = Annotated[str, Field(min_length=1, max_length=200)]


class AIViewSelection(V2Model):
    snapshot_id: Annotated[str, Field(pattern=r"^step_[0-9]{6}$")]
    field: FieldName = "density"
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None


class AIChatRequest(V2Model):
    run_id: str
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    view: AIViewSelection


class EvidenceFact(V2Model):
    evidence_id: str
    label: str
    value: float | int | str | bool | None
    unit: str
    availability: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None = None
    definition: str


class ScientificAIContext(V2Model):
    run_id: str
    result_hash: str
    config: dict
    identity: dict
    runtime: dict
    entropy: dict
    allocation: dict
    metrics: list[dict]
    current_view: RunViewContext | None
    limitations: list[str]
    evidence: list[EvidenceFact]


class AIClaim(V2Model):
    kind: Literal["FACT", "INTERPRETATION", "LIMITATION"]
    text: Text
    evidence_refs: Annotated[list[Ref], Field(min_length=1, max_length=6)]


class InterpretationContent(V2Model):
    summary: AIClaim
    key_findings: Annotated[list[AIClaim], Field(max_length=5)]
    observations: Annotated[list[AIClaim], Field(max_length=5)]
    limitations: Annotated[list[Text], Field(min_length=1, max_length=8)]
    suggested_questions: Annotated[list[Text], Field(min_length=1, max_length=5)]


class AssistantContent(V2Model):
    answer: Annotated[list[AIClaim], Field(min_length=1, max_length=6)]
    limitations: Annotated[list[Text], Field(min_length=1, max_length=8)]


class AIAnalysis(V2Model):
    run_id: str
    result_hash: str
    context_hash: str
    prompt_version: str
    model: str
    created_at: str
    cached: bool
    interpretation: InterpretationContent | None = None
    assistant: AssistantContent | None = None
    evidence: list[EvidenceFact]
    limitations: list[str]
    current_view: RunViewContext | None = None
