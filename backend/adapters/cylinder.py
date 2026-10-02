"""Read-only scientific adapter for the selected Cylinder J2C formal v2.

No solver imports, reconstruction, interpolation, fitting or CFD execution.
Selectors only address pinned registry identities. Source bytes are hash checked
before decoding; cached CSV parsing never substitutes for observing current bytes.
"""
from __future__ import annotations

import csv
import hashlib
import json
from io import BytesIO, StringIO
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from backend.core.errors import system_error, unsupported_combination
from backend.models.core import known, unresolved
from backend.models.cylinder import AllocationResult, CylinderAllocationOverview
from backend.models.evidence import EvidenceRecord, ResultProvenance
from backend.models.experiments import Experiment, ExperimentConfig
from backend.models.results import (EntropyHistory, FieldSnapshot, Metric, MetricCollection,
    ScalarSeries, ScientificArray, ScientificResult, SnapshotIndex)
from backend.models.transport import CapabilityList, ConfigList, FieldResponse
from backend.registry import cylinder_registry as R


@runtime_checkable
class CylinderAdapterProtocol(Protocol):
    def describe_experiment(self) -> Experiment: ...
    def list_configs(self) -> ConfigList: ...
    def describe_capabilities(self) -> CapabilityList: ...
    def list_snapshots(self, config_id: str) -> SnapshotIndex: ...
    def load_snapshot_metadata(self, config_id: str, snapshot_index: int) -> FieldSnapshot: ...
    def load_field(self, config_id: str, snapshot_index: int, field_id: str) -> FieldResponse: ...
    def load_entropy_history(self, config_id: str, *, series=None, offset=0, limit=2000) -> EntropyHistory: ...
    def load_scalar_series(self, config_id: str, series_id: str, *, offset=0, limit=2000) -> ScalarSeries: ...
    def load_allocation_overview(self, config_id: str) -> CylinderAllocationOverview: ...
    def load_sectors(self, config_id: str) -> AllocationResult: ...
    def load_front_band(self, config_id: str) -> AllocationResult: ...
    def load_metrics(self, config_id: str, *, metric_id=None, snapshot_index=None) -> MetricCollection: ...
    def load_array(self, result_id: str, array_id: str) -> ScientificArray: ...
    def load_evidence(self, evidence_id: str) -> EvidenceRecord: ...
    def load_provenance(self, result_id: str) -> ResultProvenance: ...


COMMON = (
    f"{R.BASE}/J2C_V2_PROTOCOL_LOCK.json", f"{R.BASE}/J2C_V2_STATUS.json",
    f"{R.BASE}/provenance/result_hashes.csv", f"{R.BASE}/analysis/cylinder_j2c_v2.py",
    f"{R.BASE}/J2C_V2_CLAIM_BOUNDARY.md", "solver/fluxes/cross_mode_ec_unified_v1.py",
    "solver/core/time_integrator.py", "solver/diagnostics/cylinder.py",
    "solver/experiments/cylinder_b2_4_production.py",
    "jcp_extension_v1/J2_entropy_diagnostics/diagnostics/channel_entropy_diagnostics.py",
)


class CylinderAdapter:
    def __init__(self, scientific_root: str | Path = R.SCIENTIFIC_ROOT):
        self._root = Path(scientific_root).resolve()
        self._results: dict[str, dict] = {}
        self._arrays: dict[tuple[str, str], tuple[dict, str, str]] = {}
        self._definitions: dict[tuple[str, str], dict] = {}
        self._sources: dict[str, set[str]] = {}
        self._hist_cache: dict[str, tuple[str, list[dict]]] = {}

    @property
    def registry_revision(self):
        return R.REGISTRY_REVISION

    @property
    def data_revision(self):
        return R.DATA_REVISION

    def _read(self, relative):
        if relative not in R.ASSETS:
            raise system_error("UNKNOWN_ASSET_ID", "Unregistered Cylinder asset", status=404, availability="MISSING")
        path = (self._root / relative).resolve()
        if not path.is_relative_to(self._root):
            raise system_error("SOURCE_READ_ERROR", "Registered asset escapes the scientific source root")
        try:
            before = path.stat()
            raw = path.read_bytes()
            after = path.stat()
        except FileNotFoundError:
            raise system_error("MISSING_SCIENTIFIC_ASSET", "Registered saved Cylinder asset is absent", status=404,
                               availability="MISSING", evidence_refs=["ev.missing.cylinder-cumulative2d"] if "cumulative2d" in relative else []) from None
        except OSError:
            raise system_error("SOURCE_READ_ERROR", "Saved Cylinder source could not be read") from None
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise system_error("SOURCE_CHANGED_DURING_READ", "Cylinder source changed during observation", status=409)
        if hashlib.sha256(raw).hexdigest() != R.ASSETS[relative]["sha256"]:
            raise system_error("SOURCE_DATA_DRIFT", "Saved Cylinder source no longer matches the pinned hash", status=409)
        return raw

    def _json(self, relative):
        return json.loads(self._read(relative))

    def _npz(self, relative):
        with np.load(BytesIO(self._read(relative)), allow_pickle=False) as z:
            return {key: z[key] for key in z.files}

    def _context(self, config_id):
        R.require_config(config_id)
        for relative in COMMON:
            self._read(relative)
        protocol = self._json(COMMON[0])
        if (protocol["protocol"] != R.MANIFEST["protocol_source"]["protocol"] or
                protocol["configurations"] != R.MANIFEST["protocol_source"]["configurations"] or
                protocol["snapshot_steps"] != list(R.STEPS)):
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Cylinder protocol does not match the frozen registry")
        status = self._json(COMMON[1])
        if status["j2c_v2_gate"] != "PASS" or status["primary_budget_scope"] != "INTERIOR_ONLY":
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Cylinder upstream validity gate is not satisfied")
        result = self._json(R.run_path(config_id, "run_result.json"))
        if (result["config"] != config_id or result["accepted_steps"] != 9757 or result["final_time"] != 2.0 or
                {k: result[k] for k in ("q_aa", "q_at")} != protocol["configurations"][config_id]):
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Cylinder run identity is inconsistent")
        return protocol, result

    def _header(self, config_id, result_id, semantic_id, unit, time, group, paths, *, definition=None, detector=None, limitations=(), scope=None):
        ev = f"ev.cylinder.{config_id}.{group}"
        definition_id = f"def.{semantic_id}"
        deps = set(paths) | set(COMMON) | {R.run_path(config_id, "run_result.json")}
        header = {"schema_version": "1.0.0", "result_id": result_id, "experiment_id": "cylinder",
            "config_id": config_id, "semantic_id": semantic_id, "data_origin": "VERIFIED_PRODUCTION",
            "availability": "AVAILABLE", "time": time, "scope": scope or R.scope(definition_id), "unit": unit,
            "verification": R.verification(ev), "provenance": {"evidence_refs": [ev],
                "source_asset_ids": [R.ASSETS[p]["asset_id"] for p in sorted(deps)],
                "registry_revision": R.REGISTRY_REVISION, "data_revision": R.DATA_REVISION,
                "release_id": unresolved("No Cylinder numerical release freeze", "NOT_APPLICABLE"), "source_drift": known(False)},
            "limitations": list(limitations)}
        header = ScientificResult.model_validate(header).model_dump(mode="python")
        self._results[result_id] = header
        self._sources.setdefault(ev, set()).update(deps)
        self._definitions[(ev, definition_id)] = {"id": definition_id, "semantic_id": semantic_id, "title": semantic_id,
            "definition": definition or semantic_id, "time_rule": f"{time['sampling']};{time['accumulation']};{time['index_convention']}",
            "spatial_rule": header["scope"]["description"], "unit": unit, "mask_refs": header["scope"]["mask_refs"],
            "detector": known(detector) if detector else R.NA, "evidence_refs": [ev], "limitations": list(limitations)}
        return header

    def _array_ref(self, header, array_id, relative, member, values, axes):
        ref = {"result_id": header["result_id"], "descriptor": {"array_id": array_id, "dtype": str(values.dtype),
            "shape": list(values.shape), "order": "C", "axes": list(axes), "encoding": "FLAT_JSON", "element_count": int(values.size)}}
        self._arrays[(header["result_id"], array_id)] = (ref, relative, member)
        return ref

    def _config(self, config_id):
        protocol, _ = self._context(config_id)
        ev = f"ev.cylinder.{config_id}.protocol"
        params = protocol["configurations"][config_id]
        result_id = f"cylinder.{config_id}.protocol"
        self._header(config_id, result_id, "Cylinder_protocol", R.FRACTION, R.time("STATIC"), "protocol", [],
            definition="Mach3 O-grid nr32, ntheta128, r=.5..8, stretch3; fixed dt; T=2; SSP-RK3; first-order curvilinear finite volume")
        return {"id": config_id, "experiment_id": "cylinder", "name": f"Cylinder {config_id}",
            "parameters": [{"name": key, "value": known(float(value)), "unit": R.FRACTION} for key, value in params.items()],
            "protocol": {"method_name": known(protocol["method"]), "method_hash": known(R.ASSETS[COMMON[5]]["sha256"]),
                "grid": known(self._grid()), "integrator": known("SSP-RK3 fixed dt"),
                "reconstruction": known("first-order curvilinear finite volume; no reconstruction"), "final_time": known(2.0),
                "boundary_scope": known("Cylinder wall and far-field boundary conditions; primary entropy budget INTERIOR_ONLY"),
                "protocol_asset_refs": [R.ASSETS[COMMON[0]]["asset_id"]]},
            "verification": R.verification(ev), "limitations": [R.NO_MAP], "evidence_refs": [ev]}

    @staticmethod
    def _grid():
        return {"coordinate_system": "CURVILINEAR_POLAR", "dimensions": [{"axis": "r", "size": 32}, {"axis": "theta", "size": 128}],
                "extent": [{"axis": "r", "lower": .5, "upper": 8.0}, {"axis": "theta", "lower": 0.0, "upper": float(2*np.pi)}]}

    def list_configs(self):
        return ConfigList.model_validate({"experiment_id": "cylinder", "items": [self._config(cid) for cid in R.CONFIGS]})

    def describe_capabilities(self):
        self.list_configs()
        items = []
        for task in ("flow", "entropy", "sectors", "front-band", "metrics", "cumulative-2d"):
            missing = task == "cumulative-2d"
            refs = [] if missing else [f"cylinder.{c}.{task}" for c in R.CONFIGS]
            # Result refs point to delivered concrete identities, not UI tab labels.
            suffix = {"flow": "snapshot.1", "entropy": "history.E_at_cumulative", "metrics": "metric.cylinder_centerline_width"}.get(task, task)
            refs = [] if missing else [f"cylinder.{c}.{suffix}" for c in R.CONFIGS]
            items.append({"id": f"cap.cylinder.{task}", "experiment_id": "cylinder", "task": task,
                "status": "MISSING" if missing else "SUPPORTED", "available_for_configs": [] if missing else list(R.CONFIGS),
                "config_support": [{"config_id": c, "status": "MISSING" if missing else "SUPPORTED",
                    "reason": "No selected saved full trajectory 2D map" if missing else "Pinned real saved native scientific data",
                    "result_refs": [] if missing else [f"cylinder.{c}.{suffix}"]} for c in R.CONFIGS],
                "controls": [{"name": "config", "kind": "ENUM", "allowed_values": list(R.CONFIGS), "combination_registry_ref": known(R.REGISTRY_REVISION)}],
                "tab_policy": {"tab_id": task, "visible_for_family": True, "disabled_for_configs": list(R.CONFIGS) if missing else [], "unsupported_deep_link_behavior": "EXPLAIN"},
                "result_refs": refs, "limitations": [R.NO_MAP] if missing else [],
                "evidence_refs": ["ev.missing.cylinder-cumulative2d"] if missing else [f"ev.cylinder.{c}.protocol" for c in R.CONFIGS]})
        return CapabilityList.model_validate({"experiment_id": "cylinder", "items": items})

    def describe_experiment(self):
        return Experiment.model_validate({"schema_version": "1.0.0", "id": "cylinder", "name": "Mach3 Cylinder",
            "scientific_family": "CYLINDER", "description": "Selected J2C formal v2 native instantaneous faces, interior-only accepted-step budgets, cumulative sectors and fixed A_u radial band",
            "capabilities": self.describe_capabilities().items, "available_configs": self.list_configs().items,
            "status": "PARTIAL", "delivery_status": "IMPLEMENTED", "limitations": [R.NO_MAP],
            "evidence_refs": [f"ev.cylinder.{c}.protocol" for c in R.CONFIGS] + ["ev.missing.cylinder-cumulative2d"], "related_experiment_ids": ["case8"]})

    def load_snapshot_metadata(self, config_id, snapshot_index):
        self._context(config_id)
        if type(snapshot_index) is not int or snapshot_index not in range(1, 6):
            raise system_error("SNAPSHOT_NOT_FOUND", "Cylinder snapshot index must be 1..5", status=404, availability="MISSING")
        step = R.STEPS[snapshot_index-1]
        relative = R.run_path(config_id, f"snapshots/native_faces_step_{step:05d}.npz")
        z = self._npz(relative)
        physical_time = float(z["time"].item())
        expected_time = R.MANIFEST["runs"][config_id]["snapshot_source"][snapshot_index-1]["physical_time"]
        if int(z["step"].item()) != step or physical_time != expected_time:
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Saved Cylinder checkpoint step/time is inconsistent")
        time = R.time("MULTI_SNAPSHOT", physical_time=physical_time, step=step, snapshot=snapshot_index)
        rid = f"cylinder.{config_id}.snapshot.{snapshot_index}"
        header = self._header(config_id, rid, "Cylinder_native_face_snapshot", R.FRACTION, time, "snapshots", [relative],
                              definition="Saved instantaneous interior-face diagnostics; no primitive field movie and no trajectory reconstruction")
        fields = []
        ev = f"ev.cylinder.{config_id}.snapshots"
        for family, shape in R.FAMILIES.items():
            axes = ["r_face" if family == "radial_interior" else "r_cell", "theta_cell" if family == "radial_interior" else "theta_face"]
            geometry_refs = {}
            for key in R.GEOMETRY:
                member = f"{family}_{key}"
                if member not in z:
                    continue
                u = R.ANGLE if key == "theta_face" else R.FRACTION if key.startswith("unit_normal") else R.LENGTH
                gh = self._header(config_id, f"{rid}.geometry.{member}", f"Cylinder_native_{key}", u, time,
                    "snapshots", [relative], definition=f"Saved {key} on {family}; native coordinates/normals/face measure without Cartesian projection")
                geometry_refs[key] = self._array_ref(gh, member, relative, member, z[member], axes)
            domain = {"id": f"domain.cylinder.{family}", "coordinate_system": "CURVILINEAR_POLAR",
                "location_type": "CYLINDER_RADIAL_FACE" if family == "radial_interior" else "CYLINDER_ANGULAR_FACE",
                "shape": list(shape), "axes": [{"name": ax, "size": n, "coordinate_values": R.NA,
                    "coordinate_array_ref": unresolved("Native curvilinear coordinate arrays are 2D; use registered geometry members", "NOT_APPLICABLE"),
                    "unit": R.LENGTH if ax.startswith("r_") else R.ANGLE} for ax, n in zip(axes, shape)],
                "extent": self._grid()["extent"], "measure_convention": {**R.MEASURE, "id": "cylinder.instantaneous-face-density",
                    "description": "Saved instantaneous face diagnostic densities; face measure is a separate native member",
                    "integral_rule": "rate=sum(native_face_measure*pi_channel) over both interior families", "includes_time_weights": False, "includes_spatial_measure": False},
                "boundary_scope": known("INTERIOR_ONLY"), "geometry_ref": known(geometry_refs["x_face"]) if "x_face" in geometry_refs else unresolved("Saved face geometry missing", "MISSING"), "evidence_refs": [ev]}
            for key in R.FIELDS:
                member = f"{family}_{key}"
                if member not in z:
                    continue  # Absence is a gap, never a zero substitute.
                if z[member].shape != shape or z[member].dtype != np.dtype("float64") or not np.isfinite(z[member]).all():
                    raise system_error("CANONICAL_SCHEMA_MISMATCH", "Native face field has unexpected shape, dtype or non-finite values")
                fh = self._header(config_id, f"{rid}.{member}", f"Cylinder_{key}_instantaneous", R.FIELD_UNITS[key], time,
                    "snapshots", [relative], definition=R.MANIFEST["field_semantics"][key] + "; " + R.FIELD_DEFINITIONS[key] + "; per native face, without face measure/time weights")
                ref = self._array_ref(fh, member, relative, member, z[member], axes)
                fields.append({"field_id": member, "label": member, "result": fh, "domain": domain, "array_ref": ref, "mask_refs": []})
        return FieldSnapshot.model_validate({"result": header, "snapshot_id": rid, "snapshot_index": snapshot_index,
            "step_index": step, "physical_time": physical_time, "grid": self._grid(), "fields": fields})

    def list_snapshots(self, config_id):
        R.require_config(config_id)
        return SnapshotIndex.model_validate({"experiment_id": "cylinder", "config_id": config_id, "snapshot_count": 5,
                                            "items": [self.load_snapshot_metadata(config_id, i) for i in range(1, 6)]})

    def load_field(self, config_id, snapshot_index, field_id):
        snapshot = self.load_snapshot_metadata(config_id, snapshot_index)
        field = next((f for f in snapshot.fields if f.field_id == field_id), None)
        if field is None:
            raise system_error("MISSING_SCIENTIFIC_ASSET", "This snapshot does not contain the requested saved native field", status=404,
                               availability="MISSING", resource_type="field", evidence_refs=snapshot.result.provenance.evidence_refs)
        return FieldResponse(snapshot=snapshot, field=field)

    def _history(self, config_id):
        _, result = self._context(config_id)
        relative = R.run_path(config_id, "stage_weighted_history.csv")
        raw = self._read(relative)
        digest = hashlib.sha256(raw).hexdigest()
        if config_id not in self._hist_cache or self._hist_cache[config_id][0] != digest:
            rows = list(csv.DictReader(StringIO(raw.decode("utf-8"))))
            if (len(rows) != 9757 or [int(r["step"]) for r in rows] != list(range(9757)) or
                    any(r["config"] != config_id or r["run_id"] != f"cylinder_{config_id}" for r in rows)):
                raise system_error("CANONICAL_SCHEMA_MISMATCH", "Saved accepted-step history identity or numbering mismatch")
            t0 = np.array([float(r["time_start"]) for r in rows])
            t1 = np.array([float(r["time_end"]) for r in rows])
            dt = np.array([float(r["dt"]) for r in rows])
            np.testing.assert_allclose(t0[1:], t1[:-1], rtol=0, atol=5e-16)
            np.testing.assert_allclose(t1-t0, dt, rtol=0, atol=5e-16)
            if t0[0] != 0 or t1[-1] != 2 or not np.all(t1 > t0):
                raise system_error("CANONICAL_SCHEMA_MISMATCH", "Saved accepted-step intervals are invalid")
            for c in ("bg", "aa", "at", "total"):
                inc = np.array([float(r[f"deltaE_{c}_int"]) for r in rows])
                cumulative = np.array([float(r[f"E_{c}_int"]) for r in rows])
                rates = np.array([[float(r[f"dotE_{c}_int_s{s}"]) for s in range(3)] for r in rows])
                np.testing.assert_allclose(inc, dt * (rates @ np.array([1/6, 1/6, 2/3])), rtol=2e-15, atol=1e-17)
                np.testing.assert_array_equal(cumulative, np.cumsum(inc))
                if cumulative[-1] != result["channel_totals"][c]:
                    raise system_error("CANONICAL_SCHEMA_MISMATCH", "Canonical terminal budget differs from accepted history")
            self._hist_cache[config_id] = digest, rows
        return relative, self._hist_cache[config_id][1]

    def load_scalar_series(self, config_id, series_id, *, offset=0, limit=2000):
        R.require_config(config_id)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 5000:
            raise system_error("INVALID_REQUEST", "History page requires offset>=0 and limit 1..5000", status=400)
        spec = next((s for s in R.MANIFEST["runs"][config_id]["history_source"]["series"] if s["series_id"] == series_id), None)
        if spec is None:
            raise system_error("INVALID_RESULT_ID", "Cylinder scalar series is not registered", status=404, availability="MISSING")
        relative, rows = self._history(config_id)
        accumulation = {"CUMULATIVE": "TRAJECTORY_INTEGRATED", "PER_STEP_INCREMENT": "STAGE_WEIGHTED_INCREMENT", "NONE": "NONE"}[spec["accumulation"]]
        stage = spec.get("stage_index")
        time = R.time("PER_STEP" if stage is None else "PER_STAGE", accumulation, stage=stage, interval={"start": 0.0, "end": 2.0})
        u = R.ENTROPY if spec["accumulation"] != "NONE" else R.RATE if spec["source_column"].startswith("dotE_") else R.unit(
            "relative_rate_residual" if series_id.startswith("relative_additivity") else "rate_residual" if series_id.startswith("absolute_additivity") else "J" if series_id.startswith("J_max") else "transverse_opportunity_norm_squared" if series_id.startswith("Pt_z") else "entropy_production_density",
            spec["unit"]["label"], spec["unit"]["system"] == "DIMENSIONLESS" or series_id.startswith("J_max"))
        header = self._header(config_id, f"cylinder.{config_id}.history.{series_id}", f"Cylinder_{series_id}", u, time,
            "history", [relative], definition=spec["definition"] + "; source accepted interval start/end retained; cumulative at time_end; stage input has no asserted endpoint time")
        points = [{"point_index": i, "step_index": known(int(r["step"])+1), "stage_index": known(stage) if stage is not None else R.NA,
            "source_step_index": known(int(r["step"])), "source_stage_index": known(stage) if stage is not None else R.NA,
            "physical_time": known(float(r["time_end"])) if stage is None else unresolved("Saved stage index has no exact physical stage-state time", "UNKNOWN"),
            "interval": known({"start": float(r["time_start"]), "end": float(r["time_end"])}), "value": known(float(r[spec["source_column"]]))}
            for i, r in enumerate(rows[offset:offset+limit], offset)]
        return ScalarSeries.model_validate({"result": header, "series_id": series_id, "label": series_id, "total_point_count": len(rows),
            "points": points, "page": {"offset": offset, "limit": limit, "returned_count": len(points), "total_count": len(rows), "has_more": offset+len(points) < len(rows)},
            "aggregation": {"CUMULATIVE": "CUMULATIVE", "PER_STEP_INCREMENT": "STEP_INCREMENT", "NONE": "NONE"}[spec["accumulation"]],
            "source_column": spec["source_column"], "definition_id": f"def.Cylinder_{series_id}"})

    def load_entropy_history(self, config_id, *, series=None, offset=0, limit=2000):
        R.require_config(config_id)
        selected = series or tuple(f"E_{c}_cumulative" for c in ("bg", "aa", "at", "total"))
        return EntropyHistory.model_validate({"experiment_id": "cylinder", "config_id": config_id,
            "series": [self.load_scalar_series(config_id, s, offset=offset, limit=limit) for s in selected],
            "stage_aggregate_refs": [f"cylinder.{config_id}.history.delta_E_{c}" for c in ("bg", "aa", "at", "total")],
            "snapshot_alignment": unresolved("Snapshot selection is independent of the dense accepted-step history", "NOT_APPLICABLE"),
            "limitations": [], "evidence_refs": [f"ev.cylinder.{config_id}.history"]})

    def _allocation(self, config_id):
        protocol, result = self._context(config_id)
        relative = R.run_path(config_id, "spatial_cumulative.npz")
        z = self._npz(relative)
        if z["bins"].shape != (17,) or not np.all(np.diff(z["bins"]) > 0):
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Cylinder angular edges must be 17 monotone saved values")
        for c in ("bg", "aa", "at", "total"):
            if z[f"channel_{c}"].shape != (16,):
                raise system_error("CANONICAL_SCHEMA_MISMATCH", "Cylinder channel must contain 16 saved sectors")
            np.testing.assert_allclose(z[f"channel_{c}"].sum(), result["channel_totals"][c], rtol=1e-13, atol=1e-14)
        np.testing.assert_allclose(z["channel_total"], z["channel_bg"]+z["channel_aa"]+z["channel_at"], rtol=1e-13, atol=1e-14)
        self._history(config_id)  # binds sector denominator to canonical accepted-step budget
        return protocol, result, relative, z

    def _mask(self, config_id, protocol):
        geometry = protocol["shock_localization_geometry"]
        anchors = self._npz(geometry["source"])
        np.testing.assert_array_equal(anchors["front_angles"], geometry["front_angles"])
        np.testing.assert_array_equal(anchors["front_radii"], geometry["front_radii"])
        ev = f"ev.cylinder.{config_id}.front-band"
        self._sources.setdefault(ev, set()).add(geometry["source"])
        return {"id": R.MASK_ID, "type": "CYLINDER_FIXED_FRONT_BAND", "domain_refs": [f"domain.cylinder.{f}" for f in R.FAMILIES],
            "definition": "Fixed A_u authoritative radial front anchors; unwrap angles, linearly interpolate radius only within anchor angular span (NaN outside); finite(r_front) and abs(r_face-r_front)<=0.16; interior-only. No bitmap or 2D cumulative map is saved.",
            "parameters": [{"name": "radial_half_width", "value": known(.16)}, {"name": "reference_config", "value": known("A_u")}] +
                [{"name": f"anchor_{i}_{key}", "value": known(float(value))} for key, values in (("angle_radian", geometry["front_angles"]), ("radius_model_length", geometry["front_radii"])) for i, value in enumerate(values)],
            "index_sets": [], "mask_array_refs": [], "scope": R.scope("def.cylinder_front_band_fraction", [R.MASK_ID]),
            "verification": R.verification(ev), "evidence_refs": [ev]}

    @staticmethod
    def _fraction(numerator, denominator):
        return known(float(numerator/denominator)) if denominator != 0 else unresolved("E_at_int is zero; fraction has no defined denominator", "NOT_APPLICABLE")

    def _metric(self, config_id, metric_id, value, unit, time, group, paths, definition, *, detector=None, limitations=(), resolution=None, scope=None):
        rid = f"cylinder.{config_id}.metric.{metric_id}"
        header = self._header(config_id, rid, metric_id, unit, time, group, paths, definition=definition,
                              detector=detector, limitations=limitations, scope=scope)
        return Metric.model_validate({"result": header, "metric_id": metric_id, "value": value, "definition_id": f"def.{metric_id}",
            "detector": known(detector) if detector else R.NA, "time_scope": time, "display_label": metric_id,
            "resolution_limit": known(resolution) if resolution is not None else unresolved("No numerical uncertainty or detector floor threshold is established for this metric")})

    def _summary(self, config_id, result, relative, z):
        denominator = result["channel_totals"]["at"]
        scalar = float(z["shock_at"].item())
        metrics = [self._metric(config_id, "E_at_int", known(denominator), R.ENTROPY, R.TRAJECTORY, "sectors", [relative], "Accepted-step cumulative interior E_at_int; sum(channel_at) agrees at rtol1e-13, atol1e-14"),
            self._metric(config_id, "cylinder_front_band_fraction", self._fraction(scalar, denominator), R.FRACTION, R.TRAJECTORY, "front-band", [relative], "Saved shock_at / canonical E_at_int; fixed A_u radial +/-0.16 band; undefined at zero denominator"),
            self._metric(config_id, "cylinder_outside_band_fraction", self._fraction(denominator-scalar, denominator), R.FRACTION, R.TRAJECTORY, "front-band", [relative], "(canonical E_at_int - saved shock_at) / canonical E_at_int; same denominator, undefined at zero")]
        ev = f"ev.cylinder.{config_id}.sectors"
        curve_error = {"domain": "SCIENTIFIC", "code": "UNSUPPORTED_COMBINATION", "message": "Cartesian cumulative spatial curve does not apply to native Cylinder sectors",
            "target": {"resource_type": "spatial_curve", "identity": known(f"cylinder.{config_id}.sectors")}, "retryable": False, "details": [], "evidence_refs": [ev]}
        return {"total_budget": {"availability": "AVAILABLE", "value": metrics[0]}, "inside": {"availability": "AVAILABLE", "value": metrics[1]},
            "outside": {"availability": "AVAILABLE", "value": metrics[2]}, "fraction_format": "FRACTION", "mask_refs": [R.MASK_ID], "measure": R.MEASURE,
            "spatial_cumulative_curve": {"availability": "UNSUPPORTED", "error": curve_error}, "evidence_refs": [ev, f"ev.cylinder.{config_id}.front-band"]}

    def load_sectors(self, config_id):
        protocol, result, relative, z = self._allocation(config_id)
        scope = R.scope("def.Cylinder_sector_E_at_integrated", [R.MASK_ID])
        header = self._header(config_id, f"cylinder.{config_id}.sectors", "Cylinder_sector_E_at_integrated", R.ENTROPY, R.TRAJECTORY,
            "sectors", [relative, R.run_path(config_id, "stage_weighted_history.csv"), protocol["shock_localization_geometry"]["source"]],
            definition="16 saved angular bins of cumulative native interior-face entropy channels; dt/RK weights and native face measure already included; sum(channel_at)=canonical E_at_int at source tolerance rtol1e-13 atol1e-14; sector_fraction=channel_at[bin]/canonical E_at_int, zero denominator -> NOT_APPLICABLE", scope=scope)
        gh = self._header(config_id, f"cylinder.{config_id}.sectors.geometry", "Cylinder_angular_edges", R.ANGLE, R.time("STATIC"),
                          "sectors", [relative], definition="17 saved angular edges, radians; separate from entropy channel units")
        edges = self._array_ref(gh, "bin_edges", relative, "bins", z["bins"], ["theta_edge"])
        channels = [{"channel": c, "array_ref": self._array_ref(header, f"channel_{c}", relative, f"channel_{c}", z[f"channel_{c}"], ["theta_sector"])} for c in ("bg", "aa", "at", "total")]
        self._mask(config_id, protocol)
        return AllocationResult.model_validate({"result": header, "representation_type": "ANGULAR_SECTORS", "summary": self._summary(config_id, result, relative, z),
            "sector_count": 16, "bin_edges": edges, "channel_arrays": channels,
            "sector_fractions": [self._fraction(float(v), result["channel_totals"]["at"]) for v in z["channel_at"]], "front_band_summary_ref": f"cylinder.{config_id}.front-band"})

    def load_front_band(self, config_id):
        protocol, result, relative, z = self._allocation(config_id)
        header = self._header(config_id, f"cylinder.{config_id}.front-band", "Cylinder_front_band_E_at_integrated", R.ENTROPY, R.TRAJECTORY,
            "front-band", [relative, protocol["shock_localization_geometry"]["source"], R.run_path(config_id, "stage_weighted_history.csv")], scope=R.scope("def.Cylinder_front_band_E_at_integrated", [R.MASK_ID]),
            definition="Saved cumulative shock_at over fixed A_u radial +/-0.16 band within anchor angular span; dt*RK_weight*native_face_measure*pi_at integrated over the trajectory [0,2], interior-only")
        return AllocationResult.model_validate({"result": header, "representation_type": "REGION_SCALAR", "summary": self._summary(config_id, result, relative, z),
            "region_mask": self._mask(config_id, protocol), "integrated_value": known(float(z["shock_at"].item())),
            "fraction": self._fraction(float(z["shock_at"].item()), result["channel_totals"]["at"]), "denominator_result_id": f"cylinder.{config_id}.metric.E_at_int"})

    def load_allocation_overview(self, config_id):
        return CylinderAllocationOverview.model_validate({"experiment_id": "cylinder", "config_id": R.require_config(config_id),
            "sectors": {"availability": "AVAILABLE", "value": self.load_sectors(config_id)},
            "front_band": {"availability": "AVAILABLE", "value": self.load_front_band(config_id)},
            "cumulative_2d": R.MANIFEST["missing_cumulative_2d"]["ResourceSlot"], "limitations": [R.NO_MAP],
            "evidence_refs": [f"ev.cylinder.{config_id}.sectors", f"ev.cylinder.{config_id}.front-band", "ev.missing.cylinder-cumulative2d"]})

    def load_metrics(self, config_id, *, metric_id=None, snapshot_index=None):
        _, result = self._context(config_id)
        if snapshot_index is not None and (type(snapshot_index) is not int or snapshot_index != 5):
            raise unsupported_combination("Formal Cylinder metrics are saved only for the terminal state; five native-face frames do not imply a metric movie", resource_type="metrics", identity=known(config_id))
        if metric_id is not None and metric_id not in R.METRICS:
            raise system_error("INVALID_RESULT_ID", "Cylinder metric is not registered", status=404, availability="MISSING")
        relative = R.run_path(config_id, "physical_metrics.json")
        self._read(R.run_path(config_id, "final_state.npz"))
        saved = self._json(relative)
        if saved != result["physical_metrics"]:
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Saved physical metrics disagree with canonical run result")
        ev = f"ev.cylinder.{config_id}.metrics"
        items = []
        for semantic_id, (key, definition, u) in R.METRICS.items():
            if metric_id is not None and semantic_id != metric_id:
                continue
            value = saved.get(key)
            width = "width" in key
            rid = f"cylinder.{config_id}.metric.{semantic_id}"
            limits = [R.floor_limit(config_id, rid)] if width and config_id in ("B_u", "D_u") else []
            scope = {"id": "cylinder.terminal-detector", "description": "Saved terminal physical metric detector on the O-grid state; distinct from interior-only cumulative budget",
                "boundary_scope": known("Saved terminal state diagnostic; see detector definition"), "spatial_domain_ref": R.NA, "mask_refs": [], "definition_refs": [f"def.{semantic_id}"]}
            metric = self._metric(config_id, semantic_id, known(float(value)) if value is not None else unresolved("Formal source metric absent", "MISSING"), u, R.TERMINAL,
                "metrics", [relative, R.run_path(config_id, "final_state.npz")], definition, detector=R.detector(ev, semantic_id), limitations=limits, scope=scope)
            items.append({"availability": "AVAILABLE", "value": metric})
        return MetricCollection.model_validate({"experiment_id": "cylinder", "config_id": config_id, "items": items, "evidence_refs": [ev]})

    def _materialize(self, config_id):
        self._config(config_id)
        self.list_snapshots(config_id)
        for s in R.MANIFEST["runs"][config_id]["history_source"]["series"]:
            self.load_scalar_series(config_id, s["series_id"], limit=1)
        self.load_sectors(config_id)
        self.load_front_band(config_id)
        self.load_metrics(config_id)

    def _resolve_result(self, result_id):
        if not isinstance(result_id, str):
            raise system_error("INVALID_RESULT_ID", "Cylinder result is not registered", status=404, availability="MISSING")
        config_id = next((c for c in R.CONFIGS if result_id.startswith(f"cylinder.{c}.")), None)
        if config_id is None:
            raise system_error("INVALID_RESULT_ID", "Cylinder result is not registered", status=404, availability="MISSING")
        if result_id not in self._results:
            self._materialize(config_id)
        if result_id not in self._results:
            raise system_error("INVALID_RESULT_ID", "Cylinder result is not registered", status=404, availability="MISSING")
        self._context(config_id)
        header = self._results[result_id]
        source_ids = set(header["provenance"]["source_asset_ids"])
        for path, asset in R.ASSETS.items():
            if asset["asset_id"] in source_ids and path not in COMMON:
                self._read(path)
        return header

    def list_array_refs(self, result_id):
        """Registry seam for ARRAY01; contains descriptors only."""
        self._resolve_result(result_id)
        return [ref for (rid, _), (ref, _, _) in self._arrays.items() if rid == result_id]

    def load_array(self, result_id, array_id):
        header = self._resolve_result(result_id)
        registered = self._arrays.get((result_id, array_id))
        if registered is None:
            raise system_error("MISSING_SCIENTIFIC_ASSET", "Requested Cylinder array is not a saved registered member", status=404, availability="MISSING", evidence_refs=header["provenance"]["evidence_refs"])
        ref, relative, member = registered
        z = self._npz(relative)
        if member not in z:
            raise system_error("MISSING_SCIENTIFIC_ASSET", "Saved member is absent", status=404, availability="MISSING")
        return ScientificArray.model_validate({"result": header, "descriptor": ref["descriptor"], "values": z[member].ravel(order="C").tolist()})

    def load_evidence(self, evidence_id):
        if evidence_id == "ev.missing.cylinder-cumulative2d":
            for relative in COMMON:
                self._read(relative)
            return EvidenceRecord.model_validate(R.MANIFEST["missing_cumulative_2d"]["Evidence"])
        selected = next((c for c in R.CONFIGS if evidence_id.startswith(f"ev.cylinder.{c}.")), None)
        if selected is None or evidence_id.rsplit(".", 1)[-1] not in ("protocol", "snapshots", "history", "sectors", "front-band", "metrics"):
            raise system_error("UNKNOWN_EVIDENCE_ID", "Cylinder evidence is not registered", status=404, availability="MISSING")
        self._materialize(selected)
        contexts = [r for r in self._results.values() if evidence_id in r["provenance"]["evidence_refs"]]
        paths = sorted(self._sources[evidence_id])
        for p in paths:
            self._read(p)
        v = R.verification(evidence_id)
        assets = [{"asset_id": R.ASSETS[p]["asset_id"], "source_id": "J2C_cylinder_formal_v2", "source_display": p,
            "relative_origin": known(p), "role": "METHOD" if p.endswith(".py") else "CONFIG" if p == COMMON[0] else "ANALYSIS" if p.endswith(".md") else "DATA",
            "format": Path(p).suffix.lstrip(".").upper(), "recorded_data_hash": known(R.ASSETS[p].get("recorded_sha256") or R.ASSETS[p]["sha256"]),
            "current_data_hash": known(R.ASSETS[p]["sha256"]), "data_drift": known(False), "verification": v, "canonical_selected": True, "limitations": []} for p in paths]
        definitions = [self._definitions[(evidence_id, d)] for d in sorted({d for r in contexts for d in r["scope"]["definition_refs"]})]
        protocol, _ = self._context(selected)
        masks = [self._mask(selected, protocol)] if evidence_id.endswith(("sectors", "front-band")) else []
        method_hash = R.ASSETS[COMMON[5]]["sha256"]
        adapter_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        processing = [{"id": f"processing.cylinder.{selected}.format-mapping", "kind": "FORMAT_MAPPING",
            "description": "Source step+1 maps accepted interval to canonical endpoint; snapshots remain 1-based, completed step0 retained; NPZ members preserve native shape/C-order; units and stage/cumulative definitions remain separate; no scientific arrays reconstructed",
            "input_asset_ids": [a["asset_id"] for a in assets], "definition_refs": [d["id"] for d in definitions], "processing_hash": known(adapter_hash), "verification": v}]
        if masks:
            processing.append({"id": f"processing.cylinder.{selected}.fractions", "kind": "VERIFIED_DERIVATION",
                "description": "Only scalar fractions and complements derived: saved channel_at[bin]/canonical E_at_int; shock_at/E_at_int; (E_at_int-shock_at)/E_at_int. Zero denominator -> NOT_APPLICABLE. Sector totals verified rtol1e-13 atol1e-14; no interpolation or trajectory reconstruction.",
                "input_asset_ids": [a["asset_id"] for a in assets], "definition_refs": [d["id"] for d in definitions], "processing_hash": known(adapter_hash), "verification": v})
        return EvidenceRecord.model_validate({"schema_version": "1.0.0", "evidence_id": evidence_id,
            "result_ids": [r["result_id"] for r in contexts], "result_contexts": contexts, "experiment_id": known("cylinder"),
            "config_id": known(selected), "config": known(self._config(selected)), "definitions": definitions, "masks": masks,
            "method_name": known(protocol["method"]), "method_hash": known(method_hash), "recorded_source_hash": known(method_hash), "current_source_hash": known(method_hash),
            "source_observations": [{"asset_id": a["asset_id"], "recorded_hash": a["recorded_data_hash"], "current_hash": a["current_data_hash"], "drift": known(False), "observation_at": v["observation_at"]} for a in assets],
            "source_assets": assets, "data_hash": unresolved("No authoritative composite data hash recorded"), "freeze_reference": unresolved("Selected formal-v2 gate verification has no numerical release FREEZE", "NOT_APPLICABLE"),
            "processing": processing, "verification": v, "limitations": [R.NO_MAP] if masks else [lim for r in contexts for lim in r["limitations"]],
            "source_drift": known(False), "created_at": unresolved("Evidence creation date not scientifically established"), "verified_at": v["verified_at"],
            "related_evidence_refs": ["ev.missing.cylinder-cumulative2d", f"ev.cylinder.{selected}.front-band" if evidence_id.endswith("sectors") else f"ev.cylinder.{selected}.sectors"] if masks else [], "superseded_by": unresolved("Current selected dataset", "NOT_APPLICABLE")})

    def load_provenance(self, result_id):
        header = self._resolve_result(result_id)
        records = [self.load_evidence(ev) for ev in header["provenance"]["evidence_refs"]]
        return ResultProvenance.model_validate({"result_id": result_id, "provenance": header["provenance"], "evidence_records": records})
