"""Scoped materialization of frozen Cylinder 05 §9/§12 DTOs.

Existing Phase4/6 public model exports and OpenAPI components remain unchanged.
Window2 should import the complete frozen union from this module for CYL06..08.
"""
from typing import Annotated, Literal

from pydantic import Field, RootModel, model_validator

from .allocation import AllocationSummary, FaceAllocation, CellAllocation
from .core import CanonicalModel, Fact, ID, Number, ResourceSlot, ScientificLimitation
from .results import ArrayRef, ScientificResult
from .evidence import MaskSpec


class ChannelArray(CanonicalModel):
    channel: Literal["bg", "aa", "at", "total"]
    array_ref: ArrayRef


class SectorAllocation(CanonicalModel):
    """Materializes the already frozen 05 §9 Cylinder variant."""
    result: ScientificResult
    representation_type: Literal["ANGULAR_SECTORS"]
    summary: AllocationSummary
    sector_count: Literal[16]
    bin_edges: ArrayRef
    channel_arrays: list[ChannelArray]
    sector_fractions: list[Fact[Number]]
    front_band_summary_ref: ID

    @model_validator(mode="after")
    def native_bins(self):
        if self.bin_edges.descriptor.shape != [17]:
            raise ValueError("Cylinder has exactly 17 angular edges")
        if [a.channel for a in self.channel_arrays] != ["bg", "aa", "at", "total"]:
            raise ValueError("Cylinder retains all four channels in source order")
        if any(a.array_ref.descriptor.shape != [16] for a in self.channel_arrays):
            raise ValueError("Each channel has exactly 16 sectors")
        if len(self.sector_fractions) != 16:
            raise ValueError("One acoustic-transverse fraction per sector required")
        if self.bin_edges.result_id == self.result.result_id:
            raise ValueError("Angle geometry requires a separate result and unit")
        if self.result.time.accumulation != "TRAJECTORY_INTEGRATED":
            raise ValueError("Sectors are trajectory integrated")
        return self


class RegionAllocation(CanonicalModel):
    result: ScientificResult
    representation_type: Literal["REGION_SCALAR"]
    summary: AllocationSummary
    region_mask: MaskSpec
    integrated_value: Fact[Number]
    fraction: Fact[Number]
    denominator_result_id: ID

    @model_validator(mode="after")
    def cumulative_band(self):
        if self.result.time.accumulation != "TRAJECTORY_INTEGRATED":
            raise ValueError("Front band is cumulative, not a terminal rate")
        if self.region_mask.type != "CYLINDER_FIXED_FRONT_BAND":
            raise ValueError("Cylinder band requires the frozen radial mask")
        return self


class AllocationResult(RootModel[Annotated[
    FaceAllocation | CellAllocation | SectorAllocation | RegionAllocation,
    Field(discriminator="representation_type")
]]):
    """Four representations defined by frozen 05 §9."""


class CylinderAllocationOverview(CanonicalModel):
    experiment_id: Literal["cylinder"]
    config_id: ID
    sectors: ResourceSlot[AllocationResult]
    front_band: ResourceSlot[AllocationResult]
    cumulative_2d: ResourceSlot[AllocationResult]
    limitations: list[ScientificLimitation]
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def frozen_gap_and_identity(self):
        if self.config_id not in ("A_u", "B_u", "D_u"):
            raise ValueError("Cylinder only registers A_u, B_u and D_u")
        if self.cumulative_2d.root.availability != "MISSING":
            raise ValueError("Selected Cylinder cumulative 2D must remain MISSING")
        for slot in (self.sectors, self.front_band):
            value = getattr(slot.root, "value", None)
            if value and (value.root.result.experiment_id, value.root.result.config_id) != (self.experiment_id, self.config_id):
                raise ValueError("Cylinder overview result identity must match")
        return self
