"""Run-scoped scientific contract; model units never imply SI calibration."""
from typing import Literal

from pydantic import Field, model_validator

from backend.models.v2.experiment import V2Model, ValidatedExperiment
from backend.models.v2.run import RunSnapshotQuery, RunSnapshotMeta


FieldName = Literal["density", "pressure", "velocity_x", "velocity_y", "speed", "mach"]


class RunFieldQuery(RunSnapshotQuery):
    field: FieldName = "density"


class ViewContextQuery(RunFieldQuery):
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None

    @model_validator(mode="after")
    def region(self):
        values = [self.x_min, self.x_max, self.y_min, self.y_max]
        if any(v is not None for v in values):
            if any(v is None for v in values) or self.x_min >= self.x_max or self.y_min >= self.y_max:
                raise ValueError("Region requires four ordered bounds")
        return self


class ScientificField(V2Model):
    run_id: str
    snapshot_id: str
    field_id: FieldName
    label: str
    time: float
    shape: list[int]
    axes: list[str]
    x: list[float]
    y: list[float]
    extent_x: list[float]
    extent_y: list[float]
    unit: str
    definition: str
    values: list[float]
    minimum: float
    maximum: float
    source_sha256: str
    availability: Literal["AVAILABLE"] = "AVAILABLE"


class NativeFaceArray(V2Model):
    array_id: str
    label: str
    channel: Literal["bg", "aa", "at"]
    location_type: Literal["CARTESIAN_X_FACE", "CARTESIAN_Y_FACE"]
    quantity: Literal["INSTANTANEOUS_PI", "CUMULATIVE_SPATIAL_ALLOCATION"]
    shape: list[int]
    axes: list[str]
    x: list[float]
    y: list[float]
    unit: str
    face_measure: float
    time_start: float
    time_end: float
    values: list[float]
    source_sha256: str


class RunAllocation(V2Model):
    availability: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None
    arrays: list[NativeFaceArray] | None
    scalar_totals: dict[str, float] | None
    definition: str
    max_scalar_abs_error: float | None


class RunMetric(V2Model):
    metric_id: str
    label: str
    value: float | None
    availability: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None
    unit: str
    definition: str
    detector: str
    window: str
    normalization: str
    applicable_conditions: str
    time: float
    resolution_limit: float | None
    evidence_id: str


class ScientificIdentity(V2Model):
    run_id: str
    result_id: str
    evidence_id: str
    config_hash: str
    classification: str
    data_origin: Literal["V2_LIVE_COMPUTATION"] = "V2_LIVE_COMPUTATION"
    verification: str
    frozen: Literal[False] = False


class FieldDefinition(V2Model):
    field_id: FieldName
    label: str
    unit: str
    definition: str


class HashAsset(V2Model):
    path: str
    sha256: str


class RunProvenance(V2Model):
    method_id: str
    method_sha256: str
    source_manifest_revision: str
    source_manifest_sha256: str
    dependencies: list[HashAsset]
    software: list[HashAsset]
    postprocess_version: str
    postprocess_sha256: str
    solver_result_sha256: str
    effective_config_sha256: str
    outputs: list[HashAsset]


class RunEntropy(V2Model):
    availability: Literal["AVAILABLE"] = "AVAILABLE"
    unit: str
    rk_weights: list[float]
    stage_states: list[str]
    face_measure_rule: str
    spatial_scope: str
    cumulative_rule: str
    rows: list[dict[str, float | int]]
    totals: dict[str, float]
    source_sha256: str


class ResultRuntime(V2Model):
    started_at: str
    finished_at: str
    accepted_steps: int
    final_time: float
    dt: float
    wall_seconds: float
    solver_seconds: float
    peak_rss_bytes: int


class ScientificRunResult(V2Model):
    schema_version: Literal["2.0.0"] = "2.0.0"
    result_hash: str
    identity: ScientificIdentity
    config: ValidatedExperiment
    runtime: ResultRuntime
    fields: list[FieldDefinition]
    snapshots: list[RunSnapshotMeta]
    entropy: RunEntropy
    metrics: list[RunMetric]
    allocation: RunAllocation
    limitations: list[str]
    provenance: RunProvenance


class RunEvidence(V2Model):
    evidence_id: str
    result_hash: str
    identity: ScientificIdentity
    config: ValidatedExperiment
    effective_config: dict
    provenance: RunProvenance
    outputs: list[HashAsset]
    supports: list[str]
    does_not_support: list[str]
    limitations: list[str]


class RunViewContext(V2Model):
    run_id: str
    result_hash: str
    evidence_id: str
    snapshot_id: str
    snapshot_sha256: str
    field: FieldName
    time: float
    unit: str
    region: dict[str, float] | None
    sample_location: Literal["CELL_CENTER"] = "CELL_CENTER"
    selected_count: int
    availability: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None
    minimum: float | None
    maximum: float | None
    mean: float | None
