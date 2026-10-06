from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class V2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False,
                              json_schema_serialization_defaults_required=True)


Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Profile = Literal["fast", "paper", "custom"]


class LiveInitialCondition(V2Model):
    base: Literal["STATIONARY_NORMAL_SHOCK"] = "STATIONARY_NORMAL_SHOCK"
    front_center: Finite = 0.5
    corrugation_amplitude: Finite = 0.0125
    wavelength_count: Annotated[int, Field(strict=True)] = 4
    transition_cells: Finite = 1.0
    transverse_seed_sound_speed_factor: Finite = 0.01
    transverse_seed_width: Finite = 0.04
    transverse_seed_phase: Finite = 0.0


class LivePhysics(V2Model):
    mach: Finite = 6.0
    gamma: Finite = 1.4
    initial_condition: LiveInitialCondition = Field(default_factory=LiveInitialCondition)


class LiveDomain(V2Model):
    x: tuple[Finite, Finite] = (0.0, 1.0)
    y: tuple[Finite, Finite] = (0.0, 1.0)


class LiveGrid(V2Model):
    nx: Annotated[int, Field(strict=True, ge=1, le=128)]
    ny: Annotated[int, Field(strict=True, ge=1, le=32)]
    domain: LiveDomain = Field(default_factory=LiveDomain)


class LiveTime(V2Model):
    cfl: Annotated[Finite, Field(gt=0, le=1)]
    final_time: Annotated[Finite, Field(gt=0, le=0.08)]
    integrator: Literal["SSP_RK3"] = "SSP_RK3"
    dt_strategy: Literal["INITIAL_STATE_FIXED_STEP"] = "INITIAL_STATE_FIXED_STEP"


class LiveMethod(V2Model):
    method_id: Literal["cross_mode_ec_unified_v1"] = "cross_mode_ec_unified_v1"
    q_aa: Annotated[Finite, Field(ge=0, le=13.2)]
    q_at: Annotated[Finite, Field(ge=0, le=0.396)]


class LiveDiscretization(V2Model):
    reconstruction: Literal["FIRST_ORDER"] = "FIRST_ORDER"
    x_lower: Literal["PRE_SHOCK_INFLOW"] = "PRE_SHOCK_INFLOW"
    x_upper: Literal["OUTFLOW"] = "OUTFLOW"
    y_boundary: Literal["PERIODIC"] = "PERIODIC"
    positivity_clipping: Annotated[bool, Field(strict=True)] = False
    artificial_viscosity: Annotated[bool, Field(strict=True)] = False


class LiveOutput(V2Model):
    snapshot_policy: Literal["SOURCE_CHECKPOINT_FRACTIONS"] = "SOURCE_CHECKPOINT_FRACTIONS"
    checkpoint_fractions: tuple[Finite, Finite, Finite, Finite, Finite, Finite] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


class LiveExperimentConfig(V2Model):
    schema_version: Literal["2.0.0"] = "2.0.0"
    protocol_revision: Literal["case8.protocol.p1.1"] = "case8.protocol.p1.1"
    case_id: Literal["case8"]
    profile: Profile
    physics: LivePhysics = Field(default_factory=LivePhysics)
    grid: LiveGrid
    time: LiveTime
    method: LiveMethod
    discretization: LiveDiscretization = Field(default_factory=LiveDiscretization)
    output: LiveOutput = Field(default_factory=LiveOutput)


class ExperimentSubmission(V2Model):
    input_mode: Literal["template", "form", "natural_language"]
    template_id: Annotated[str, Field(max_length=80)] | None = None
    natural_language_text: Annotated[str, Field(max_length=4000)] | None = None
    parser_version: Annotated[str, Field(max_length=80)] | None = None
    capability_revision: Annotated[str, Field(min_length=1, max_length=80)]


class ValidateExperimentRequest(V2Model):
    config: LiveExperimentConfig
    submission: ExperimentSubmission


class V2FieldIssue(V2Model):
    field: Annotated[str, Field(min_length=1, max_length=160)]
    reason: Annotated[str, Field(min_length=1, max_length=500)]


class V2ProtocolDiff(V2Model):
    field: str
    expected: Any
    actual: Any


class ValidatedExperiment(V2Model):
    normalized_config: LiveExperimentConfig
    requested_profile: Profile
    classification: Literal["LIVE_FAST_RUN", "LIVE_PAPER_PROFILE", "PAPER_SCALE_CUSTOM", "CUSTOM_RUN"]
    protocol_diff: list[V2ProtocolDiff]
    output_diff: list[V2ProtocolDiff]
    warnings: list[str]
    unsupported_fields: list[V2FieldIssue]
    config_hash: str
    capability_revision: str
    execution_available: bool = False


class LiveTemplate(V2Model):
    template_id: str
    label: str
    profile: Literal["fast", "paper"]
    benchmark_status: Literal["PENDING", "PASSED", "NOT_APPLICABLE"]
    config: LiveExperimentConfig


class ParameterCapability(V2Model):
    field_path: str
    label: str
    scope: Literal["INPUT", "OUTPUT"] = "INPUT"
    support: Literal["FIXED", "CANDIDATE", "UNSUPPORTED"]
    verified_values: list[Any] = Field(default_factory=list)
    candidate_values: list[Any] = Field(default_factory=list)
    unit: str
    source_refs: list[str]
    required_stage: str
    validation_ready: bool
    execution_verified: bool = False
    reason: str


class LiveCase(V2Model):
    case_id: Literal["case8"] = "case8"
    label: str
    capability_revision: str
    source_manifest_revision: str
    protocol_id: str
    input_validation_status: Literal["IMPLEMENTED"] = "IMPLEMENTED"
    execution_status: Literal["STANDALONE_VERIFIED", "LIVE_AVAILABLE"] = "STANDALONE_VERIFIED"
    execution_available: bool = False
    limitations: list[str]
    grid_pairs: list[tuple[int, int]]
    capabilities: list[ParameterCapability]
    templates: list[LiveTemplate]


class LiveCases(V2Model):
    cases: list[LiveCase]
    natural_language_available: bool


class NaturalLanguageRequest(V2Model):
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    capability_revision: str


class DraftParameters(V2Model):
    nx: Annotated[int, Field(strict=True)] | None = None
    ny: Annotated[int, Field(strict=True)] | None = None
    cfl: Finite | None = None
    final_time: Finite | None = None
    q_aa: Finite | None = None
    q_at: Finite | None = None
    mach: Finite | None = None
    gamma: Finite | None = None


class NaturalLanguageExtraction(V2Model):
    template_id: str | None
    parameters: DraftParameters
    unresolved_fields: list[V2FieldIssue]
    unsupported_fields: list[V2FieldIssue]
    warnings: list[Annotated[str, Field(max_length=500)]]


class ExperimentConfigDraft(V2Model):
    config: LiveExperimentConfig | None
    template_id: str | None
    unresolved_fields: list[V2FieldIssue]
    unsupported_fields: list[V2FieldIssue]
    warnings: list[str]
    parser_version: str
    source_text: str
    capability_revision: str
    validated: ValidatedExperiment | None
    ready_for_confirmation: bool


class V2ErrorTarget(V2Model):
    resource_type: str = "experiment"
    identity: str | None = None


class V2ErrorBody(V2Model):
    code: str
    message: str
    retryable: bool
    target: V2ErrorTarget = Field(default_factory=V2ErrorTarget)
    details: list[V2FieldIssue] = Field(default_factory=list)


class V2FailedEnvelope(V2Model):
    schema_version: Literal["2.0.0"] = "2.0.0"
    request_id: str
    error: V2ErrorBody


T = TypeVar("T")


class V2Envelope(V2Model, Generic[T]):
    schema_version: Literal["2.0.0"] = "2.0.0"
    request_id: str
    data: T
    warnings: list[str] = Field(default_factory=list)
