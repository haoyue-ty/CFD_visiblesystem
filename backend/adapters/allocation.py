"""Optional allocation extension; does not change Case8AdapterProtocol.

Implementers resolve registered identities under one pinned revision, read only,
and use frozen typed errors. No method accepts a path, time selector or free q.
"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from backend.models import ExperimentCapability, MaskSpec, ScientificArray, ScientificDefinition
from backend.models.allocation import (AllocationRepresentation, AllocationResult,
                                       AllocationSummary, MeasureDefinition)


@dataclass(frozen=True)
class AllocationDescription:
    """Internal description, not a replacement HTTP DTO or delivery declaration.

    definition retains time/spatial rules, unit, masks and evidence; detailed
    arrays/domains/measure/provenance arrive via load_allocation_metadata.
    """
    capability: ExperimentCapability
    representation_type: AllocationRepresentation
    measure_definition: MeasureDefinition
    coordinate_convention: str
    mask_definition: str
    definition: ScientificDefinition


@runtime_checkable
class AllocationAdapterProtocol(Protocol):
    def describe_allocation(self, experiment_id: str, config_id: str, *,
                            registry_revision: str | None = None) -> AllocationDescription: ...
    def load_allocation_metadata(self, result_id: str, *,
                                 registry_revision: str | None = None) -> AllocationResult: ...
    def load_allocation_array(self, result_id: str, array_id: str, *,
                              registry_revision: str | None = None) -> ScientificArray: ...
    def load_mask(self, mask_id: str, *,
                  registry_revision: str | None = None) -> MaskSpec: ...
    def load_summary_metrics(self, result_id: str, *,
                             registry_revision: str | None = None) -> AllocationSummary: ...
