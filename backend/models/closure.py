"""Canonical entropy closure entities, frozen 05_DATA_SCHEMA §10.

ScalarPoint inherits run identity, units and definitions through its containing
ScalarSeries.result; no alternate point/series DTO is introduced.
"""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .core import CanonicalModel, ID, PositiveInt, ResourceSlot, ScientificLimitation, fact_value
from .experiments import ExperimentConfig
from .results import Metric, ScalarSeries


class EntropyClosureRun(CanonicalModel):
    run_id: ID
    config: ExperimentConfig
    stage_point_count: PositiveInt
    step_point_count: PositiveInt
    stage_series_refs: list[ID]
    step_series_refs: list[ID]
    terminal_summary: list[ResourceSlot[Metric]]
    limitations: list[ScientificLimitation]
    evidence_refs: Annotated[list[ID], Field(min_length=1)]

    @model_validator(mode="after")
    def identities(self):
        if self.config.id != self.run_id or self.config.experiment_id != "entropy-closure":
            raise ValueError("Closure configuration identifies the complete run selection")
        if self.stage_point_count != 3 * self.step_point_count:
            raise ValueError("Closure has three recorded stages per accepted step")
        for slot in self.terminal_summary:
            metric = getattr(slot.root, "value", None)
            if metric and (metric.result.config_id != self.run_id or metric.result.experiment_id != "entropy-closure"):
                raise ValueError("Terminal metric identity must match run")
        return self


class ClosureRunRegistry(CanonicalModel):
    experiment_id: Literal["entropy-closure"]
    runs: list[EntropyClosureRun]

    @model_validator(mode="after")
    def unique_runs(self):
        if len({run.run_id for run in self.runs}) != len(self.runs):
            raise ValueError("Duplicate closure run")
        return self


class ClosureHistory(CanonicalModel):
    run_id: ID
    granularity: Literal["PER_STAGE", "PER_STEP"]
    series: list[ScalarSeries]
    evidence_refs: Annotated[list[ID], Field(min_length=1)]

    @model_validator(mode="after")
    def identities(self):
        if len({series.series_id for series in self.series}) != len(self.series):
            raise ValueError("Duplicate closure series")
        for series in self.series:
            if (series.result.experiment_id, series.result.config_id, series.result.time.sampling) != (
                "entropy-closure", self.run_id, self.granularity
            ):
                raise ValueError("Series must match closure run and granularity")
            for point in series.points:
                source_step = fact_value(point.source_step_index)
                if source_step is None or source_step < 1 or fact_value(point.step_index) != source_step:
                    raise ValueError("Closure preserves one-based accepted step indices")
                source_stage = fact_value(point.source_stage_index)
                if self.granularity == "PER_STAGE":
                    if source_stage not in (1, 2, 3) or fact_value(point.stage_index) != source_stage - 1:
                        raise ValueError("Closure maps source stages 1/2/3 to canonical 0/1/2")
                    if point.point_index != 3 * (source_step - 1) + source_stage - 1:
                        raise ValueError("Stage ordinal must preserve source order")
                elif point.point_index != source_step - 1:
                    raise ValueError("Step ordinal must preserve source order")
        return self


class RunMetrics(CanonicalModel):
    run_id: ID
    metrics: list[ResourceSlot[Metric]]

    @model_validator(mode="after")
    def identities(self):
        for slot in self.metrics:
            metric = getattr(slot.root, "value", None)
            if metric and (metric.result.config_id != self.run_id or metric.result.experiment_id != "entropy-closure"):
                raise ValueError("Refinement metrics must match the run")
        return self


class RefinementSummary(CanonicalModel):
    comparison_id: ID
    run_ids: list[ID]
    metrics_by_run: list[RunMetrics]
    refinement_slope: ResourceSlot[Metric]
    limitations: list[ScientificLimitation]
    evidence_refs: Annotated[list[ID], Field(min_length=1)]

    @model_validator(mode="after")
    def identities(self):
        if [run.run_id for run in self.metrics_by_run] != self.run_ids or len(set(self.run_ids)) != len(self.run_ids):
            raise ValueError("Refinement metrics must match the ordered run set")
        return self
