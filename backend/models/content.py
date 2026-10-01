"""Frozen 05 §15 content DTOs. No numerical result or array payloads."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from backend.models.core import CanonicalModel, Fact, ID, Integer, ScientificLimitation, Text
from backend.models.experiments import ControlSpec

MechanismState = Literal["STRICT_1D", "WEAKLY_2D"]
QatState = Literal["OFF", "ENABLED"]
ViewKind = Literal["MECHANISM", "ENTROPY", "ALLOCATION", "SPECTRUM", "CROSS_FLOW", "EVIDENCE"]


class MechanismNode(CanonicalModel):
    id: ID
    label: Text
    explanation: Text


class MechanismEdge(CanonicalModel):
    from_node: ID
    to_node: ID
    label: Text


class MechanismContent(CanonicalModel):
    content_id: ID
    data_origin: Literal["SCHEMATIC"]
    nodes: Annotated[list[MechanismNode], Field(min_length=1)]
    edges: Annotated[list[MechanismEdge], Field(min_length=1)]
    supported_states: list[MechanismState]
    evidence_refs: Annotated[list[ID], Field(min_length=1)]
    limitations: list[ScientificLimitation]

    @model_validator(mode="after")
    def graph_identity(self):
        identities = [node.id for node in self.nodes]
        if len(set(identities)) != len(identities):
            raise ValueError("Mechanism node identities must be unique")
        pairs = [(edge.from_node, edge.to_node) for edge in self.edges]
        if len(set(pairs)) != len(pairs):
            raise ValueError("Mechanism edges must be unique")
        if any(a not in identities or b not in identities or a == b for a, b in pairs):
            raise ValueError("Mechanism edges must reference distinct registered nodes")
        if sorted(self.supported_states) != ["STRICT_1D", "WEAKLY_2D"]:
            raise ValueError("Both frozen schematic states are required exactly once")
        return self


class ScientificTarget(CanonicalModel):
    experiment_id: ID
    config_id: Fact[ID]
    result_ids: Annotated[list[ID], Field(min_length=1)]


class ScenePreset(CanonicalModel):
    scene_id: Annotated[Integer, Field(ge=1, le=7)]
    title: Text
    conclusion: Text
    view_kind: ViewKind
    targets: list[ScientificTarget]
    allowed_controls: list[ControlSpec]
    evidence_refs: Annotated[list[ID], Field(min_length=1)]
    limitations: list[ScientificLimitation]


class SceneList(CanonicalModel):
    items: list[ScenePreset]

    @model_validator(mode="after")
    def seven_scenes(self):
        if [scene.scene_id for scene in self.items] != list(range(1, 8)):
            raise ValueError("Explore requires the ordered seven scenes with IDs 1..7")
        return self
