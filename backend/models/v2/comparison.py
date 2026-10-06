from typing import Any, Annotated, Literal

from pydantic import Field

from backend.models.v2.experiment import V2Model, Finite
from backend.models.v2.result import FieldName, ScientificField, ScientificRunResult


class CompareRunsRequest(V2Model):
    run_a: str
    run_b: str
    field: FieldName = "density"
    snapshot_time: Annotated[Finite, Field(ge=0)] | None = None


class ProtocolDifference(V2Model):
    field: str
    a: Any
    b: Any
    affects_conditions: bool


class MetricComparison(V2Model):
    metric_id: str
    label: str
    unit: str
    definition: str
    comparable: bool
    reason: str | None
    a: float | None
    b: float | None
    b_minus_a: float | None


class RunComparison(V2Model):
    version: Literal["case8.comparison.p7.1"] = "case8.comparison.p7.1"
    same_conditions: bool
    differences: list[ProtocolDifference]
    a: ScientificRunResult
    b: ScientificRunResult
    common_snapshot_times: list[float]
    snapshot_time: float | None
    field_a: ScientificField | None
    field_b: ScientificField | None
    color_min: float | None
    color_max: float | None
    field_reason: str | None
    metrics: list[MetricComparison]
    limitations: list[str]
