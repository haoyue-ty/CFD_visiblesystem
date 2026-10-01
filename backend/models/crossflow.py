"""Frozen 05 §12 composite DTOs; no shared score or normalization."""
from typing import Literal

from pydantic import model_validator

from backend.models import (CanonicalModel, Fact, ID, MetricCollection, ProtocolSpec,
                            ResourceSlot, ScientificLimitation)
from backend.models.cylinder import AllocationResult


class CrossFlowSide(CanonicalModel):
    experiment_id: Literal["case8", "cylinder"]
    config_id: ID
    protocol: ProtocolSpec
    budget: ResourceSlot[MetricCollection]
    metrics: ResourceSlot[MetricCollection]
    allocation: ResourceSlot[AllocationResult]
    front_band: ResourceSlot[AllocationResult]
    snapshot_refs: list[ID]
    history_refs: list[ID]
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def child_identities(self):
        for slot in (self.budget, self.metrics, self.allocation, self.front_band):
            child = getattr(slot.root, "value", None)
            if child is None:
                continue
            identity = child.root.result if isinstance(child, AllocationResult) else child
            if (identity.experiment_id, identity.config_id) != (self.experiment_id, self.config_id):
                raise ValueError("Composite child must match its side identity")
        return self


class ComparabilityRule(CanonicalModel):
    left_definition_id: ID
    right_definition_id: ID
    status: Literal["DESCRIPTIVE_ONLY", "COMPATIBLE_WITH_DECLARED_MAPPING"]
    reason: str
    mapping_ref: Fact[ID]

    @model_validator(mode="after")
    def explicit_mapping(self):
        if not self.reason.strip():
            raise ValueError("Comparability requires an explicit reason")
        if self.status == "COMPATIBLE_WITH_DECLARED_MAPPING" and self.mapping_ref.root.state != "KNOWN":
            raise ValueError("Compatibility requires a declared mapping")
        return self


class CrossFlowComparison(CanonicalModel):
    comparison_id: ID
    left: CrossFlowSide
    right: CrossFlowSide
    comparability: list[ComparabilityRule]
    ranking_policy: Literal["NO_UNIFIED_RANKING"]
    limitations: list[ScientificLimitation]
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def ordered_sides(self):
        if (self.left.experiment_id, self.right.experiment_id) != ("case8", "cylinder"):
            raise ValueError("Frozen comparison has Case8 left and Cylinder right")
        return self
