from typing import Annotated, Generic, Literal, TypeVar

from pydantic import Field, RootModel

from .core import CanonicalModel, ErrorBody, Fact, ID, SchemaVersion
from .experiments import Experiment, ExperimentCapability, ExperimentConfig
from .results import FieldDescriptor, FieldSnapshot

T = TypeVar("T")


class EnvelopeHeader(CanonicalModel):
    schema_version: SchemaVersion
    request_id: ID
    registry_revision: Fact[ID]
    data_revision: Fact[ID]


class AvailableEnvelope(EnvelopeHeader, Generic[T]):
    availability: Literal["AVAILABLE"]
    data: T
    issues: Annotated[list[ErrorBody], Field(max_length=0)]


class PartialEnvelope(EnvelopeHeader, Generic[T]):
    availability: Literal["PARTIAL"]
    data: T
    issues: Annotated[list[ErrorBody], Field(min_length=1)]


class FailedEnvelope(EnvelopeHeader):
    availability: Literal["MISSING", "UNSUPPORTED", "ERROR"]
    error: ErrorBody
    issues: Annotated[list[ErrorBody], Field(max_length=0)]


class ApiEnvelope(RootModel[Annotated[AvailableEnvelope[T] | PartialEnvelope[T] | FailedEnvelope, Field(discriminator="availability")]], Generic[T]):
    pass


class ExperimentList(CanonicalModel):
    items: list[Experiment]


class ConfigList(CanonicalModel):
    experiment_id: ID
    items: list[ExperimentConfig]


class CapabilityList(CanonicalModel):
    experiment_id: ID
    items: list[ExperimentCapability]


class FieldResponse(CanonicalModel):
    snapshot: FieldSnapshot
    field: FieldDescriptor
