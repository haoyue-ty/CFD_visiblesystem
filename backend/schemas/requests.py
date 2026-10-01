"""Request models from FROZEN 06_API_CONTRACT.md section 4.

Each request model declares both the query fields and the path selectors for its operation,
so the exported OpenAPI parameters and the runtime payload parse from one declaration.

Numeric path selectors stay declared as ``Integer`` rather than ``PositiveInt``: the
catalog parses them before model validation, which lets ``snapshots/0`` be rejected as a
syntax error (400 INVALID_REQUEST) instead of being coerced to a valid initial state.
"""
from typing import Annotated, Literal

from pydantic import Field

from backend.models import CanonicalModel, ID, Integer, NonNegativeInt, PositiveInt


class RegistryQuery(CanonicalModel):
    registry_revision: ID | None = None


class ExperimentPath(RegistryQuery):
    experiment_id: ID


class ConfigQuery(RegistryQuery):
    config_id: ID


class SnapshotQuery(RegistryQuery):
    config_id: ID
    snapshot_index: Integer
    field: ID | None = None


class FieldQuery(RegistryQuery):
    config_id: ID
    snapshot_index: Integer
    field_id: ID


class HistoryQuery(RegistryQuery):
    config_id: ID
    series: list[ID] = []
    offset: NonNegativeInt = 0
    limit: Annotated[Integer, Field(ge=1, le=5000)] = 2000


class ScalarSeriesQuery(RegistryQuery):
    config_id: ID
    series_id: ID
    offset: NonNegativeInt = 0
    limit: Annotated[Integer, Field(ge=1, le=5000)] = 2000


class MetricQuery(RegistryQuery):
    config_id: ID
    metric_id: ID | None = None
    snapshot_index: PositiveInt | None = None


class AlignmentQuery(RegistryQuery):
    config_id: ID
    scalar_step: PositiveInt
    policy: Literal["NEAREST_RECORDED", "PINNED"] = "NEAREST_RECORDED"
    snapshot_index: PositiveInt | None = None


class EvidenceQuery(RegistryQuery):
    experiment_id: ID | None = None
    status: Literal["FROZEN_VERIFIED", "VERIFIED_NOT_FROZEN", "DERIVED_VERIFIED",
                    "AVAILABLE_UNVERIFIED", "PARTIAL", "MISSING", "LEGACY",
                    "SUPERSEDED", "NOT_APPLICABLE"] | None = None
    section: Literal["CURRENT", "GAPS", "HISTORY", "ALL"] = "CURRENT"
    offset: NonNegativeInt = 0
    limit: Annotated[Integer, Field(ge=1, le=200)] = 50


class ArrayQuery(RegistryQuery):
    """format is fixed FLAT_JSON; no user dtype/member/path/downsample is accepted."""

    result_id: ID
    array_id: ID


class ProvenanceQuery(RegistryQuery):
    result_id: ID


class IdentityQuery(RegistryQuery):
    """Path-only identity selector for EVI02 and EVI04."""

    evidence_id: ID | None = None
    asset_id: ID | None = None


class AllocationQuery(RegistryQuery):
    """Allocation identity selector; representation is server-declared, never a guess."""

    result_id: ID


class AllocationArrayQuery(AllocationQuery):
    """One registered allocation field array; no user dtype/member/path is accepted."""

    array_id: ID


class AllocationComparisonQuery(RegistryQuery):
    """Comparison scope selector; the three frozen Gate variants when omitted."""

    experiment_id: ID = "gate"
    representation_type: Literal["FACE_FIELD", "CELL_FIELD", "ANGULAR_SECTOR"] | None = None
