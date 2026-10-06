from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from backend.models.v2.experiment import V2Model, ValidateExperimentRequest, ValidatedExperiment

RunStatus = Literal["QUEUED", "STARTING", "RUNNING", "POSTPROCESSING", "COMPLETED", "FAILED", "CANCELLED"]


class CreateRunRequest(ValidateExperimentRequest):
    idempotency_key: Annotated[str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")]
    confirmed_config_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class RunRecord(V2Model):
    run_id: str
    status: RunStatus
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    heartbeat_at: str | None = None
    worker_pid: int | None = None
    worker_identity: str | None = None
    manager_identity: str | None = None
    cancel_requested: bool = False
    completed_steps: int = 0
    planned_steps: int | None = None
    physical_time: float = 0.0
    requested_final_time: float
    failure: str | None = None
    last_event_id: int = 0
    experiment: ValidatedExperiment
    data_origin: Literal["V2_LIVE_COMPUTATION"] = "V2_LIVE_COMPUTATION"
    log_tail: list[str] = Field(default_factory=list)


class RunQuery(V2Model):
    model_config = ConfigDict(extra="forbid", strict=False, allow_inf_nan=False)


class RunListQuery(RunQuery):
    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    status: RunStatus | None = None


class RunPath(RunQuery):
    run_id: str


class RunHistoryQuery(RunPath):
    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=200)] = 100


class RunEventsQuery(RunPath):
    after: Annotated[int, Field(ge=0)] = 0


class RunSnapshotQuery(RunPath):
    snapshot_id: Annotated[str, Field(pattern=r"^step_[0-9]{6}$")]


class RunList(V2Model):
    runs: list[RunRecord]
    total: int
    offset: int
    limit: int


class RunHistory(V2Model):
    rows: list[dict[str, float | int]]
    total: int
    offset: int


class RunSnapshotMeta(V2Model):
    snapshot_id: str
    step: int
    time: float
    cell_shape: list[int]


class RunSnapshots(V2Model):
    snapshots: list[RunSnapshotMeta]
    availability: Literal["AVAILABLE", "PENDING"]


class RunDensity(V2Model):
    run_id: str
    snapshot_id: str
    time: float
    shape: list[int]
    axes: list[str]
    x: list[float]
    y: list[float]
    extent_x: list[float]
    extent_y: list[float]
    unit: Literal["model density"] = "model density"
    values: list[float]
    minimum: float
    maximum: float
    source_sha256: str
    definition: Literal["rho = conservative state[..., 0]; C order, y then x"] = "rho = conservative state[..., 0]; C order, y then x"
