"""Case8 adapter: reads the real scientific source and emits canonical models.

STRICT READ-ONLY. This module never writes, renames, deletes or modifies any
scientific file and never runs CFD. Every snapshot step/time/shape/field is read
from the recorded checkpoint; history rows are read from the recorded CSV. No
time interpolation, no rounding substitutes, no synthesised fields.
"""
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from backend.models import (CapabilityList, ConfigList, EntropyHistory, EvidenceRecord,
                            Experiment, FieldDescriptor, FieldResponse, FieldSnapshot,
                            MetricCollection, ResultProvenance, ScalarSeries, ScientificArray, SnapshotAlignment,
                            SnapshotIndex)
from backend.models.core import known, unresolved
from backend.registry import case8_evidence as EV
from backend.registry import case8_registry as REG
from backend.registry import case8_semantics as SEM
from backend.registry import case8_source_constants as C


@runtime_checkable
class Case8AdapterProtocol(Protocol):
    def describe_experiment(self) -> Experiment: ...
    def list_configs(self) -> ConfigList: ...
    def describe_capabilities(self) -> CapabilityList: ...
    def list_snapshots(self, config_id: str) -> SnapshotIndex: ...
    def load_snapshot_metadata(self, config_id: str, snapshot_index: int) -> FieldSnapshot: ...
    def load_field(self, config_id: str, snapshot_index: int, field_id: str) -> FieldResponse: ...
    def load_array(self, result_id: str, array_id: str) -> ScientificArray: ...
    def load_entropy_history(self, config_id: str, *, series: tuple[str, ...] | None = None,
                             offset: int = 0, limit: int = 2000) -> EntropyHistory: ...
    def load_scalar_series(self, config_id: str, series_id: str, *, offset: int = 0,
                           limit: int = 2000) -> ScalarSeries: ...
    def load_metrics(self, config_id: str, *, metric_id: str | None = None,
                     snapshot_index: int | None = None) -> MetricCollection: ...
    def load_evidence(self, evidence_id: str) -> EvidenceRecord: ...
    def load_provenance(self, result_id: str) -> ResultProvenance: ...
    def load_snapshot_alignment(self, config_id: str, *, scalar_step: int,
                                policy: str = "NEAREST_RECORDED",
                                snapshot_index: int | None = None) -> SnapshotAlignment: ...


SNAPSHOT_INDEX_CONVENTION = "USER_VISIBLE_1_BASED_RECORDED_INDEX"

_CONFIG_DIR: dict[str, str] = {
    "A_u": "03_case8_A_u", "B_u": "04_case8_B_u",
    "C_u": "06_case8_C_u", "D_u": "05_case8_D_u",
}


class Case8Adapter:
    """Concrete Case8 adapter over the read-only scientific root."""

    def __init__(self, scientific_root: str | Path = C.SCIENTIFIC_ROOT_WINDOWS):
        self._root = Path(scientific_root)
        self._hist_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------ paths
    def _checkpoint_path(self, config_id: str, source_step: int) -> Path:
        return self._root / C.CHECKPOINT_DIRS[config_id] / f"step_{source_step:06d}.npz"

    def _history_path(self, config_id: str) -> Path:
        return self._root / C.J2B_RUN_ROOT_REL / C.HISTORY_REL_TEMPLATE.format(config=config_id)

    # -------------------------------------------------------- snapshot lookup
    def _snapshot_lookup(self, config_id: str) -> dict[int, int]:
        return {item["snapshot_index"]: item["source_step_index"]
                for item in REG.snapshot_schedule(config_id)}

    def _source_step_for(self, config_id: str, snapshot_index: int) -> int:
        table = self._snapshot_lookup(config_id)
        if snapshot_index not in table:
            raise KeyError(f"configuration {config_id!r} has no snapshot_index {snapshot_index}")
        return table[snapshot_index]

    # ----------------------------------------------------------- NPZ reading
    def _read_checkpoint(self, config_id: str, source_step: int) -> dict:
        path = self._checkpoint_path(config_id, source_step)
        with np.load(path, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
            return {
                "source_step": int(arrays["step"]),
                "physical_time": float(arrays["time"]),
                "arrays": arrays,
            }

    # ============================================================ experiment
    def describe_experiment(self) -> Experiment:
        doc = REG.registry_document()
        return Experiment.model_validate({
            "schema_version": "1.0.0",
            "id": REG.EXPERIMENT_ID,
            "name": "Case8 Mach6",
            "scientific_family": "CARTESIAN_SHOCK_REPLAY",
            "description": "Four recorded configurations; six snapshots and 1912 scalar records per configuration",
            "capabilities": REG.capabilities(),
            "available_configs": doc["configs"],
            "status": "PARTIAL",
            "delivery_status": "IMPLEMENTED",
            "limitations": [{
                "id": "lim.case8.dense-fields", "code": "DISCRETE_RECORDED_ONLY",
                "description": "No per-step full state or all-stage spatial fields",
                "affected_refs": ["case8"], "severity": "WARNING",
            }],
            "evidence_refs": [C.ASSET_ID_METHOD],
            "related_experiment_ids": ["gate", "spectrum", "cylinder"],
        })

    def list_configs(self) -> ConfigList:
        return ConfigList.model_validate({
            "experiment_id": REG.EXPERIMENT_ID,
            "items": REG.registry_document()["configs"],
        })

    def describe_capabilities(self) -> CapabilityList:
        return CapabilityList.model_validate({
            "experiment_id": REG.EXPERIMENT_ID,
            "items": REG.capabilities(),
        })

    # ============================================================ snapshots
    def _snapshot_result(self, config_id: str, snapshot_index: int, source_step: int,
                         physical_time: float, semantic_id: str,
                         field_id: str | None = None) -> dict:
        rid = (f"case8.{config_id}.snapshot.{snapshot_index}" if field_id is None
               else f"case8.{config_id}.snapshot.{snapshot_index}.{field_id}")
        unit = SEM.UNIT_MODEL_ENERGY if field_id is None else SEM.FIELD_SEMANTICS[field_id]["unit"]
        asset_id = EV.checkpoint_asset_id(config_id, source_step)
        return {
            "schema_version": "1.0.0",
            "result_id": rid,
            "experiment_id": REG.EXPERIMENT_ID,
            "config_id": config_id,
            "semantic_id": semantic_id,
            "data_origin": "VERIFIED_PRODUCTION",
            "availability": "AVAILABLE",
            "time": {
                "sampling": "MULTI_SNAPSHOT",
                "accumulation": "NONE",
                "physical_time": known(physical_time),
                "interval": unresolved("Instantaneous state", "NOT_APPLICABLE"),
                "step_index": known(source_step),
                "stage_index": unresolved("Accepted-step endpoint snapshot", "NOT_APPLICABLE"),
                "snapshot_index": known(snapshot_index),
                "index_convention": SNAPSHOT_INDEX_CONVENTION,
            },
            "scope": {
                "id": "case8.cells",
                "description": f"Corrected Case8 {config_id} recorded endpoint",
                "boundary_scope": known("x_lower pre-shock inflow; x_upper outflow; y periodic"),
                "spatial_domain_ref": known("case8.cells"),
                "mask_refs": [],
                "definition_refs": [semantic_id],
            },
            "unit": unit,
            "verification": dict(EV._CHECKPOINT_VERIFICATION),
            "provenance": {
                "evidence_refs": [f"ev.case8.{config_id}.snapshot.{snapshot_index}"],
                "source_asset_ids": [asset_id],
                "registry_revision": REG.REGISTRY_REVISION,
                "data_revision": REG.DATA_REVISION,
                "release_id": unresolved("No release bundle created", "NOT_APPLICABLE"),
                "source_drift": unresolved("Observe all source dependencies before asserting false"),
            },
            "limitations": [dict(EV._UNIT_UNKNOWN_LIMITATION)],
        }

    def _field_descriptor(self, config_id: str, snapshot_index: int, source_step: int,
                          physical_time: float, field_id: str) -> dict:
        spec = SEM.FIELD_SEMANTICS[field_id]
        header = self._snapshot_result(config_id, snapshot_index, source_step,
                                       physical_time, spec["semantic_id"], field_id)
        shape = list(spec["shape"])
        axes = list(spec["axes"])
        length_unit = {
            "id": "model_length", "system": "MODEL", "quantity": "length",
            "label": "model length",
            "si_mapping": unresolved("No established SI mapping"),
        }
        domain = {
            "id": "case8.cells" if field_id != "front" else "case8.rows",
            "coordinate_system": "CARTESIAN",
            "location_type": spec["location_type"],
            "shape": shape,
            "axes": [{
                "name": ax, "size": sz,
                "coordinate_values": unresolved("Coordinates not bound in first slice"),
                "coordinate_array_ref": unresolved("No coordinate array selected", "NOT_APPLICABLE"),
                "unit": dict(length_unit),
            } for ax, sz in zip(axes, shape)],
            "extent": [{"axis": "x", "lower": C.DOMAIN_X[0], "upper": C.DOMAIN_X[1]},
                       {"axis": "y", "lower": C.DOMAIN_Y[0], "upper": C.DOMAIN_Y[1]}],
            "measure_convention": {
                "id": "case8.cell-measure",
                "description": "Uniform Cartesian cell measure",
                "integral_rule": "sum(value)",
                "measure_parameters": [],
                "includes_time_weights": False,
                "includes_spatial_measure": True,
            },
            "boundary_scope": known("x_lower pre-shock inflow; x_upper outflow; y periodic"),
            "geometry_ref": unresolved("Cartesian coordinate axes", "NOT_APPLICABLE"),
            "evidence_refs": [EV.checkpoint_asset_id(config_id, source_step)],
        }
        return {
            "field_id": field_id,
            "label": spec["label"],
            "result": header,
            "domain": domain,
            "array_ref": {
                "result_id": header["result_id"],
                "descriptor": {
                    "array_id": field_id,
                    "dtype": "float64",
                    "shape": shape,
                    "order": "C",
                    "axes": axes,
                    "encoding": "FLAT_JSON",
                    "element_count": int(np.prod(shape)),
                },
            },
            "mask_refs": [],
        }

    def list_snapshots(self, config_id: str) -> SnapshotIndex:
        if config_id not in C.CONFIG_ORDER:
            raise KeyError(config_id)
        items = [self.load_snapshot_metadata(config_id, idx)
                 for idx in sorted(self._snapshot_lookup(config_id))]
        return SnapshotIndex.model_validate({
            "experiment_id": REG.EXPERIMENT_ID,
            "config_id": config_id,
            "snapshot_count": len(items),
            "items": items,
        })

    def load_snapshot_metadata(self, config_id: str, snapshot_index: int) -> FieldSnapshot:
        if config_id not in C.CONFIG_ORDER:
            raise KeyError(config_id)
        source_step = self._source_step_for(config_id, snapshot_index)
        ckpt = self._read_checkpoint(config_id, source_step)
        if ckpt["source_step"] != source_step:
            raise ValueError(f"checkpoint step mismatch for {config_id} index {snapshot_index}")
        header = self._snapshot_result(config_id, snapshot_index, source_step,
                                       ckpt["physical_time"], "snapshot_metadata")
        fields = [self._field_descriptor(config_id, snapshot_index, source_step,
                                         ckpt["physical_time"], fid)
                  for fid in SEM.STORED_FLOW_FIELDS]
        grid = {
            "coordinate_system": "CARTESIAN",
            "dimensions": [{"axis": "y", "size": C.GRID_NY}, {"axis": "x", "size": C.GRID_NX}],
            "extent": [{"axis": "x", "lower": C.DOMAIN_X[0], "upper": C.DOMAIN_X[1]},
                       {"axis": "y", "lower": C.DOMAIN_Y[0], "upper": C.DOMAIN_Y[1]}],
        }
        return FieldSnapshot.model_validate({
            "result": header,
            "snapshot_id": f"case8.{config_id}.snapshot.{snapshot_index}",
            "snapshot_index": snapshot_index,
            "step_index": source_step,
            "physical_time": ckpt["physical_time"],
            "grid": grid,
            "fields": fields,
        })

    def load_field(self, config_id: str, snapshot_index: int, field_id: str) -> FieldResponse:
        if field_id not in SEM.STORED_FLOW_FIELDS:
            raise KeyError(f"field {field_id!r} is not a stored Case8 flow field")
        snapshot = self.load_snapshot_metadata(config_id, snapshot_index)
        for field in snapshot.fields:
            if field.field_id == field_id:
                return FieldResponse.model_validate({"snapshot": snapshot, "field": field})
        raise KeyError(field_id)

    # ============================================================ arrays
    def load_array(self, result_id: str, array_id: str) -> ScientificArray:
        parts = result_id.split(".")
        if len(parts) != 5 or parts[0] != "case8" or parts[2] != "snapshot":
            raise KeyError(f"unsupported array result_id {result_id!r}")
        if parts[1] not in C.CONFIG_ORDER or parts[3] not in tuple(str(i) for i in range(1, 7)):
            raise KeyError(result_id)
        config_id, snapshot_index, field_id = parts[1], int(parts[3]), parts[4]
        if field_id not in SEM.STORED_FLOW_FIELDS or array_id != field_id:
            raise KeyError(array_id)
        source_step = self._source_step_for(config_id, snapshot_index)
        ckpt = self._read_checkpoint(config_id, source_step)
        values = np.asarray(ckpt["arrays"][field_id])
        descriptor = {
            "array_id": field_id,
            "dtype": "float64",
            "shape": [int(s) for s in values.shape],
            "order": "C",
            "axes": list(SEM.FIELD_SEMANTICS[field_id]["axes"]),
            "encoding": "FLAT_JSON",
            "element_count": int(values.size),
        }
        header = self._snapshot_result(config_id, snapshot_index, source_step,
                                       ckpt["physical_time"],
                                       SEM.FIELD_SEMANTICS[field_id]["semantic_id"], field_id)
        return ScientificArray.model_validate({
            "result": header,
            "descriptor": descriptor,
            "values": [float(v) for v in values.reshape(-1, order="C")],
        })

    # ==================================================== entropy history
    def _history_rows(self, config_id: str) -> dict:
        if config_id in self._hist_cache:
            return self._hist_cache[config_id]
        path = self._history_path(config_id)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            columns = list(reader.fieldnames or [])
        self._hist_cache[config_id] = {"columns": columns, "rows": rows}
        return self._hist_cache[config_id]

    def _history_result(self, config_id: str, series_id: str, spec: dict) -> dict:
        return {
            "schema_version": "1.0.0",
            "result_id": f"case8.{config_id}.{series_id}",
            "experiment_id": REG.EXPERIMENT_ID,
            "config_id": config_id,
            "semantic_id": spec["definition_id"],
            "data_origin": "VERIFIED_PRODUCTION",
            "availability": "AVAILABLE",
            "time": {
                "sampling": "PER_STEP",
                "accumulation": "STEP_INCREMENT" if spec["aggregation"] == "STEP_INCREMENT" else "TRAJECTORY_INTEGRATED",
                "physical_time": unresolved("Per-step series; see point interval"),
                "interval": known({"start": 0.0, "end": C.FINAL_TIME}),
                "step_index": unresolved("Per-step series; see point step_index"),
                "stage_index": unresolved("Accepted-step endpoint", "NOT_APPLICABLE"),
                "snapshot_index": unresolved("Scalar history has no snapshot index", "NOT_APPLICABLE"),
                "index_convention": "source_step_index preserved; step_index=source_step_index+1",
            },
            "scope": {
                "id": "case8.native-face-budget",
                "description": f"Case8 {config_id} accepted-step entropy budget history",
                "boundary_scope": known("x_lower pre-shock inflow; x_upper outflow; y periodic"),
                "spatial_domain_ref": unresolved("Scalar budget, not a spatial field", "NOT_APPLICABLE"),
                "mask_refs": [],
                "definition_refs": [spec["definition_id"]],
            },
            "unit": spec["unit"],
            "verification": dict(EV._HISTORY_VERIFICATION),
            "provenance": {
                "evidence_refs": [f"ev.case8.{config_id}.entropy"],
                "source_asset_ids": [C.ASSET_ID_HISTORY_TEMPLATE.format(config=config_id)],
                "registry_revision": REG.REGISTRY_REVISION,
                "data_revision": REG.DATA_REVISION,
                "release_id": unresolved("No release bundle created", "NOT_APPLICABLE"),
                "source_drift": unresolved("Observe all source dependencies before asserting false"),
            },
            "limitations": [dict(EV._UNIT_UNKNOWN_LIMITATION)],
        }

    def load_scalar_series(self, config_id: str, series_id: str, *, offset: int = 0,
                           limit: int = 2000) -> ScalarSeries:
        if series_id not in SEM.HISTORY_SERIES:
            raise KeyError(series_id)
        spec = SEM.HISTORY_SERIES[series_id]
        rows = self._history_rows(config_id)["rows"]
        total = len(rows)
        page_rows = rows[offset:offset + limit]
        points = []
        for i, row in enumerate(page_rows):
            src_step = int(float(row["step"]))
            t_start = float(row["time_start"])
            t_end = float(row["time_end"])
            value = float(row[spec["source_column"]])
            points.append({
                "point_index": offset + i,
                "step_index": known(src_step + 1),
                "stage_index": unresolved("Accepted-step endpoint", "NOT_APPLICABLE"),
                "source_step_index": known(src_step),
                "source_stage_index": unresolved("No single stage", "NOT_APPLICABLE"),
                "physical_time": known(t_end),
                "interval": known({"start": t_start, "end": t_end}),
                "value": known(value),
            })
        return ScalarSeries.model_validate({
            "result": self._history_result(config_id, series_id, spec),
            "series_id": series_id,
            "label": spec["label"],
            "total_point_count": total,
            "points": points,
            "page": {
                "offset": offset, "limit": limit,
                "returned_count": len(points), "total_count": total,
                "has_more": offset + len(points) < total,
            },
            "aggregation": spec["aggregation"],
            "source_column": spec["source_column"],
            "definition_id": spec["definition_id"],
        })

    def load_entropy_history(self, config_id: str, *, series: tuple[str, ...] | None = None,
                             offset: int = 0, limit: int = 2000) -> EntropyHistory:
        selected = series or ("E_bg_cumulative", "E_aa_cumulative", "E_at_cumulative",
                              "E_bg_step", "E_aa_step", "E_at_step")
        series_models = [self.load_scalar_series(config_id, sid, offset=offset, limit=limit)
                         for sid in selected]
        return EntropyHistory.model_validate({
            "experiment_id": REG.EXPERIMENT_ID,
            "config_id": config_id,
            "series": series_models,
            "stage_aggregate_refs": list(SEM.STAGE_AGGREGATE_COLUMNS),
            "snapshot_alignment": unresolved("No alignment policy selected for this request"),
            "limitations": [],
            "evidence_refs": [f"ev.case8.{config_id}.entropy"],
        })

    def load_snapshot_alignment(self, config_id: str, *, scalar_step: int,
                                policy: str = "NEAREST_RECORDED",
                                snapshot_index: int | None = None) -> SnapshotAlignment:
        rows = self._history_rows(config_id)["rows"]
        row = next((r for r in rows if int(float(r["step"])) + 1 == scalar_step), None)
        if row is None:
            from backend.core.errors import system_error
            raise system_error("INVALID_REQUEST", "Accepted scalar step is not recorded", status=400)
        scalar_time = float(row["time_end"])
        snapshots = self.list_snapshots(config_id).items
        if policy == "PINNED":
            selected = self.load_snapshot_metadata(config_id, snapshot_index)
        elif policy == "NEAREST_RECORDED":
            selected = min(snapshots, key=lambda item: (abs(item.physical_time - scalar_time), item.snapshot_index))
        else:
            from backend.core.errors import system_error
            raise system_error("INVALID_REQUEST", "Unknown alignment policy", status=400)
        return SnapshotAlignment(
            experiment_id=REG.EXPERIMENT_ID, config_id=config_id, selection_policy=policy,
            selected_scalar_step=scalar_step, selected_scalar_time=scalar_time,
            displayed_snapshot_id=selected.snapshot_id, displayed_snapshot_index=selected.snapshot_index,
            displayed_snapshot_time=selected.physical_time,
            signed_time_delta=selected.physical_time - scalar_time,
            limitations=[{"id": "lim.case8.alignment", "code": "DISCRETE_RECORDED_ONLY",
                          "description": "Scalar and snapshot times have different granularities; no interpolated field",
                          "affected_refs": [selected.snapshot_id], "severity": "WARNING"}],
        )

    # ============================================================ metrics
    def load_metrics(self, config_id: str, *, metric_id: str | None = None,
                     snapshot_index: int | None = None) -> MetricCollection:
        if snapshot_index is None:
            snapshot_index = 6
        source_step = self._source_step_for(config_id, snapshot_index)
        metrics = self._read_checkpoint_metrics(config_id, source_step)
        ckpt = self._read_checkpoint(config_id, source_step)
        pairs = [
            ("case8_width", "front_width_mean"),
            ("case8_front_RMS", "front_rms"),
            ("case8_front_high_k_energy", "front_high_k_energy"),
        ]
        if metric_id is not None and metric_id not in {mid for mid, _ in pairs}:
            raise KeyError(metric_id)
        items = []
        for mid, column in pairs:
            if metric_id is not None and metric_id != mid:
                continue
            defn = SEM.DEFINITIONS[mid]
            header = self._metric_result(config_id, snapshot_index, source_step,
                                         ckpt["physical_time"], mid, defn["unit"])
            value = metrics.get(column)
            if value is None:
                from backend.core.errors import system_error
                error = system_error("MISSING_SCIENTIFIC_ASSET", "Recorded metric column is absent",
                                     status=404, availability="MISSING", resource_type="case8_metric",
                                     identity=known(mid), evidence_refs=[f"ev.case8.{config_id}.metrics"])
                items.append({"availability": "MISSING", "error": error.body.model_dump(mode="python")})
                continue
            items.append({
                "availability": "AVAILABLE",
                "value": {
                    "result": header,
                    "metric_id": mid,
                    "value": known(float(value)),
                    "definition_id": mid,
                    "detector": known(defn["detector"]) if isinstance(defn["detector"], dict)
                                else defn["detector"],
                    "time_scope": header["time"],
                    "display_label": defn["title"],
                    "resolution_limit": unresolved("No declared resolution limit"),
                },
            })
        return MetricCollection.model_validate({
            "experiment_id": REG.EXPERIMENT_ID,
            "config_id": config_id,
            "items": items,
            "evidence_refs": [f"ev.case8.{config_id}.metrics"],
        })

    def _metric_result(self, config_id: str, snapshot_index: int, source_step: int,
                       physical_time: float, metric_id: str, unit: dict) -> dict:
        header = self._snapshot_result(config_id, snapshot_index, source_step,
                                       physical_time, metric_id)
        header["result_id"] = f"case8.{config_id}.metrics.{metric_id}"
        header["unit"] = unit
        header["provenance"]["evidence_refs"] = [f"ev.case8.{config_id}.metrics"]
        header["provenance"]["source_asset_ids"].append(f"asset.case8.{config_id}.checkpoint_metrics")
        return header

    @lru_cache(maxsize=None)
    def _read_checkpoint_metrics(self, config_id: str, source_step: int) -> dict:
        path = (self._root / "corrected_physics_reproduction_v1" / "case8" /
                _CONFIG_DIR[config_id] / "source_data" / "checkpoint_metrics.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if int(rec["step"]) == source_step:
                return rec
        return {}

    # ============================================================ evidence
    def load_evidence(self, evidence_id: str) -> EvidenceRecord:
        parts = evidence_id.split(".")
        experiment_fact = known(REG.EXPERIMENT_ID)
        config_fact = unresolved("No configuration bound to this evidence id")
        assets: list[dict] = []
        result_ids: list[str] = []
        contexts: list[dict] = []
        definitions: list[dict] = []

        if len(parts) in (5, 6) and parts[:2] == ["ev", "case8"] and parts[3] == "snapshot":
            if parts[2] not in C.CONFIG_ORDER or parts[4] not in tuple(str(i) for i in range(1, 7)):
                raise KeyError(evidence_id)
            config_id, idx = parts[2], int(parts[4])
            field_id = parts[5] if len(parts) == 6 else None
            source_step = self._source_step_for(config_id, idx)
            snap = self.load_snapshot_metadata(config_id, idx)
            config_fact = known(config_id)
            assets = [EV.checkpoint_source_asset(config_id, source_step)]
            if field_id is not None:
                field = next((f for f in snap.fields if f.field_id == field_id), None)
                if field is None:
                    raise KeyError(f"no field {field_id!r} in snapshot {idx}")
                result_ids = [field.result.result_id]
                contexts = [field.result.model_dump(mode="json")]
            else:
                result_ids = [snap.result.result_id, *[field.result.result_id for field in snap.fields]]
                contexts = [snap.result.model_dump(mode="json"), *[field.result.model_dump(mode="json") for field in snap.fields]]
            definitions = [
                {
                    "id": fid, "semantic_id": spec["semantic_id"], "title": spec["label"],
                    "definition": spec["definition"], "time_rule": spec["time_rule"],
                    "spatial_rule": spec["spatial_rule"], "unit": spec["unit"],
                    "mask_refs": [],
                    "detector": unresolved("Stored state variable, not detector metric", "NOT_APPLICABLE"),
                    "evidence_refs": [evidence_id], "limitations": [],
                }
                for fid, spec in SEM.FIELD_SEMANTICS.items()
            ]
        elif len(parts) == 4 and parts[:2] == ["ev", "case8"] and parts[3] == "entropy":
            config_id = parts[2]
            config_fact = known(config_id)
            assets = [EV.history_source_asset(config_id)]
            keys = ("E_bg_cumulative", "E_aa_cumulative", "E_at_cumulative", "E_bg_step", "E_aa_step", "E_at_step")
            contexts = [self.load_scalar_series(config_id, key, limit=1).result.model_dump(mode="json") for key in keys]
            result_ids = [context["result_id"] for context in contexts]
            definitions = [self._definition_payload(key, evidence_id) for key in keys]
        elif len(parts) == 4 and parts[:2] == ["ev", "case8"] and parts[3] == "metrics":
            config_id = parts[2]
            config_fact = known(config_id)
            source_step = self._source_step_for(config_id, 6)
            assets = [EV.checkpoint_source_asset(config_id, source_step)]
            # Metric values originate in the recorded checkpoint metrics file.
            import hashlib
            relative = f"corrected_physics_reproduction_v1/case8/{_CONFIG_DIR[config_id]}/source_data/checkpoint_metrics.jsonl"
            with (self._root / relative).open("rb") as stream:
                current = hashlib.file_digest(stream, "sha256").hexdigest()
            assets.append({**assets[0], "asset_id": f"asset.case8.{config_id}.checkpoint_metrics",
                           "source_display": f"Case8 {config_id} recorded checkpoint metrics",
                           "relative_origin": known(relative), "format": "JSONL",
                           "recorded_data_hash": unresolved("No frozen metrics-file hash bound"),
                           "current_data_hash": known(current),
                           "data_drift": unresolved("No recorded baseline for comparison"),
                           "verification": {**assets[0]["verification"], "status": "PARTIAL",
                                            "basis": ["Read-only current hash observed; no recorded metrics-file baseline"]}})
            collection = self.load_metrics(config_id)
            contexts = [slot.root.value.result.model_dump(mode="json") for slot in collection.items
                        if hasattr(slot.root, "value")]
            result_ids = [context["result_id"] for context in contexts]
            definitions = [self._definition_payload(key, evidence_id) for key in
                           ("case8_width", "case8_front_RMS", "case8_front_high_k_energy")]
        elif evidence_id == "ev.case8.D_u.allocation":
            config_fact = known("D_u")
            meta = EV.allocation_registry_metadata()
            assets = [{
                "asset_id": meta["asset_id"], "source_id": "scientific-root-v1",
                "source_display": meta["source_display"], "relative_origin": meta["relative_origin"],
                "role": "DATA", "format": "NPZ",
                "recorded_data_hash": unresolved("Allocation map not bound in this window"),
                "current_data_hash": unresolved("Runtime observation not performed"),
                "data_drift": unresolved("Not observed"),
                "verification": {
                    "status": "PARTIAL", "basis": ["Registry metadata only; values deferred"],
                    "verified_at": unresolved("Not verified"),
                    "observation_at": unresolved("Not observed"),
                    "evidence_refs": [evidence_id],
                },
                "canonical_selected": True,
                "limitations": [{
                    "id": "lim.allocation.deferred", "code": "IMPLEMENTATION_DEFERRED",
                    "description": "Cumulative native-face values not loaded in this window",
                    "affected_refs": [meta["result_id"]], "severity": "WARNING",
                }],
            }]
            result_ids = []  # values deferred; no numerical result bound in this window
            contexts: list = []
        else:
            raise KeyError(f"unsupported evidence id {evidence_id!r}")

        return EvidenceRecord.model_validate({
            "schema_version": "1.0.0",
            "evidence_id": evidence_id,
            "result_ids": result_ids,
            "result_contexts": contexts,
            "experiment_id": experiment_fact,
            "config_id": config_fact,
            "config": known(next(item.model_dump(mode="python") for item in self.list_configs().items
                                 if item.id == config_fact["value"])) if config_fact.get("state") == "KNOWN"
                      else unresolved("No configuration bound"),
            "definitions": definitions,
            "masks": [],
            "method_name": known(C.METHOD_NAME),
            "method_hash": known(C.METHOD_SHA256),
            "recorded_source_hash": known(C.METHOD_SHA256),
            "current_source_hash": unresolved("Runtime read-only observation not performed"),
            "source_observations": [],
            "source_assets": assets,
            "data_hash": known(assets[0]["recorded_data_hash"]["value"])
            if len(assets) == 1 and assets[0]["recorded_data_hash"].get("state") == "KNOWN"
            else unresolved("No established composite data hash"),
            "freeze_reference": unresolved("No upstream per-asset freeze record", "NOT_APPLICABLE"),
            "processing": [{
                "id": f"processing.{evidence_id}.read",
                "kind": "FORMAT_MAPPING",
                "description": "Read-only mapping of source member/column into canonical model; values preserved",
                "input_asset_ids": [a["asset_id"] for a in assets],
                "definition_refs": [d["id"] for d in definitions],
                "processing_hash": unresolved("Adapter hash not recorded"),
                "verification": {
                    "status": "NOT_APPLICABLE", "basis": ["Read-only format mapping"],
                    "verified_at": unresolved("Mapping, not a scientific claim", "NOT_APPLICABLE"),
                    "observation_at": unresolved("Mapping", "NOT_APPLICABLE"),
                    "evidence_refs": [evidence_id],
                },
            }],
            "verification": _adapter_evidence_verification(assets, evidence_id),
            "limitations": [],
            "source_drift": unresolved("Runtime dependency observation has not occurred"),
            "created_at": unresolved("No authoritative per-result timestamp"),
            "verified_at": unresolved("No authoritative per-result timestamp bound"),
            "related_evidence_refs": [C.ASSET_ID_METHOD],
            "superseded_by": unresolved("No known replacement", "NOT_APPLICABLE"),
        })

    def _definition_payload(self, def_id: str, evidence_id: str) -> dict:
        d = SEM.DEFINITIONS[def_id]
        return {
            "id": d["id"], "semantic_id": d["semantic_id"], "title": d["title"],
            "definition": d["definition"], "time_rule": d["time_rule"],
            "spatial_rule": d["spatial_rule"], "unit": d["unit"], "mask_refs": [],
            "detector": known(d["detector"]) if "id" in d["detector"] else d["detector"], "evidence_refs": [evidence_id], "limitations": [],
        }

    # ============================================================ provenance
    def load_provenance(self, result_id: str) -> ResultProvenance:
        parts = result_id.split(".")
        if len(parts) < 3 or parts[0] != "case8" or parts[1] not in C.CONFIG_ORDER:
            raise KeyError(result_id)
        config_id = parts[1]
        if parts[2] == "snapshot" and len(parts) in (4, 5) and parts[3] in tuple(str(i) for i in range(1, 7)):
            idx = int(parts[3])
            item = self.load_snapshot_metadata(config_id, idx)
            result = item.result if len(parts) == 4 else self.load_field(config_id, idx, parts[4]).field.result
        elif parts[2] == "metrics" and len(parts) == 4:
            items = self.load_metrics(config_id, metric_id=parts[3]).items
            if not items:
                raise KeyError(result_id)
            result = items[0].root.value.result
        elif len(parts) == 3 and parts[2] in SEM.HISTORY_SERIES:
            result = self.load_scalar_series(config_id, parts[2], limit=1).result
        else:
            raise KeyError(result_id)
        return ResultProvenance(result_id=result_id, provenance=result.provenance, evidence_records=[])



def _adapter_evidence_verification(assets: list[dict], evidence_id: str) -> dict:
    if any(asset.get("verification", {}).get("status") == "PARTIAL" for asset in assets):
        return {"status": "PARTIAL", "basis": ["At least one source dependency lacks a recorded verification baseline"],
                "verified_at": unresolved("No complete verification event"),
                "observation_at": unresolved("No complete source observation"), "evidence_refs": [evidence_id]}
    if assets and assets[0].get("verification", {}).get("status"):
        v = dict(assets[0]["verification"])
        v["evidence_refs"] = [evidence_id]
        return v
    return {
        "status": "PARTIAL", "basis": ["Registry metadata only"],
        "verified_at": unresolved("Not verified"),
        "observation_at": unresolved("Not observed"),
        "evidence_refs": [evidence_id],
    }
