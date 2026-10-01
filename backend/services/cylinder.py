"""Flask-independent, validated Cylinder scientific service for CYL01..09.

Window 2 can inject the protocol without knowing any scientific source paths.
No route, application activation or API contract changes are made here.
"""
from pydantic import BaseModel

from backend.adapters.cylinder import CylinderAdapterProtocol
from backend.core.errors import DomainError, system_error
from backend.models.cylinder import AllocationResult, CylinderAllocationOverview
from backend.models import (CapabilityList, ConfigList, EntropyHistory, EvidenceRecord,
    Experiment, FieldResponse, FieldSnapshot, MetricCollection, ResultProvenance,
    ScalarSeries, ScientificArray, SnapshotIndex)


class CylinderService:
    def __init__(self, adapter: CylinderAdapterProtocol | None):
        self.adapter = adapter

    def _call(self, method, model: type[BaseModel], *args, **kwargs):
        if self.adapter is None:
            raise system_error("FEATURE_NOT_ENABLED", "Cylinder adapter is not enabled", status=503, retryable=True)
        try:
            value = getattr(self.adapter, method)(*args, **kwargs)
            payload = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
            return model.model_validate(payload)
        except DomainError:
            raise
        except (FileNotFoundError, OSError):
            raise system_error("SOURCE_READ_ERROR", "Saved Cylinder source could not be read") from None
        except (ValueError, TypeError, KeyError, AssertionError, IndexError):
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Cylinder scientific result failed canonical validation") from None

    def load_allocation_overview(self, config_id):
        return self._call("load_allocation_overview", CylinderAllocationOverview, config_id)

    def load_sectors(self, config_id):
        return self._call("load_sectors", AllocationResult, config_id)

    def load_front_band(self, config_id):
        return self._call("load_front_band", AllocationResult, config_id)

    def describe_experiment(self) -> Experiment:
        return self._call("describe_experiment", Experiment)

    def list_configs(self) -> ConfigList:
        return self._call("list_configs", ConfigList)

    def describe_capabilities(self) -> CapabilityList:
        return self._call("describe_capabilities", CapabilityList)

    def list_snapshots(self, config_id: str) -> SnapshotIndex:
        return self._call("list_snapshots", SnapshotIndex, config_id)

    def load_snapshot_metadata(self, config_id: str, snapshot_index: int) -> FieldSnapshot:
        return self._call("load_snapshot_metadata", FieldSnapshot, config_id, snapshot_index)

    def load_field(self, config_id: str, snapshot_index: int, field_id: str) -> FieldResponse:
        return self._call("load_field", FieldResponse, config_id, snapshot_index, field_id)

    def load_array(self, result_id: str, array_id: str) -> ScientificArray:
        return self._call("load_array", ScientificArray, result_id, array_id)

    def load_entropy_history(self, config_id: str, *, series: tuple[str, ...] | None = None,
                             offset: int = 0, limit: int = 2000) -> EntropyHistory:
        return self._call("load_entropy_history", EntropyHistory, config_id, series=series, offset=offset, limit=limit)

    def load_scalar_series(self, config_id: str, series_id: str, *, offset: int = 0,
                           limit: int = 2000) -> ScalarSeries:
        return self._call("load_scalar_series", ScalarSeries, config_id, series_id, offset=offset, limit=limit)

    def load_metrics(self, config_id: str, *, metric_id: str | None = None,
                     snapshot_index: int | None = None) -> MetricCollection:
        return self._call("load_metrics", MetricCollection, config_id, metric_id=metric_id, snapshot_index=snapshot_index)

    def load_evidence(self, evidence_id: str) -> EvidenceRecord:
        return self._call("load_evidence", EvidenceRecord, evidence_id)

    def load_provenance(self, result_id: str) -> ResultProvenance:
        return self._call("load_provenance", ResultProvenance, result_id)
