from typing import Literal

from pydantic import AwareDatetime, model_validator

from .core import CanonicalModel, Fact, HashFact, ID, ScientificLimitation, Verification
from .context import MaskIndexSet, NamedFact, ScopeSpec
from .experiments import ExperimentConfig
from .results import ArrayRef, PageWindow, ScientificDefinition, ScientificResult


class MaskSpec(CanonicalModel):
    """Dependency of EvidenceRecord, not an allocation adapter."""
    id: ID
    type: Literal["GATE_CELL_SHOCK_WINDOW", "CASE8_NATIVE_FACE_SHOCK_WINDOW", "SPECTRUM_FIXED_SHOCK_CELLS", "CYLINDER_FIXED_FRONT_BAND"]
    domain_refs: list[ID]
    definition: str
    parameters: list[NamedFact]
    index_sets: list[MaskIndexSet]
    mask_array_refs: list[ArrayRef]
    scope: ScopeSpec
    verification: Verification
    evidence_refs: list[ID]


class SourceAsset(CanonicalModel):
    asset_id: ID
    source_id: ID
    source_display: str
    relative_origin: Fact[str]
    role: Literal["DATA", "CONFIG", "METHOD", "MASK", "ANALYSIS", "FREEZE", "MISSING_REFERENCE"]
    format: str
    recorded_data_hash: HashFact
    current_data_hash: HashFact
    data_drift: Fact[bool]
    verification: Verification
    canonical_selected: bool
    limitations: list[ScientificLimitation]


class SourceObservation(CanonicalModel):
    asset_id: ID
    recorded_hash: HashFact
    current_hash: HashFact
    drift: Fact[bool]
    observation_at: Fact[AwareDatetime]


class FreezeReference(CanonicalModel):
    freeze_id: ID
    manifest_asset_id: ID
    recorded_at: Fact[AwareDatetime]
    hash: HashFact


class ProcessingRecord(CanonicalModel):
    id: ID
    kind: Literal["FORMAT_MAPPING", "METADATA_CORRECTION", "VERIFIED_DERIVATION", "DISPLAY_ONLY"]
    description: str
    input_asset_ids: list[ID]
    definition_refs: list[ID]
    processing_hash: HashFact
    verification: Verification


class EvidenceRecord(CanonicalModel):
    schema_version: Literal["1.0.0"]
    evidence_id: ID
    result_ids: list[ID]
    result_contexts: list[ScientificResult]
    experiment_id: Fact[ID]
    config_id: Fact[ID]
    config: Fact[ExperimentConfig]
    definitions: list[ScientificDefinition]
    masks: list[MaskSpec]
    method_name: Fact[str]
    method_hash: HashFact
    recorded_source_hash: HashFact
    current_source_hash: HashFact
    source_observations: list[SourceObservation]
    source_assets: list[SourceAsset]
    data_hash: HashFact
    freeze_reference: Fact[FreezeReference]
    processing: list[ProcessingRecord]
    verification: Verification
    limitations: list[ScientificLimitation]
    source_drift: Fact[bool]
    created_at: Fact[AwareDatetime]
    verified_at: Fact[AwareDatetime]
    related_evidence_refs: list[ID]
    superseded_by: Fact[ID]

    @model_validator(mode="after")
    def contexts_match(self):
        contexts = [result.result_id for result in self.result_contexts]
        if len(set(self.result_ids)) != len(self.result_ids) or sorted(contexts) != sorted(self.result_ids):
            raise ValueError("Evidence result contexts must correspond one-to-one to result ids")
        return self


class EvidenceIndexItem(CanonicalModel):
    evidence_id: ID
    result_ids: list[ID]
    experiment_id: Fact[ID]
    title: str
    verification: Verification
    source_drift: Fact[bool]
    limitations: list[ScientificLimitation]


class EvidenceIndex(CanonicalModel):
    items: list[EvidenceIndexItem]
    page: PageWindow


class ResultProvenance(CanonicalModel):
    result_id: ID
    provenance: "ProvenanceRef"
    evidence_records: list[EvidenceRecord]


from .core import ProvenanceRef
ResultProvenance.model_rebuild()
