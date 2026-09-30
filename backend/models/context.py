from typing import Annotated, Literal

from pydantic import Field, model_validator

from .core import CanonicalModel, Fact, ID, Integer, NonNegativeInt, Number, PositiveInt, UnitSpec, fact_value


class NamedFact(CanonicalModel):
    name: str
    value: Fact[Number | str]


class ScopeSpec(CanonicalModel):
    id: ID
    description: str
    boundary_scope: Fact[str]
    spatial_domain_ref: Fact[ID]
    mask_refs: list[ID]
    definition_refs: list[ID]


class TimeInterval(CanonicalModel):
    start: Number
    end: Number

    @model_validator(mode="after")
    def ordered(self):
        if self.start > self.end:
            raise ValueError("Time interval must be ordered")
        return self


class TimeSpec(CanonicalModel):
    sampling: Literal["STATIC", "TERMINAL", "MULTI_SNAPSHOT", "PER_STEP", "PER_STAGE"]
    accumulation: Literal["NONE", "TRAJECTORY_INTEGRATED", "STEP_INCREMENT", "STAGE_WEIGHTED_INCREMENT"]
    physical_time: Fact[Number]
    interval: Fact[TimeInterval]
    step_index: Fact[NonNegativeInt]
    stage_index: Fact[Annotated[Integer, Field(ge=0, le=2)]]
    snapshot_index: Fact[PositiveInt]
    index_convention: str


class AxisSize(CanonicalModel):
    axis: str
    size: PositiveInt


class AxisExtent(CanonicalModel):
    axis: str
    lower: Number
    upper: Number

    @model_validator(mode="after")
    def ordered(self):
        if self.lower >= self.upper:
            raise ValueError("Axis lower must be less than upper")
        return self


class GridSpec(CanonicalModel):
    coordinate_system: Literal["CARTESIAN", "CURVILINEAR_POLAR"]
    dimensions: list[AxisSize]
    extent: list[AxisExtent]


class MeasureConvention(CanonicalModel):
    id: ID
    description: str
    integral_rule: str
    measure_parameters: list[NamedFact]
    includes_time_weights: bool
    includes_spatial_measure: bool


class AxisDescriptor(CanonicalModel):
    name: str
    size: PositiveInt
    coordinate_values: Fact[list[Number]]
    coordinate_array_ref: Fact["ArrayRef"]
    unit: UnitSpec

    @model_validator(mode="after")
    def coordinates(self):
        values = fact_value(self.coordinate_values)
        ref = fact_value(self.coordinate_array_ref)
        if values is not None and ref is not None:
            raise ValueError("Coordinate values and array reference are exclusive")
        if values is not None and len(values) != self.size:
            raise ValueError("Coordinate count must match axis size")
        if ref is not None and ref.descriptor.shape != [self.size]:
            raise ValueError("Coordinate array must match axis size")
        return self


class SpatialDomain(CanonicalModel):
    id: ID
    coordinate_system: Literal["CARTESIAN", "CURVILINEAR_POLAR", "FOURIER_PROFILE", "ANGULAR"]
    location_type: Literal["CARTESIAN_CELL", "CARTESIAN_X_FACE", "CARTESIAN_Y_FACE", "CARTESIAN_ROW", "CYLINDER_RADIAL_FACE", "CYLINDER_ANGULAR_FACE", "CYLINDER_ANGULAR_SECTOR", "CYLINDER_FRONT_BAND", "PROFILE_CELL"]
    shape: list[PositiveInt]
    axes: list[AxisDescriptor]
    extent: list[AxisExtent]
    measure_convention: MeasureConvention
    boundary_scope: Fact[str]
    geometry_ref: Fact["ArrayRef"]
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def dimensions_match(self):
        if self.shape != [axis.size for axis in self.axes]:
            raise ValueError("Domain shape must match axis sizes")
        return self


class MaskIndexSet(CanonicalModel):
    axis: str
    indices: list[NonNegativeInt]
    index_base: Annotated[Integer, Field(ge=0, le=1)]


# ArrayRef lives in results.py. The package rebuilds forward references once.
