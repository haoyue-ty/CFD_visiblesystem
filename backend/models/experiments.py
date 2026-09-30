from typing import Literal

from pydantic import model_validator

from .core import (Availability, CanonicalModel, CapabilityStatus, DeliveryStatus,
                   Fact, HashFact, ID, Number, SchemaVersion, ScientificLimitation,
                   UnitSpec, Verification, fact_value)
from .context import GridSpec


class AccountFeatureInfo(CanonicalModel):
    """Static feature metadata only; no account storage or operations."""
    enabled: bool
    status: Literal["AVAILABLE", "UNSUPPORTED", "ERROR"]
    registration_method: Literal["QQ_EMAIL_CODE"]


class ExperimentRef(CanonicalModel):
    experiment_id: ID
    name: str
    delivery_status: DeliveryStatus


class ProjectInfo(CanonicalModel):
    schema_version: SchemaVersion
    project_id: ID
    name: str
    architecture_style: str
    api_version: str
    registry_revision: ID
    data_revision: ID
    release_id: Fact[ID]
    replay_primary: bool
    live_demo_priority: str
    top_level_navigation: list[str]
    page_template_ids: list[ID]
    experiments: list[ExperimentRef]
    account_extension: AccountFeatureInfo
    limitations: list[ScientificLimitation]


class ParameterValue(CanonicalModel):
    name: Literal["q_aa", "q_at", "gate", "CFL", "epsilon", "ell", "mode"]
    value: Fact[Number | str]
    unit: UnitSpec

    @model_validator(mode="after")
    def parameter_type(self):
        value = fact_value(self.value)
        if value is not None:
            if self.name == "gate" and not isinstance(value, str):
                raise ValueError("Gate parameter is an enum string")
            if self.name != "gate" and isinstance(value, str):
                raise ValueError("Numeric parameters cannot be strings")
            if self.name in ("ell", "mode") and value != int(value):
                raise ValueError("Mode and ell must be integral")
        return self


class ProtocolSpec(CanonicalModel):
    method_name: Fact[str]
    method_hash: HashFact
    grid: Fact[GridSpec]
    integrator: Fact[str]
    reconstruction: Fact[str]
    final_time: Fact[Number]
    boundary_scope: Fact[str]
    protocol_asset_refs: list[ID]


class ExperimentConfig(CanonicalModel):
    id: ID
    experiment_id: ID
    name: str
    parameters: list[ParameterValue]
    protocol: ProtocolSpec
    verification: Verification
    limitations: list[ScientificLimitation]
    evidence_refs: list[ID]


class ConfigCapability(CanonicalModel):
    config_id: ID
    status: CapabilityStatus
    reason: str
    result_refs: list[ID]


class ControlSpec(CanonicalModel):
    name: str
    kind: Literal["ENUM", "RECORDED_INDEX"]
    allowed_values: list[str]
    combination_registry_ref: Fact[ID]


class TabPolicy(CanonicalModel):
    tab_id: str
    visible_for_family: bool
    disabled_for_configs: list[ID]
    unsupported_deep_link_behavior: Literal["EXPLAIN"]


class ExperimentCapability(CanonicalModel):
    id: ID
    experiment_id: ID
    task: str
    status: CapabilityStatus
    available_for_configs: list[ID]
    config_support: list[ConfigCapability]
    controls: list[ControlSpec]
    tab_policy: TabPolicy
    result_refs: list[ID]
    limitations: list[ScientificLimitation]
    evidence_refs: list[ID]


class Experiment(CanonicalModel):
    schema_version: SchemaVersion
    id: ID
    name: str
    scientific_family: str
    description: str
    capabilities: list[ExperimentCapability]
    available_configs: list[ExperimentConfig]
    status: Availability
    delivery_status: DeliveryStatus
    limitations: list[ScientificLimitation]
    evidence_refs: list[ID]
    related_experiment_ids: list[ID]

    @model_validator(mode="after")
    def identities(self):
        if any(item.experiment_id != self.id for item in [*self.available_configs, *self.capabilities]):
            raise ValueError("Experiment children must belong to the same experiment")
        return self
