"""Read-only D_u trajectory-integrated native-face allocation adapter.

Reads immutable in-memory bytes under pinned hashes, then reobserves all selected
dependencies to reject mixed reads. No imports or execution of scientific code,
no interpolation, no averaging, and no fabricated allocation for other configs.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile

import numpy as np

from backend.adapters.allocation import AllocationDescription
from backend.core.errors import DomainError, missing_resource, system_error
from backend.models import (EvidenceRecord, MaskSpec, ResultProvenance, ScientificArray,
                            known, unresolved)
from backend.models.allocation import AllocationResult, AllocationSummary
from backend.registry import case8_allocation as R
from backend.registry import case8_semantics as SEM
from backend.registry import case8_source_constants as C


class Case8AllocationAdapter:
    """Optional AllocationAdapterProtocol implementation, separate from flow APIs."""

    def __init__(self, scientific_root: str | Path = C.SCIENTIFIC_ROOT_WINDOWS):
        self._root = Path(scientific_root)

    @property
    def registry_revision(self):
        return R.REGISTRY_REVISION

    def _revision(self, revision):
        if revision is not None and revision != self.registry_revision:
            raise system_error("REVISION_UNAVAILABLE", "Allocation registry revision unavailable", status=409)

    def _config(self, experiment_id, config_id):
        if experiment_id != "case8":
            raise system_error("UNKNOWN_EXPERIMENT", "Experiment is not registered by this adapter", status=404)
        if config_id not in C.CONFIG_ORDER:
            raise system_error("UNKNOWN_CONFIG", "Configuration is not registered", status=404)
        if config_id != "D_u":
            raise missing_resource("MISSING_SCIENTIFIC_ASSET", "No saved cumulative native-face allocation for this configuration",
                                   resource_type="allocation", identity=known(f"case8.{config_id}.allocation"))

    def _result(self, result_id):
        missing = {f"case8.{cid}.allocation": cid for cid in ("A_u", "B_u", "C_u")}
        if result_id in missing:
            self._config("case8", missing[result_id])
        if result_id != R.RESULT_ID:
            raise system_error("INVALID_RESULT_ID", "Allocation result identity is not registered", status=404)

    def _read_bytes(self, name):
        path = self._root / R.FREEZE_DIR / name
        try:
            before = path.stat()
            raw = path.read_bytes()
            after = path.stat()
        except FileNotFoundError:
            raise missing_resource("MISSING_SCIENTIFIC_ASSET", "A registered allocation dependency is missing",
                                   resource_type="asset", identity=known(R.ASSETS[name][0])) from None
        except OSError:
            raise system_error("SOURCE_READ_ERROR", "Allocation dependency could not be read") from None
        stamp = lambda s: (s.st_size, s.st_mtime_ns, s.st_ino)
        if stamp(before) != stamp(after):
            raise self._changed()
        return raw, stamp(after)

    @staticmethod
    def _changed():
        return system_error("SOURCE_CHANGED_DURING_READ", "Allocation dependencies changed during read",
                            status=409, domain="SCIENTIFIC", evidence_refs=[R.EVIDENCE_ID])

    def _bundle(self):
        blobs, stamps = {}, {}
        for name, (_, expected, *_rest) in R.ASSETS.items():
            raw, stamp = self._read_bytes(name)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise system_error("SOURCE_DATA_DRIFT", "Allocation dependency does not match its recorded SHA256",
                                   status=409, domain="SCIENTIFIC", resource_type="asset",
                                   identity=known(R.ASSETS[name][0]), evidence_refs=[R.EVIDENCE_ID])
            blobs[name], stamps[name] = raw, stamp
        for name, raw in blobs.items():
            try:
                current, stamp = self._read_bytes(name)
            except DomainError:
                raise self._changed() from None
            if current != raw or stamp != stamps[name]:
                raise self._changed()
        try:
            metadata = {name: json.loads(blobs[name]) for name in (
                "rerun_config.json", "rerun_metrics.json", "verification_report.json", "FREEZE_MANIFEST.json")}
            self._validate_metadata(metadata)
        except (ValueError, KeyError, TypeError):
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Frozen allocation metadata is inconsistent") from None
        return blobs, metadata, datetime.now(timezone.utc)

    @staticmethod
    def _validate_metadata(metadata):
        config = metadata["rerun_config.json"]
        report = metadata["verification_report.json"]
        manifest = metadata["FREEZE_MANIFEST.json"]
        if (config["case"], config["configuration"], config["mode"], config["number_of_steps"],
            config["final_time"], config["q_at"], config["grid"]["nx"], config["grid"]["ny"],
            config["method_sha256"]) != ("Case8", "D_u", "DIAGNOSTIC_RERUN", 1912, 0.08, 0.396, 128, 32, R.METHOD_HASH):
            raise ValueError("Identity or trajectory mismatch")
        if not report["FREEZE_ALLOWED"] or not all(report["GATES"].values()):
            raise ValueError("Upstream verification gates did not pass")
        entries = {entry["relative_path"]: entry for entry in manifest["files"]}
        for name, (_, sha, *_rest) in R.ASSETS.items():
            if name != "FREEZE_MANIFEST.json" and entries[name]["sha256"] != sha:
                raise ValueError("Manifest baseline mismatch")

    def describe_allocation(self, experiment_id: str, config_id: str, *,
                            registry_revision: str | None = None) -> AllocationDescription:
        self._revision(registry_revision)
        self._config(experiment_id, config_id)
        return AllocationDescription(capability=R.capability(), representation_type="FACE_FIELD",
                                     measure_definition="face integrated", coordinate_convention=R.COORDINATE_CONVENTION,
                                     mask_definition=R.MASK_DEFINITION, definition=R.definition())

    @staticmethod
    def _header(result_id, observed, *, unit=None, semantic=None, assets=None, masks=None):
        return {
            "schema_version": "1.0.0", "result_id": result_id, "experiment_id": "case8", "config_id": "D_u",
            "semantic_id": semantic or "Case8_face_Pi_at_integrated", "data_origin": "DIAGNOSTIC_RERUN",
            "availability": "AVAILABLE",
            "time": {"sampling": "TERMINAL", "accumulation": "TRAJECTORY_INTEGRATED",
                     "physical_time": known(0.08), "interval": known({"start": 0.0, "end": 0.08}),
                     "step_index": known(1912), "stage_index": unresolved("Full accepted-step trajectory", "NOT_APPLICABLE"),
                     "snapshot_index": unresolved("No cumulative snapshot sequence", "NOT_APPLICABLE"),
                     "index_convention": "1912 accepted steps; full trajectory, no playback index"},
            "scope": {"id": "case8.native-face-budget", "description": R.COORDINATE_CONVENTION,
                      "boundary_scope": known(R.BOUNDARY), "spatial_domain_ref": known("case8.native-faces"),
                      "mask_refs": [R.MASK_ID] if masks is None else masks,
                      "definition_refs": [semantic or "Case8_face_Pi_at_integrated"]},
            "unit": deepcopy(unit or R.FACE_UNIT), "verification": R.verification(observed),
            "provenance": {"evidence_refs": [R.EVIDENCE_ID],
                           "source_asset_ids": assets or [item[0] for item in R.ASSETS.values()],
                           "registry_revision": R.REGISTRY_REVISION, "data_revision": R.DATA_REVISION,
                           "release_id": unresolved("No release bundle created", "NOT_APPLICABLE"),
                           "source_drift": known(False)},
            "limitations": deepcopy(R.LIMITATIONS),
        }

    def _array_header(self, array_id, observed):
        if array_id.endswith("_window_mask"):
            mask_unit = {"id": "dimensionless_mask", "system": "DIMENSIONLESS", "quantity": "mask membership",
                         "label": "boolean mask membership", "si_mapping": unresolved("Dimensionless membership", "NOT_APPLICABLE")}
            header = self._header(R.array_result_id(array_id), observed, unit=mask_unit,
                                  semantic="Case8_native_face_shock_window", assets=[R.MASK_ASSET_ID])
        elif array_id in ("x_face", "x_cell", "y_face"):
            header = self._header(R.array_result_id(array_id), observed, unit=SEM.UNIT_MODEL_LENGTH,
                                  semantic="Case8_native_face_coordinates", assets=[R.DATA_ASSET_ID], masks=[])
        else:
            return self._header(R.array_result_id(array_id), observed)
        na = unresolved("Static saved geometry or prescribed initial-front mask", "NOT_APPLICABLE")
        header["time"] = {"sampling": "STATIC", "accumulation": "NONE", "physical_time": na,
                          "interval": na, "step_index": na, "stage_index": na, "snapshot_index": na,
                          "index_convention": "Static native-face geometry/mask; no time index"}
        return header

    def _field(self, array_id, observed):
        xnormal = array_id == "pi_at_x_faces"
        _, shape, _, _ = R.ARRAYS[array_id]
        axes = []
        for axis, size, coordinate in (("y", shape[0], None if xnormal else "y_face"),
                                       ("x", shape[1], "x_face" if xnormal else "x_cell")):
            axes.append({"name": axis, "size": size, "unit": SEM.UNIT_MODEL_LENGTH,
                         "coordinate_values": unresolved("Coordinates are loaded through registered references", "NOT_APPLICABLE"),
                         "coordinate_array_ref": known(R.array_ref(coordinate)) if coordinate else
                         unresolved("y_cell is not saved; y=(j+0.5)/32 convention retained; no synthesized coordinate array")})
        return {"field_id": array_id, "label": "Time-integrated Pi_at on " + ("x-normal faces" if xnormal else "y-normal faces"),
                "result": self._array_header(array_id, observed), "array_ref": R.array_ref(array_id), "mask_refs": [R.MASK_ID],
                "domain": {"id": R.DOMAINS[array_id], "coordinate_system": "CARTESIAN",
                           "location_type": "CARTESIAN_X_FACE" if xnormal else "CARTESIAN_Y_FACE",
                           "shape": list(shape), "axes": axes,
                           "extent": [{"axis": "x", "lower": 0.0, "upper": 1.0}, {"axis": "y", "lower": 0.0, "upper": 1.0}],
                           "measure_convention": deepcopy(R.MEASURE), "boundary_scope": known(R.BOUNDARY),
                           "geometry_ref": unresolved("Cartesian native-face axes", "NOT_APPLICABLE"), "evidence_refs": [R.EVIDENCE_ID]}}

    def _summary(self, metadata, observed):
        metrics = metadata["rerun_metrics.json"]
        total = metrics["e_at_total_accum"]
        def metric(name, raw, unit, semantic):
            header = self._header(f"{R.RESULT_ID}.{name}", observed, unit=unit, semantic=semantic)
            value = known(raw) if total != 0 else unresolved("ZERO_DENOMINATOR", "NOT_APPLICABLE")
            if name == "total_budget":
                value = known(raw)
            return {"availability": "AVAILABLE", "value": {
                "result": header, "metric_id": name, "value": value, "definition_id": semantic,
                "detector": unresolved("Saved accumulated budget", "NOT_APPLICABLE"), "time_scope": header["time"],
                "display_label": name, "resolution_limit": unresolved("No bound measurement resolution")}}
        return {"total_budget": metric("total_budget", total, SEM.UNIT_MODEL_ENTROPY, "E_at_cumulative"),
                "inside": metric("inside", metrics["e_at_inside_accum"]/total if total else 0.0, SEM.UNIT_FRACTION, "Case8_face_window_fraction"),
                "outside": metric("outside", metrics["e_at_outside_accum"]/total if total else 0.0, SEM.UNIT_FRACTION, "Case8_face_outside_fraction"),
                "fraction_format": "FRACTION", "mask_refs": [R.MASK_ID], "measure": deepcopy(R.MEASURE),
                "spatial_cumulative_curve": {"availability": "MISSING", "error": missing_resource(
                    "MISSING_SCIENTIFIC_ASSET", "No saved verified spatial cumulative curve",
                    resource_type="spatial_curve", identity=known("case8.D_u.allocation.spatial_curve")).body.model_dump()},
                "evidence_refs": [R.EVIDENCE_ID]}

    def _metadata(self, metadata, observed):
        return AllocationResult.model_validate({"result": self._header(R.RESULT_ID, observed), "representation_type": "FACE_FIELD",
                                               "fields": [self._field(name, observed) for name in R.DOMAINS],
                                               "summary": self._summary(metadata, observed)})

    def load_allocation_metadata(self, result_id: str, *,
                                 registry_revision: str | None = None) -> AllocationResult:
        self._revision(registry_revision)
        self._result(result_id)
        _, metadata, observed = self._bundle()
        return self._metadata(metadata, observed)

    def load_summary_metrics(self, result_id: str, *,
                             registry_revision: str | None = None) -> AllocationSummary:
        self._revision(registry_revision)
        self._result(result_id)
        _, metadata, observed = self._bundle()
        return AllocationSummary.model_validate(self._summary(metadata, observed))

    @staticmethod
    def _decode_faces(blobs, metadata):
        """Validate native schema and closure without modifying any source values."""
        try:
            with np.load(BytesIO(blobs["Pi_at_trajectory_integrated.npz"]), allow_pickle=False) as data:
                arrays = {key: data[key] for key in data.files}
            with np.load(BytesIO(blobs["shock_window_final_or_definition.npz"]), allow_pickle=False) as data:
                masks = {key: data[key] for key in data.files}
            for key, (_, shape, dtype, _) in R.ARRAYS.items():
                array = masks[key] if key.endswith("_window_mask") else arrays[key]
                if array.shape != shape or str(array.dtype) != dtype or not np.isfinite(array).all():
                    raise ValueError("Invalid native face schema")
            for key in masks:
                if key not in arrays or not np.array_equal(masks[key], arrays[key]):
                    raise ValueError("Mask/geometry assets disagree")
            for key, expected in {"dx": 1.0/128, "dy": 1.0/32, "final_time": 0.08,
                                  "steps": 1912, "q_aa": 3.96, "q_at": 0.396}.items():
                if arrays[key].shape != () or arrays[key].item() != expected:
                    raise ValueError("Integrated trajectory metadata mismatch")
            metrics = metadata["rerun_metrics.json"]
            dx, dy = arrays["dx"].item(), arrays["dy"].item()
            x, y = arrays["pi_at_x_faces"], arrays["pi_at_y_faces"]
            total = float(dy*x.sum() + dx*y.sum())
            inside = float(dy*x[masks["x_window_mask"]].sum() + dx*y[masks["y_window_mask"]].sum())
            tolerance = metrics["e_at_internal_closure_abs_error"] + 1e-17
            if abs(total - metrics["e_at_total_accum"]) > tolerance or abs(inside - metrics["e_at_inside_accum"]) > tolerance:
                raise ValueError("Native face budget closure mismatch")
            if abs((total-inside) - metrics["e_at_outside_accum"]) > tolerance:
                raise ValueError("Outside budget closure mismatch")
        except (ValueError, TypeError, KeyError, OSError, EOFError, BadZipFile):
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Frozen native-face arrays fail shape/dtype/mask/budget validation") from None
        return arrays, masks

    def load_allocation_array(self, result_id: str, array_id: str, *,
                              registry_revision: str | None = None) -> ScientificArray:
        self._revision(registry_revision)
        if array_id not in R.ARRAYS:
            raise system_error("INVALID_RESULT_ID", "Allocation array identity is not registered", status=404)
        if result_id != R.array_result_id(array_id):
            self._result(result_id)  # Parent allocation selector is also accepted.
        blobs, metadata, observed = self._bundle()
        arrays, masks = self._decode_faces(blobs, metadata)
        values = masks[array_id] if array_id.endswith("_window_mask") else arrays[array_id]
        return ScientificArray.model_validate({"result": self._array_header(array_id, observed),
                                               "descriptor": R.array_ref(array_id)["descriptor"],
                                               "values": values.reshape(-1, order="C").tolist()})

    def _mask(self, observed):
        return MaskSpec.model_validate({
            "id": R.MASK_ID, "type": "CASE8_NATIVE_FACE_SHOCK_WINDOW", "domain_refs": list(R.DOMAINS.values()),
            "definition": R.MASK_DEFINITION, "parameters": [{"name": "half_width", "value": known(0.08)}],
            "index_sets": [], "mask_array_refs": [R.array_ref(name) for name in ("x_window_mask", "y_window_mask")],
            "scope": self._header(R.RESULT_ID, observed)["scope"], "verification": R.verification(observed), "evidence_refs": [R.EVIDENCE_ID]})

    def load_mask(self, mask_id: str, *, registry_revision: str | None = None) -> MaskSpec:
        self._revision(registry_revision)
        if mask_id != R.MASK_ID:
            raise system_error("INVALID_RESULT_ID", "Mask identity is not registered", status=404)
        _, _, observed = self._bundle()
        return self._mask(observed)

    def load_evidence(self, evidence_id: str, *, registry_revision: str | None = None) -> EvidenceRecord:
        self._revision(registry_revision)
        if evidence_id != R.EVIDENCE_ID:
            raise system_error("UNKNOWN_EVIDENCE_ID", "Allocation evidence is not registered", status=404)
        blobs, metadata, observed = self._bundle()
        allocation = self._metadata(metadata, observed).root
        assets = []
        for name, (identity, sha, role, fmt, status) in R.ASSETS.items():
            verification = R.verification(observed)
            verification["status"] = status
            assets.append({"asset_id": identity, "source_id": "scientific-root-v1", "source_display": name,
                           "relative_origin": known(f"{R.FREEZE_DIR}/{name}"), "role": role, "format": fmt,
                           "recorded_data_hash": known(sha), "current_data_hash": known(hashlib.sha256(blobs[name]).hexdigest()),
                           "data_drift": known(False), "verification": verification, "canonical_selected": True, "limitations": []})
        contexts = [allocation.result.model_dump(mode="python")]
        contexts += [self._array_header(name, observed) for name in R.ARRAYS]
        contexts += [slot.root.value.result.model_dump(mode="python") for slot in (
            allocation.summary.total_budget, allocation.summary.inside, allocation.summary.outside)]
        manifest_id, manifest_hash, *_ = R.ASSETS["FREEZE_MANIFEST.json"]
        return EvidenceRecord.model_validate({
            "schema_version": "1.0.0", "evidence_id": R.EVIDENCE_ID, "result_ids": [item["result_id"] for item in contexts],
            "result_contexts": contexts, "experiment_id": known("case8"), "config_id": known("D_u"),
            "config": unresolved("Authoritative diagnostic parameters are in the hashed rerun_config asset"),
            "definitions": [R.definition().model_dump(mode="python")], "masks": [self._mask(observed).model_dump(mode="python")],
            "method_name": known("cross_mode_ec_unified_v1"), "method_hash": known(R.METHOD_HASH),
            "recorded_source_hash": known(R.ASSETS["Pi_at_trajectory_integrated.npz"][1]),
            "current_source_hash": known(hashlib.sha256(blobs["Pi_at_trajectory_integrated.npz"]).hexdigest()),
            "source_observations": [{"asset_id": a["asset_id"], "recorded_hash": a["recorded_data_hash"],
                                     "current_hash": a["current_data_hash"], "drift": known(False), "observation_at": known(observed)} for a in assets],
            "source_assets": assets, "data_hash": known(R.ASSETS["Pi_at_trajectory_integrated.npz"][1]),
            "freeze_reference": known({"freeze_id": "case8.D_u.spatial-rerun.freeze", "manifest_asset_id": manifest_id,
                                       "recorded_at": unresolved("Upstream manifest has no timestamp"), "hash": known(manifest_hash)}),
            "processing": [{"id": "processing.case8.D_u.allocation.read", "kind": "FORMAT_MAPPING",
                            "description": "Verbatim saved members to C-order flat arrays; no scientific code executed or values transformed",
                            "input_asset_ids": [a["asset_id"] for a in assets], "definition_refs": ["Case8_face_Pi_at_integrated"],
                            "processing_hash": unresolved("Adapter code hash not recorded"),
                            "verification": {"status": "NOT_APPLICABLE", "basis": ["Read-only format mapping"],
                                             "verified_at": unresolved("Not scientific verification", "NOT_APPLICABLE"),
                                             "observation_at": known(observed), "evidence_refs": [R.EVIDENCE_ID]}}],
            "verification": R.verification(observed), "limitations": deepcopy(R.LIMITATIONS), "source_drift": known(False),
            "created_at": unresolved("No authoritative result creation timestamp"),
            "verified_at": unresolved("Upstream verification timestamp not recorded"), "related_evidence_refs": [],
            "superseded_by": unresolved("No known replacement", "NOT_APPLICABLE")})

    def load_provenance(self, result_id: str, *, registry_revision: str | None = None) -> ResultProvenance:
        self._revision(registry_revision)
        registered = {R.RESULT_ID, *(R.array_result_id(name) for name in R.ARRAYS),
                      *(f"{R.RESULT_ID}.{name}" for name in ("total_budget", "inside", "outside"))}
        if result_id not in registered:
            self._result(result_id)
        evidence = self.load_evidence(R.EVIDENCE_ID, registry_revision=registry_revision)
        for result in evidence.result_contexts:
            if result.result_id == result_id:
                return ResultProvenance(result_id=result_id, provenance=result.provenance, evidence_records=[evidence])
        self._result(result_id)
        raise system_error("INVALID_RESULT_ID", "Allocation result identity is not registered", status=404)
