"""Canonical public models from frozen 05_DATA_SCHEMA.md sections 1–5."""
import re

from typing import Annotated, Generic, Literal, TypeVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, RootModel, model_serializer, model_validator

T = TypeVar("T")
ID = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")]
Text = Annotated[str, Field(min_length=1)]
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Integer = Annotated[int, Field(strict=True)]
NonNegativeInt = Annotated[Integer, Field(ge=0)]
PositiveInt = Annotated[Integer, Field(gt=0)]
SchemaVersion = Literal["1.0.0"]
Availability = Literal["AVAILABLE", "PARTIAL", "MISSING", "UNSUPPORTED", "ERROR"]
CapabilityStatus = Literal["SUPPORTED", "PARTIAL", "MISSING", "UNSUPPORTED"]
DeliveryStatus = Literal["PLANNED", "IMPLEMENTED"]
VerificationStatus = Literal["FROZEN_VERIFIED", "VERIFIED_NOT_FROZEN", "DERIVED_VERIFIED", "AVAILABLE_UNVERIFIED", "PARTIAL", "MISSING", "LEGACY", "SUPERSEDED", "NOT_APPLICABLE"]
DataOrigin = Literal["FROZEN_PRODUCTION", "VERIFIED_PRODUCTION", "VERIFIED_POSTPROCESS", "DIAGNOSTIC_RERUN", "MOCK", "SCHEMATIC", "LIVE_DEMO"]


_PUBLIC_LOCATOR = re.compile(r"file://[^\s]+|(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s]+|\\\\[^\s]+|(?<![\w:])/(?:home|Users|tmp|var|mnt|opt|workspace)/[^\s]+", re.IGNORECASE)


def _public_strings(value):
    if isinstance(value, str):
        return _PUBLIC_LOCATOR.sub("[source locator withheld]", value)
    if isinstance(value, dict):
        return {key: _public_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_public_strings(item) for item in value]
    return value


class CanonicalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @model_serializer(mode="wrap")
    def public_payload(self, handler):
        # Free text follows the same public locator prohibition as SourceAsset.
        return _public_strings(handler(self))


class KnownFact(CanonicalModel, Generic[T]):
    state: Literal["KNOWN"]
    value: T


class UnresolvedFact(CanonicalModel):
    state: Literal["UNKNOWN", "MISSING", "NOT_APPLICABLE"]
    reason: Text


class Fact(RootModel[Annotated[KnownFact[T] | UnresolvedFact, Field(discriminator="state")]], Generic[T]):
    """Absent facts have a reason and cannot carry a value or null."""


HashFact = Fact[Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]]


class ScientificLimitation(CanonicalModel):
    id: ID
    code: str
    description: str
    affected_refs: list[ID]
    severity: Literal["INFO", "WARNING", "BLOCKING"]


class UnitSpec(CanonicalModel):
    id: ID
    system: Literal["MODEL", "DIMENSIONLESS", "UNKNOWN"]
    quantity: str
    label: str
    si_mapping: Fact[str]


class Verification(CanonicalModel):
    status: VerificationStatus
    basis: list[str]
    verified_at: Fact[AwareDatetime]
    observation_at: Fact[AwareDatetime]
    evidence_refs: list[ID]

    @model_validator(mode="after")
    def verified_basis(self):
        if self.status in ("FROZEN_VERIFIED", "VERIFIED_NOT_FROZEN", "DERIVED_VERIFIED") and not self.basis:
            raise ValueError("Verified status requires an explicit verification basis")
        return self


class ProvenanceRef(CanonicalModel):
    evidence_refs: Annotated[list[ID], Field(min_length=1)]
    source_asset_ids: list[ID]
    registry_revision: ID
    data_revision: ID
    release_id: Fact[ID]
    source_drift: Fact[bool]


class ErrorTarget(CanonicalModel):
    resource_type: str
    identity: Fact[ID]


class ErrorDetail(CanonicalModel):
    field: str
    issue: str
    allowed_values: list[str]


class ErrorBody(CanonicalModel):
    domain: Literal["SYSTEM", "SCIENTIFIC", "ACCOUNT"]
    code: str
    message: str
    target: ErrorTarget
    retryable: bool
    details: list[ErrorDetail]
    evidence_refs: list[ID]


class AvailableSlot(CanonicalModel, Generic[T]):
    availability: Literal["AVAILABLE"]
    value: T


class PartialSlot(CanonicalModel, Generic[T]):
    availability: Literal["PARTIAL"]
    value: T
    issues: Annotated[list[ErrorBody], Field(min_length=1)]


class FailedSlot(CanonicalModel):
    availability: Literal["MISSING", "UNSUPPORTED", "ERROR"]
    error: ErrorBody


class ResourceSlot(RootModel[Annotated[AvailableSlot[T] | PartialSlot[T] | FailedSlot, Field(discriminator="availability")]], Generic[T]):
    pass


def known(value: T) -> dict:
    return {"state": "KNOWN", "value": value}


def unresolved(reason: str, state: Literal["UNKNOWN", "MISSING", "NOT_APPLICABLE"] = "UNKNOWN") -> dict:
    return {"state": state, "reason": reason}


def fact_value(fact: Fact[T]) -> T | None:
    return fact.root.value if isinstance(fact.root, KnownFact) else None
