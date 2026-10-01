"""Flask-independent DI seam for Window 2; no source path knowledge here."""
from pydantic import BaseModel

from backend.adapters import Case8AdapterProtocol
from backend.core.errors import system_error
from backend.models import (CapabilityList, ConfigList, EntropyHistory, EvidenceRecord,
                            Experiment, FieldResponse, FieldSnapshot, MetricCollection,
                            ResultProvenance, ScalarSeries, ScientificArray, SnapshotAlignment,
                            SnapshotIndex)


class Case8Service:
    def __init__(self, adapter: Case8AdapterProtocol | None):
        self.adapter = adapter

    def _call(self, method: str, model: type[BaseModel], *args, **kwargs):
        if self.adapter is None:
            raise system_error("FEATURE_NOT_ENABLED", "Case8 adapter has not been delivered",
                               status=503, retryable=True)
        try:
            value = getattr(self.adapter, method)(*args, **kwargs)
        except KeyError:
            code = {"load_snapshot_metadata": "SNAPSHOT_NOT_FOUND", "load_field": "SNAPSHOT_NOT_FOUND",
                    "load_snapshot_alignment": "SNAPSHOT_NOT_FOUND", "load_array": "INVALID_RESULT_ID",
                    "load_evidence": "UNKNOWN_EVIDENCE_ID", "load_provenance": "INVALID_RESULT_ID",
                    "load_scalar_series": "INVALID_RESULT_ID", "load_entropy_history": "INVALID_RESULT_ID"}.get(method, "UNKNOWN_CONFIG")
            raise system_error(code, "Requested scientific identity is not registered", status=404, availability="MISSING") from None
        except (FileNotFoundError, OSError):
            raise system_error("SOURCE_READ_ERROR", "Recorded scientific source could not be read") from None
        # Revalidate serialized model instances too; adapters cannot bypass validators.
        payload = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        return model.model_validate(payload)

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

    def load_snapshot_alignment(self, config_id: str, *, scalar_step: int,
                                policy: str = "NEAREST_RECORDED",
                                snapshot_index: int | None = None) -> SnapshotAlignment:
        return self._call("load_snapshot_alignment", SnapshotAlignment, config_id,
                          scalar_step=scalar_step, policy=policy, snapshot_index=snapshot_index)
