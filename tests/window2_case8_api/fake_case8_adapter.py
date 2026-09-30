"""TEST-ONLY Case8 adapter standing in for the Window 1 scientific adapter.

This module is deliberately confined to the test tree and is never imported by
``backend.registry`` or any production composition root. Every payload it returns is marked
``MOCK`` and uses the ``mock.`` result namespace required by ScientificResult, so these
values can never be mistaken for reproduced Case8 science.

Structure mirrors the real Case8 slice (six recorded 1-based snapshots, a 1912-point
scalar history) because the API contract's counting and pagination rules are the thing
under test, not the numbers themselves.
"""
from backend.models import (ArrayDescriptor, ArrayRef, CapabilityList, ConfigCapability,
                            ConfigList, ControlSpec, DetectorSpec, EntropyHistory,
                            EvidenceRecord, EvidenceIndexItem, Experiment, ExperimentCapability,
                            ExperimentConfig, FieldDescriptor, FieldResponse, FieldSnapshot,
                            FreezeReference, GridSpec, MaskSpec, Metric, MetricCollection,
                            PageWindow, ParameterValue, ProcessingRecord, ProtocolSpec,
                            ProvenanceRef, ResultProvenance, ScalarPoint, ScalarSeries,
                            ScientificArray, ScientificDefinition, ScientificResult,
                            SnapshotAlignment, SnapshotIndex, SourceAsset,
                            SourceObservation, SpatialDomain, TabPolicy, UnitSpec, Verification,
                            known, unresolved)

EXPERIMENT_ID = "case8"
CONFIG_IDS = ("A_u", "B_u", "D_u")
SNAPSHOT_INDEX = 6
HISTORY_POINTS = 1912
# Recorded step/time pairs for the six indices; index 6 is completed step 1912 at t=0.08.
SNAPSHOT_STEPS = ((1, 0, 0.0), (2, 382, 0.016), (3, 764, 0.032),
                  (4, 1146, 0.048), (5, 1529, 0.064), (6, 1912, 0.08))
CONVENTION = "USER_VISIBLE_1_BASED_RECORDED_INDEX"


def _unknown(reason: str) -> dict:
    return unresolved(reason)


def _na(reason: str) -> dict:
    return unresolved(reason, "NOT_APPLICABLE")


def _unit(quantity: str, label: str) -> UnitSpec:
    return UnitSpec(id=f"mock.unit.{quantity}", system="MODEL", quantity=quantity,
                    label=label, si_mapping=_unknown("No SI mapping in mock data"))


def _verification() -> Verification:
    return Verification(status="NOT_APPLICABLE", basis=["Test-only fake adapter"],
                        verified_at=_na("Mock data"), observation_at=_na("Mock data"),
                        evidence_refs=["mock.evidence.adapter"])


def _result(result_id: str, semantic_id: str, config_id: str, *,
            sampling: str = "MULTI_SNAPSHOT", accumulation: str = "NONE",
            snapshot_index: int | None = None, step_index: int | None = None,
            physical_time: float | None = None) -> ScientificResult:
    time: dict = {
        "sampling": sampling, "accumulation": accumulation,
        "physical_time": known(physical_time) if physical_time is not None else _unknown("No recorded time"),
        "interval": _na("Instantaneous recorded quantity"),
        "step_index": known(step_index) if step_index is not None else _unknown("No recorded step"),
        "stage_index": _na("No stage dimension"),
        "snapshot_index": known(snapshot_index) if snapshot_index is not None else _unknown("No snapshot selector"),
        "index_convention": CONVENTION,
    }
    return ScientificResult.model_validate({
        "schema_version": "1.0.0", "result_id": result_id, "experiment_id": EXPERIMENT_ID,
        "config_id": config_id, "semantic_id": semantic_id, "data_origin": "MOCK",
        "availability": "AVAILABLE", "time": time,
        "scope": {"id": f"mock.scope.{config_id}", "description": "Test-only scope",
                  "boundary_scope": _unknown("Not recorded in mock"),
                  "spatial_domain_ref": _na("Mock domain is inline"),
                  "mask_refs": [], "definition_refs": []},
        "unit": _unit(semantic_id, f"mock {semantic_id}"),
        "verification": _verification().model_dump(mode="python"),
        "provenance": ProvenanceRef(
            evidence_refs=["mock.evidence.adapter"], source_asset_ids=[],
            registry_revision="mock.registry", data_revision="mock.data",
            release_id=_na("No release in mock"), source_drift=_unknown("Mock data")).model_dump(mode="python"),
        "limitations": [],
    })


def _grid() -> GridSpec:
    return GridSpec.model_validate({
        "coordinate_system": "CARTESIAN",
        "dimensions": [{"axis": "y", "size": 32}, {"axis": "x", "size": 128}],
        "extent": [{"axis": "y", "lower": 0.0, "upper": 1.0},
                   {"axis": "x", "lower": 0.0, "upper": 4.0}],
    })


def _array_descriptor(array_id: str = "density") -> ArrayDescriptor:
    return ArrayDescriptor.model_validate({
        "array_id": array_id, "dtype": "float64", "shape": [32, 128], "order": "C",
        "axes": ["y", "x"], "encoding": "FLAT_JSON", "element_count": 4096,
    })


def _domain(config_id: str) -> SpatialDomain:
    def axis(name: str, size: int, lower: float, upper: float):
        return {"name": name, "size": size,
                "coordinate_values": _unknown("Coordinates are not mocked"),
                "coordinate_array_ref": _na("Coordinates are not mocked"),
                "unit": _unit(name, f"mock {name} axis").model_dump(mode="python")}
    return SpatialDomain.model_validate({
        "id": f"mock.domain.{config_id}.face", "coordinate_system": "CARTESIAN",
        "location_type": "CARTESIAN_CELL", "shape": [32, 128],
        "axes": [axis("y", 32, 0.0, 1.0), axis("x", 128, 0.0, 4.0)],
        "extent": [{"axis": "y", "lower": 0.0, "upper": 1.0},
                   {"axis": "x", "lower": 0.0, "upper": 4.0}],
        "measure_convention": {"id": "mock.measure", "description": "Test-only measure",
                               "integral_rule": "SUM", "measure_parameters": [],
                               "includes_time_weights": False, "includes_spatial_measure": True},
        "boundary_scope": _unknown("Not recorded in mock"),
        "geometry_ref": _na("No geometry array in mock"),
        "evidence_refs": ["mock.evidence.adapter"],
    })


def _field(config_id: str, snapshot_index: int, step_index: int,
           physical_time: float, field_id: str) -> FieldDescriptor:
    result = _result(f"mock.{EXPERIMENT_ID}.{config_id}.snapshot.{snapshot_index}.{field_id}",
                     field_id, config_id, snapshot_index=snapshot_index,
                     step_index=step_index, physical_time=physical_time)
    return FieldDescriptor.model_validate({
        "field_id": field_id, "label": f"Mock {field_id}", "result": result,
        "domain": _domain(config_id),
        "array_ref": {"result_id": result.result_id, "descriptor": _array_descriptor(field_id)},
        "mask_refs": [],
    })


def _snapshot(config_id: str, index: int, step: int, time: float) -> FieldSnapshot:
    result = _result(f"mock.{EXPERIMENT_ID}.{config_id}.snapshot.{index}", "snapshot",
                     config_id, snapshot_index=index, step_index=step, physical_time=time)
    return FieldSnapshot.model_validate({
        "result": result, "snapshot_id": f"{config_id}.{index}", "snapshot_index": index,
        "step_index": step, "physical_time": time, "grid": _grid(),
        "fields": [_field(config_id, index, step, time, "density"),
                   _field(config_id, index, step, time, "Pi_at")],
    })


def _scalar_series(config_id: str, series_id: str, offset: int, limit: int) -> ScalarSeries:
    total = HISTORY_POINTS
    stop = min(offset + limit, total)
    points = []
    for point_index in range(offset, stop):
        points.append(ScalarPoint.model_validate({
            # source_step_index stays 0-based while canonical step_index stays 1-based.
            "point_index": point_index, "step_index": known(point_index + 1),
            "stage_index": _na("No stage dimension"),
            "source_step_index": known(point_index),
            "source_stage_index": _na("No stage dimension"),
            "physical_time": known(round(point_index * 0.08 / 1911, 12)),
            "interval": _na("Instantaneous recorded quantity"),
            "value": known(float(point_index)),
        }))
    return ScalarSeries.model_validate({
        "result": _result(f"mock.{EXPERIMENT_ID}.{config_id}.{series_id}.cumulative", series_id,
                          config_id, sampling="PER_STEP", accumulation="TRAJECTORY_INTEGRATED"),
        "series_id": series_id, "label": f"Mock {series_id}", "total_point_count": total,
        "points": points,
        "page": {"offset": offset, "limit": limit, "returned_count": len(points),
                 "total_count": total, "has_more": offset + len(points) < total},
        "aggregation": "CUMULATIVE", "source_column": "mock_value", "definition_id": "mock.definition",
    })


class FakeCase8Adapter:
    """Contract test double. Not a scientific parser and never registered as one."""

    label = "TEST_ONLY_FAKE_CASE8_ADAPTER"

    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    # --- registry ---------------------------------------------------------------
    def describe_experiment(self) -> Experiment:
        self._record("describe_experiment")
        configs = [ExperimentConfig.model_validate({
            "id": config_id, "experiment_id": EXPERIMENT_ID, "name": config_id,
            "parameters": [ParameterValue.model_validate({
                "name": "gate", "value": known("Ungated"),
                "unit": _unit("gate", "mock gate").model_dump(mode="python")})],
            "protocol": ProtocolSpec.model_validate({
                "method_name": _unknown("Not recorded in mock"),
                "method_hash": known("a" * 64),
                "grid": known(_grid().model_dump(mode="python")),
                "integrator": _unknown("Not recorded in mock"),
                "reconstruction": _unknown("Not recorded in mock"),
                "final_time": known(0.08), "boundary_scope": _unknown("Not recorded in mock"),
                "protocol_asset_refs": []}),
            "verification": _verification(), "limitations": [],
            "evidence_refs": ["mock.evidence.adapter"]}) for config_id in CONFIG_IDS]
        capability = ExperimentCapability.model_validate({
            "id": "mock.capability.flow", "experiment_id": EXPERIMENT_ID, "task": "FLOW",
            "status": "SUPPORTED", "available_for_configs": list(CONFIG_IDS),
            "config_support": [ConfigCapability(config_id=config_id, status="SUPPORTED",
                                                reason="Mock capability", result_refs=[])
                               for config_id in CONFIG_IDS],
            "controls": [ControlSpec(name="gate", kind="ENUM", allowed_values=["Ungated"],
                                     combination_registry_ref=_unknown("Not recorded in mock"))],
            "tab_policy": TabPolicy(tab_id="flow", visible_for_family=True,
                                    disabled_for_configs=[],
                                    unsupported_deep_link_behavior="EXPLAIN"),
            "result_refs": [], "limitations": [], "evidence_refs": ["mock.evidence.adapter"]})
        return Experiment.model_validate({
            "schema_version": "1.0.0", "id": EXPERIMENT_ID, "name": "Case8 (mock)",
            "scientific_family": "case8", "description": "Test-only fake adapter metadata",
            "capabilities": [capability], "available_configs": configs,
            "status": "AVAILABLE", "delivery_status": "IMPLEMENTED", "limitations": [],
            "evidence_refs": ["mock.evidence.adapter"], "related_experiment_ids": []})

    def list_configs(self) -> ConfigList:
        self._record("list_configs")
        return ConfigList(experiment_id=EXPERIMENT_ID, items=self.describe_experiment().available_configs)

    def describe_capabilities(self) -> CapabilityList:
        self._record("describe_capabilities")
        return CapabilityList(experiment_id=EXPERIMENT_ID,
                              items=self.describe_experiment().capabilities)

    # --- snapshots --------------------------------------------------------------
    def list_snapshots(self, config_id: str) -> SnapshotIndex:
        self._record("list_snapshots", config_id)
        return SnapshotIndex.model_validate({
            "experiment_id": EXPERIMENT_ID, "config_id": config_id,
            "snapshot_count": len(SNAPSHOT_STEPS),
            "items": [_snapshot(config_id, index, step, time)
                      for index, step, time in SNAPSHOT_STEPS]})

    def load_snapshot_metadata(self, config_id: str, snapshot_index: int) -> FieldSnapshot:
        self._record("load_snapshot_metadata", config_id, snapshot_index)
        if not 1 <= snapshot_index <= SNAPSHOT_INDEX:
            from backend.core.errors import missing_resource
            raise missing_resource(
                "SNAPSHOT_NOT_FOUND", "No recorded snapshot at this index",
                resource_type="case8_snapshot",
                identity=known(f"{config_id}.snapshot.{snapshot_index}"))
        index, step, time = SNAPSHOT_STEPS[snapshot_index - 1]
        return _snapshot(config_id, index, step, time)

    def load_field(self, config_id: str, snapshot_index: int, field_id: str) -> FieldResponse:
        self._record("load_field", config_id, snapshot_index, field_id)
        snapshot = self.load_snapshot_metadata(config_id, snapshot_index)
        for field in snapshot.fields:
            if field.field_id == field_id:
                return FieldResponse(snapshot=snapshot, field=field)
        from backend.core.errors import missing_resource
        raise missing_resource("SNAPSHOT_NOT_FOUND", "No recorded field at this snapshot",
                               resource_type="case8_field",
                               identity=known(f"{config_id}.snapshot.{snapshot_index}.{field_id}"))

    # --- arrays -----------------------------------------------------------------
    def load_array(self, result_id: str, array_id: str) -> ScientificArray:
        self._record("load_array", result_id, array_id)
        parts = result_id.split(".")
        config_id, snapshot_index = parts[2], int(parts[4])
        index, step, time = SNAPSHOT_STEPS[snapshot_index - 1]
        result = _result(result_id, array_id, config_id, snapshot_index=index,
                         step_index=step, physical_time=time)
        return ScientificArray.model_validate({
            "result": result, "descriptor": _array_descriptor(array_id),
            "values": [float(value) for value in range(4096)]})

    # --- history / metrics ------------------------------------------------------
    def load_entropy_history(self, config_id: str, *, series=None, offset: int = 0,
                             limit: int = 2000) -> EntropyHistory:
        self._record("load_entropy_history", config_id, series=series, offset=offset, limit=limit)
        ids = series or ("E_at_cumulative",)
        return EntropyHistory.model_validate({
            "experiment_id": EXPERIMENT_ID, "config_id": config_id,
            "series": [_scalar_series(config_id, series_id, offset, limit) for series_id in ids],
            "stage_aggregate_refs": [], "snapshot_alignment": _na("No scalar selection in history"),
            "limitations": [], "evidence_refs": ["mock.evidence.adapter"]})

    def load_scalar_series(self, config_id: str, series_id: str, *, offset: int = 0,
                           limit: int = 2000) -> ScalarSeries:
        self._record("load_scalar_series", config_id, series_id, offset=offset, limit=limit)
        return _scalar_series(config_id, series_id, offset, limit)

    def load_metrics(self, config_id: str, *, metric_id=None, snapshot_index=None) -> MetricCollection:
        self._record("load_metrics", config_id, metric_id=metric_id, snapshot_index=snapshot_index)
        definition = DetectorSpec(id="mock.detector", name="Mock detector",
                                  definition="Test-only detector", parameters=[],
                                  evidence_refs=["mock.evidence.adapter"])
        metric = Metric.model_validate({
            "result": _result(f"mock.{EXPERIMENT_ID}.{config_id}.metric.shock-width", "shock-width",
                              config_id, sampling="TERMINAL"),
            "metric_id": metric_id or "shock-width", "value": known(0.25),
            "definition_id": "mock.definition", "detector": known(definition.model_dump(mode="python")),
            "time_scope": _result(f"mock.{EXPERIMENT_ID}.{config_id}.metric.shock-width", "shock-width",
                                  config_id, sampling="TERMINAL").time.model_dump(mode="python"),
            "display_label": "Mock shock width",
            "resolution_limit": known(0.01)})
        return MetricCollection.model_validate({
            "experiment_id": EXPERIMENT_ID, "config_id": config_id,
            "items": [{"availability": "AVAILABLE", "value": metric.model_dump(mode="python")}],
            "evidence_refs": ["mock.evidence.adapter"]})

    def load_snapshot_alignment(self, config_id: str, *, scalar_step: int,
                                policy: str = "NEAREST_RECORDED",
                                snapshot_index: int | None = None) -> SnapshotAlignment:
        self._record("load_snapshot_alignment", config_id, scalar_step=scalar_step,
                     policy=policy, snapshot_index=snapshot_index)
        if policy == "PINNED" and snapshot_index is not None:
            index, step, time = SNAPSHOT_STEPS[snapshot_index - 1]
        else:
            # Deterministic same-distance rule: earlier time wins, so lowest index wins.
            index, step, time = min(SNAPSHOT_STEPS,
                                    key=lambda item: (abs(item[2] - scalar_step * 0.08 / 1911), item[0]))
        scalar_time = scalar_step * 0.08 / 1911
        return SnapshotAlignment.model_validate({
            "experiment_id": EXPERIMENT_ID, "config_id": config_id,
            "selection_policy": policy, "selected_scalar_step": scalar_step,
            "selected_scalar_time": scalar_time,
            "displayed_snapshot_id": f"{config_id}.{index}", "displayed_snapshot_index": index,
            "displayed_snapshot_time": time,
            "signed_time_delta": time - scalar_time, "limitations": []})

    # --- evidence ---------------------------------------------------------------
    def load_evidence(self, evidence_id: str) -> EvidenceRecord:
        self._record("load_evidence", evidence_id)
        if not evidence_id.startswith("mock."):
            from backend.core.errors import missing_resource
            raise missing_resource("UNKNOWN_EVIDENCE_ID", "Unknown evidence identity",
                                   resource_type="evidence",
                                   identity=unresolved("Not present in the registry index"))
        result = _result("mock.case8.D_u.snapshot.6.density", "density", "D_u",
                         snapshot_index=6, step_index=1912, physical_time=0.08)
        return EvidenceRecord.model_validate({
            "schema_version": "1.0.0", "evidence_id": evidence_id,
            "result_ids": [result.result_id],
            "result_contexts": [result.model_dump(mode="python")],
            "experiment_id": known(EXPERIMENT_ID), "config_id": known("D_u"),
            "config": _unknown("Configuration is not mocked"),
            "definitions": [], "masks": [], "method_name": _unknown("Not recorded in mock"),
            "method_hash": known("b" * 64), "recorded_source_hash": known("c" * 64),
            "current_source_hash": known("c" * 64),
            "source_observations": [SourceObservation(asset_id="mock_asset", recorded_hash=known("c" * 64),
                                                      current_hash=known("c" * 64),
                                                      drift=known(False),
                                                      observation_at=_unknown("Not observed")).model_dump(mode="python")],
            "source_assets": [SourceAsset.model_validate({
                "asset_id": "mock_asset", "source_id": "mock_source",
                "source_display": "Test-only source", "relative_origin": _unknown("No origin in mock"),
                "role": "DATA", "format": "mock", "recorded_data_hash": known("c" * 64),
                "current_data_hash": known("c" * 64), "data_drift": known(False),
                "verification": _verification(), "canonical_selected": True,
                "limitations": []}).model_dump(mode="python")],
            "data_hash": known("c" * 64),
            "freeze_reference": _na("No freeze in mock"), "processing": [],
            "verification": _verification(), "limitations": [],
            "source_drift": known(False), "created_at": _unknown("Not recorded in mock"),
            "verified_at": _na("Mock data"), "related_evidence_refs": [],
            "superseded_by": _na("Not superseded")})

    def load_provenance(self, result_id: str) -> ResultProvenance:
        self._record("load_provenance", result_id)
        if "missing" in result_id:
            from backend.core.errors import missing_resource
            raise missing_resource("INVALID_RESULT_ID", "Unknown result identity",
                                   resource_type="result",
                                   identity=unresolved("Not present in the registry index"))
        return ResultProvenance.model_validate({
            "result_id": result_id,
            "provenance": ProvenanceRef(evidence_refs=["mock.evidence.adapter"], source_asset_ids=["mock_asset"],
                                        registry_revision="mock.registry", data_revision="mock.data",
                                        release_id=_na("No release in mock"),
                                        source_drift=_unknown("Mock data")).model_dump(mode="python"),
            "evidence_records": [self.load_evidence("mock.evidence.adapter").model_dump(mode="python")]})
