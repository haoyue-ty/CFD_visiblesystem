from math import prod
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .core import (CanonicalModel, DataOrigin, Fact, ID, Integer, NonNegativeInt,
                   Number, PositiveInt, ProvenanceRef, ResourceSlot, SchemaVersion,
                   ScientificLimitation, UnitSpec, Verification, fact_value)
from .context import GridSpec, NamedFact, ScopeSpec, SpatialDomain, TimeInterval, TimeSpec


class ScientificResult(CanonicalModel):
    schema_version: SchemaVersion
    result_id: ID
    experiment_id: ID
    config_id: ID
    semantic_id: ID
    data_origin: DataOrigin
    availability: Literal["AVAILABLE", "PARTIAL"]
    time: TimeSpec
    scope: ScopeSpec
    unit: UnitSpec
    verification: Verification
    provenance: ProvenanceRef
    limitations: list[ScientificLimitation]

    @model_validator(mode="after")
    def origin_status(self):
        if self.data_origin in ("MOCK", "SCHEMATIC") and self.verification.status != "NOT_APPLICABLE":
            raise ValueError("Mock and schematic results cannot claim scientific verification")
        if self.data_origin == "MOCK" and not self.result_id.startswith("mock."):
            raise ValueError("Mock results require the mock namespace")
        if self.data_origin not in ("MOCK", "SCHEMATIC", "LIVE_DEMO") and self.verification.status not in (
            "FROZEN_VERIFIED", "VERIFIED_NOT_FROZEN", "DERIVED_VERIFIED", "PARTIAL"
        ):
            raise ValueError("Production results require a verified basis")
        if self.data_origin not in ("MOCK", "SCHEMATIC") and not self.provenance.source_asset_ids:
            raise ValueError("Scientific results require source asset identities")
        return self


class ComplexValue(CanonicalModel):
    real: Number
    imag: Number


class ArrayDescriptor(CanonicalModel):
    array_id: ID
    dtype: Literal["float64", "int64", "bool", "complex128"]
    shape: list[PositiveInt]
    order: Literal["C"]
    axes: list[str]
    encoding: Literal["FLAT_JSON"]
    element_count: PositiveInt

    @model_validator(mode="after")
    def shape_count(self):
        if self.element_count != prod(self.shape) or len(self.axes) != len(self.shape):
            raise ValueError("Array count and axes must match shape")
        return self


class ArrayRef(CanonicalModel):
    result_id: ID
    descriptor: ArrayDescriptor


class ScientificArray(CanonicalModel):
    result: ScientificResult
    descriptor: ArrayDescriptor
    values: list[Number | Integer | bool | ComplexValue]

    @model_validator(mode="after")
    def values_match(self):
        if len(self.values) != self.descriptor.element_count:
            raise ValueError("Flat value count must match descriptor")
        types = {"float64": (int, float), "int64": (int,), "bool": (bool,), "complex128": (ComplexValue,)}
        if any(type(value) not in types[self.descriptor.dtype] for value in self.values):
            raise ValueError("Array values must match dtype without coercion")
        return self


class FieldDescriptor(CanonicalModel):
    field_id: ID
    label: str
    result: ScientificResult
    domain: SpatialDomain
    array_ref: ArrayRef
    mask_refs: list[ID]

    @model_validator(mode="after")
    def field_identity(self):
        if self.array_ref.result_id != self.result.result_id:
            raise ValueError("Field reference and header result must match")
        if self.domain.shape != self.array_ref.descriptor.shape:
            raise ValueError("Field array shape must match domain")
        if [axis.name for axis in self.domain.axes] != self.array_ref.descriptor.axes:
            raise ValueError("Field array axes must match domain")
        return self


class FieldSnapshot(CanonicalModel):
    result: ScientificResult
    snapshot_id: ID
    snapshot_index: PositiveInt
    step_index: NonNegativeInt
    physical_time: Number
    grid: GridSpec
    fields: list[FieldDescriptor]

    @model_validator(mode="after")
    def snapshot_context(self):
        header = self.result
        if header.time.sampling != "MULTI_SNAPSHOT" or header.time.accumulation != "NONE":
            raise ValueError("Snapshot must use recorded instantaneous time semantics")
        for name in ("snapshot_index", "step_index", "physical_time"):
            if fact_value(getattr(header.time, name)) != getattr(self, name):
                raise ValueError("Snapshot selector must match header time")
        if header.experiment_id == "case8" and self.snapshot_index > 6:
            raise ValueError("Case8 has only six recorded indices")
        for field in self.fields:
            if (field.result.experiment_id, field.result.config_id, field.result.time) != (
                header.experiment_id, header.config_id, header.time
            ):
                raise ValueError("Snapshot fields must match experiment, config and time")
        return self


class SnapshotIndex(CanonicalModel):
    experiment_id: ID
    config_id: ID
    snapshot_count: NonNegativeInt
    items: list[FieldSnapshot]

    @model_validator(mode="after")
    def index_matches(self):
        if self.snapshot_count != len(self.items):
            raise ValueError("Snapshot count must match metadata items")
        indices = [item.snapshot_index for item in self.items]
        if len(set(indices)) != len(indices):
            raise ValueError("Recorded indices must be unique")
        if any((item.result.experiment_id, item.result.config_id) != (self.experiment_id, self.config_id) for item in self.items):
            raise ValueError("Snapshot identity must match index")
        return self


class ScalarPoint(CanonicalModel):
    point_index: NonNegativeInt
    step_index: Fact[NonNegativeInt]
    stage_index: Fact[Annotated[Integer, Field(ge=0, le=2)]]
    source_step_index: Fact[NonNegativeInt]
    source_stage_index: Fact[NonNegativeInt]
    physical_time: Fact[Number]
    interval: Fact[TimeInterval]
    value: Fact[Number]


class PageWindow(CanonicalModel):
    offset: NonNegativeInt
    limit: PositiveInt
    returned_count: NonNegativeInt
    total_count: NonNegativeInt
    has_more: bool

    @model_validator(mode="after")
    def page_bounds(self):
        if self.returned_count > min(self.limit, max(0, self.total_count - self.offset)):
            raise ValueError("Page counts exceed available records")
        if self.has_more != (self.offset + self.returned_count < self.total_count):
            raise ValueError("Page has_more must reflect remaining records")
        return self


class ScalarSeries(CanonicalModel):
    result: ScientificResult
    series_id: ID
    label: str
    total_point_count: NonNegativeInt
    points: list[ScalarPoint]
    page: PageWindow
    aggregation: Literal["NONE", "CUMULATIVE", "STEP_INCREMENT", "STAGE_AGGREGATE"]
    source_column: str
    definition_id: ID

    @model_validator(mode="after")
    def page_matches(self):
        if self.total_point_count != self.page.total_count or len(self.points) != self.page.returned_count:
            raise ValueError("Series counts must match the page")
        return self


class SnapshotAlignment(CanonicalModel):
    experiment_id: ID
    config_id: ID
    selection_policy: Literal["NEAREST_RECORDED", "PINNED"]
    selected_scalar_step: PositiveInt
    selected_scalar_time: Number
    displayed_snapshot_id: ID
    displayed_snapshot_index: PositiveInt
    displayed_snapshot_time: Number
    signed_time_delta: Number
    limitations: list[ScientificLimitation]

    @model_validator(mode="after")
    def delta_matches(self):
        if self.signed_time_delta != self.displayed_snapshot_time - self.selected_scalar_time:
            raise ValueError("Alignment delta is displayed time minus selected time")
        return self


class EntropyHistory(CanonicalModel):
    experiment_id: ID
    config_id: ID
    series: list[ScalarSeries]
    stage_aggregate_refs: list[ID]
    snapshot_alignment: Fact[SnapshotAlignment]
    limitations: list[ScientificLimitation]
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def identities(self):
        if any((item.result.experiment_id, item.result.config_id) != (self.experiment_id, self.config_id) for item in self.series):
            raise ValueError("History series must match its identity")
        alignment = fact_value(self.snapshot_alignment)
        if alignment and (alignment.experiment_id, alignment.config_id) != (self.experiment_id, self.config_id):
            raise ValueError("History alignment must match its identity")
        return self


class DetectorSpec(CanonicalModel):
    id: ID
    name: str
    definition: str
    parameters: list[NamedFact]
    evidence_refs: list[ID]


class Metric(CanonicalModel):
    result: ScientificResult
    metric_id: ID
    value: Fact[Number]
    definition_id: ID
    detector: Fact[DetectorSpec]
    time_scope: TimeSpec
    display_label: str
    resolution_limit: Fact[Number]

    @model_validator(mode="after")
    def time_matches(self):
        if self.time_scope != self.result.time:
            raise ValueError("Metric time scope must equal result time")
        return self


class MetricCollection(CanonicalModel):
    experiment_id: ID
    config_id: ID
    items: list[ResourceSlot[Metric]]
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def identities(self):
        for slot in self.items:
            item = getattr(slot.root, "value", None)
            if item and (item.result.experiment_id, item.result.config_id) != (self.experiment_id, self.config_id):
                raise ValueError("Metric must match collection identity")
        return self


class ScientificDefinition(CanonicalModel):
    id: ID
    semantic_id: ID
    title: str
    definition: str
    time_rule: str
    spatial_rule: str
    unit: UnitSpec
    mask_refs: list[ID]
    detector: Fact[DetectorSpec]
    evidence_refs: list[ID]
    limitations: list[ScientificLimitation]
