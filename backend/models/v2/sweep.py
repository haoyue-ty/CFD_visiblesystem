from typing import Annotated, Literal

from pydantic import Field, model_validator

from backend.models.v2.experiment import V2Model, ValidateExperimentRequest, ValidatedExperiment, Finite
from backend.models.v2.run import RunQuery, RunRecord


class SweepRequest(ValidateExperimentRequest):
    q_aa_values: Annotated[list[Annotated[Finite, Field(ge=0, le=13.2)]], Field(min_length=1, max_length=3)]
    q_at_values: Annotated[list[Annotated[Finite, Field(ge=0, le=0.396)]], Field(min_length=1, max_length=3)]
    max_tasks: Annotated[int, Field(ge=1, le=9)] = 4
    time_budget_seconds: Annotated[Finite, Field(ge=1, le=1800)] = 300.0

    @model_validator(mode="after")
    def budget(self):
        if len(self.q_aa_values)*len(self.q_at_values) > self.max_tasks:
            raise ValueError("扫描组合数超过总任务预算")
        if len(set(self.q_aa_values)) != len(self.q_aa_values) or len(set(self.q_at_values)) != len(self.q_at_values):
            raise ValueError("扫描值必须唯一")
        return self


class SweepPreview(V2Model):
    sweep_hash: str
    experiments: list[ValidatedExperiment]
    total_tasks: int
    max_tasks: int
    time_budget_seconds: float
    warnings: list[str]


class CreateSweepRequest(SweepRequest):
    idempotency_key: Annotated[str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")]
    confirmed_sweep_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class SweepItem(V2Model):
    index: int
    q_aa: float
    q_at: float
    config_hash: str
    run: RunRecord | None = None
    status: Literal["PENDING", "QUEUED", "STARTING", "RUNNING", "POSTPROCESSING", "COMPLETED", "FAILED", "CANCELLED", "SKIPPED"] = "PENDING"


class SweepRecord(V2Model):
    sweep_id: str
    sweep_hash: str
    status: Literal["QUEUED", "RUNNING", "CANCELLING", "COMPLETED", "FAILED", "CANCELLED"]
    created_at: str
    finished_at: str | None = None
    time_budget_seconds: float
    elapsed_seconds: float = 0.0
    max_tasks: int
    total_tasks: int
    settled_tasks: int = 0
    successful_tasks: int = 0
    cancel_requested: bool = False
    failure: str | None = None
    items: list[SweepItem]
    warnings: list[str]


class SweepPath(RunQuery):
    sweep_id: str


class SweepListQuery(RunQuery):
    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=100)] = 20


class SweepList(V2Model):
    sweeps: list[SweepRecord]
    total: int
    offset: int
    limit: int
