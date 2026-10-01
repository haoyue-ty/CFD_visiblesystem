"""Phase 6A schema subset of frozen 05 §9; no loaders or HTTP operations.

AllocationRepresentation is an internal capability vocabulary. Cylinder's frozen
wire discriminator remains ANGULAR_SECTORS; its result variant is deferred.
"""
from typing import Annotated, Literal

from pydantic import Field, RootModel, model_validator

from .core import CanonicalModel, ID, ResourceSlot, fact_value
from .context import MeasureConvention, ScopeSpec
from .results import ArrayRef, FieldDescriptor, Metric, ScientificResult

AllocationRepresentation = Literal["FACE_FIELD", "CELL_FIELD", "ANGULAR_SECTOR"]
MeasureDefinition = Literal["face integrated", "cell integrated", "sector aggregated"]
WIRE_REPRESENTATION: dict[AllocationRepresentation, str] = {
    "FACE_FIELD": "FACE_FIELD", "CELL_FIELD": "CELL_FIELD",
    "ANGULAR_SECTOR": "ANGULAR_SECTORS",
}


class SpatialCurve(CanonicalModel):
    result: ScientificResult
    axis: str
    coordinates: ArrayRef
    cumulative_fraction: ArrayRef
    definition_id: ID


class AllocationSummary(CanonicalModel):
    total_budget: ResourceSlot[Metric]
    inside: ResourceSlot[Metric]
    outside: ResourceSlot[Metric]
    fraction_format: Literal["FRACTION"]
    mask_refs: list[ID]
    measure: MeasureConvention
    spatial_cumulative_curve: ResourceSlot[SpatialCurve]
    evidence_refs: list[ID]


class AllocationField(CanonicalModel):
    result: ScientificResult
    summary: AllocationSummary
    fields: Annotated[list[FieldDescriptor], Field(min_length=1)]

    @model_validator(mode="after")
    def shared_context(self):
        header = self.result
        if header.time.accumulation != "TRAJECTORY_INTEGRATED":
            raise ValueError("Allocation is cumulative, not an instantaneous or step field")
        if not self.summary.measure.includes_time_weights:
            raise ValueError("Stored allocation already includes time/RK weights")
        if len({field.field_id for field in self.fields}) != len(self.fields):
            raise ValueError("Allocation field identities must be unique")
        for field in self.fields:
            other = field.result
            if (other.experiment_id, other.config_id, other.semantic_id, other.time,
                other.data_origin, other.unit, other.provenance.registry_revision,
                other.provenance.data_revision) != (
                header.experiment_id, header.config_id, header.semantic_id, header.time,
                header.data_origin, header.unit, header.provenance.registry_revision,
                header.provenance.data_revision):
                raise ValueError("Allocation fields must retain the same scientific context")
            if field.domain.measure_convention != self.summary.measure:
                raise ValueError("Field and summary must use the same measure convention")
            if field.domain.coordinate_system != "CARTESIAN" or [
                axis.name for axis in field.domain.axes
            ] != ["y", "x"]:
                raise ValueError("First-batch allocation retains Cartesian [y,x] axes")
            if not set(field.mask_refs).issubset(self.summary.mask_refs):
                raise ValueError("Field mask identities must be retained by the summary")
        for slot in (self.summary.total_budget, self.summary.inside, self.summary.outside):
            metric = getattr(slot.root, "value", None)
            if metric is not None and (
                metric.result.experiment_id, metric.result.config_id,
                metric.result.provenance.registry_revision, metric.result.provenance.data_revision
            ) != (header.experiment_id, header.config_id,
                  header.provenance.registry_revision, header.provenance.data_revision):
                raise ValueError("Summary metrics must retain allocation identity and revision")
            if metric is not None:
                if metric.time_scope.accumulation != "TRAJECTORY_INTEGRATED":
                    raise ValueError("Allocation summary cannot substitute an instantaneous metric")
                interval = fact_value(metric.time_scope.interval)
                if interval is not None and fact_value(header.time.interval) is not None and interval != fact_value(header.time.interval):
                    raise ValueError("Known summary and allocation integration intervals must agree")
        return self


class FaceAllocation(AllocationField):
    representation_type: Literal["FACE_FIELD"]

    @model_validator(mode="after")
    def native_faces(self):
        header = self.result
        if (header.experiment_id, header.config_id, header.semantic_id, header.time.sampling) != (
            "case8", "D_u", "Case8_face_Pi_at_integrated", "TERMINAL"
        ):
            raise ValueError("First-batch FACE_FIELD is terminal Case8 D_u native-face allocation")
        if header.data_origin not in ("DIAGNOSTIC_RERUN", "MOCK"):
            raise ValueError("Case8 cumulative map must retain DIAGNOSTIC_RERUN origin")
        locations = {field.domain.location_type: field.domain.shape for field in self.fields}
        if len(self.fields) != 2 or locations != {
            "CARTESIAN_X_FACE": [32, 129], "CARTESIAN_Y_FACE": [32, 128]
        }:
            raise ValueError("Native x/y faces cannot be replaced by a cell projection")
        if self.summary.measure.includes_spatial_measure:
            raise ValueError("Face values still require dy/dx spatial measures")
        return self


class CellAllocation(AllocationField):
    representation_type: Literal["CELL_FIELD"]

    @model_validator(mode="after")
    def integrated_cells(self):
        header = self.result
        if (header.experiment_id, header.semantic_id, header.time.sampling) != (
            "gate", "Gate_cell_Pi_at_integrated", "STATIC"
        ) or header.config_id not in ("Acoustic", "Pressure", "Ungated"):
            raise ValueError("First-batch CELL_FIELD is one of the three frozen Gate variants")
        if len(self.fields) != 1 or (
            self.fields[0].domain.location_type, self.fields[0].domain.shape
        ) != ("CARTESIAN_CELL", [32, 128]):
            raise ValueError("Gate allocation uses one 32x128 cell field")
        if not self.summary.measure.includes_spatial_measure:
            raise ValueError("Gate cells already include spatial measure; do not multiply again")
        return self


class AllocationResult(RootModel[Annotated[
    FaceAllocation | CellAllocation, Field(discriminator="representation_type")
]]):
    """First-batch subset only; Cylinder sector and REGION_SCALAR remain deferred."""


class AllocationArrayResponse(CanonicalModel):
    """One allocation field array whose header carries the wire representation.

    ``representation_type`` is mandatory on every allocation response so a client
    never has to infer face vs cell from array shape or field identity.
    """

    result: ScientificResult
    representation_type: AllocationRepresentation
    field_id: ID
    array_ref: ArrayRef
    values: list


class AllocationMetadata(CanonicalModel):
    """Registered allocation identity, measure, convention and mask refs.

    Metadata never embeds values; arrays load separately with their own headers.
    """

    result_id: ID
    experiment_id: ID
    config_id: ID
    semantic_id: ID
    representation_type: AllocationRepresentation
    wire_representation: str
    measure_definition: MeasureDefinition
    measure: MeasureConvention
    coordinate_convention: str
    mask_definition: str
    mask_refs: list[ID]
    domains: list[ID]
    array_refs: list[ArrayRef]
    evidence_refs: list[ID]
    scope: ScopeSpec
    result: ScientificResult


class AllocationComparisonEntry(CanonicalModel):
    """One comparable allocation variant with its own representation header."""

    result_id: ID
    config_id: ID
    representation_type: AllocationRepresentation
    wire_representation: str
    array_ref: ArrayRef
    summary: ResourceSlot[AllocationSummary]


class AllocationComparison(CanonicalModel):
    """Common extent/colour basis plus per-variant refs; no normalised values."""

    comparison_id: ID
    experiment_id: ID
    representation_type: AllocationRepresentation
    shared_extent: list[ResourceSlot[Metric]]
    colour_scale: Literal["SHARED_COMPARISON_SCALE"]
    entries: Annotated[list[AllocationComparisonEntry], Field(min_length=1)]
    measure: MeasureConvention
    evidence_refs: list[ID]
