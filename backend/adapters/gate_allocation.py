"""Gate allocation adapter: reads the three frozen cell allocations, read-only.

STRICT READ-ONLY. This module never writes, renames, deletes or modifies any
scientific file and never runs CFD. It reads only the frozen PASSAGE6
Experiment 1 package and maps ``Pi_at.npy`` (and its frozen entitlement /
analysis siblings) into canonical models.

Scientific contract preserved here:
  * CELL_FIELD only — never converted to faces, never projected/averaged.
  * cell-centered ``[y, x]`` ordering (C-order), 32x128.
  * trajectory-integrated (STATIC + TRAJECTORY_INTEGRATED [0, 0.08]); the saved
    array already includes native face measure, RK and time weights.
  * shock window is the fixed cell-center classification of the saved map,
    ``abs(x_i - x_s(y_j)) <= 0.08``; it is not recentered on an evolved front.
  * normalization is preserved: ``sum(Pi_at) == E_at``; no extra dx/dy/dt.

Forbidden and rejected here:
  * interpolating ``q_at`` — only the three matched values are addressable;
  * inventing a gate that does not exist;
  * altering the three frozen budgets;
  * producing face fields from the cell map.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.adapters.allocation import AllocationDescription
from backend.core.errors import (missing_resource, system_error,
                                 unsupported_combination)
from backend.models import (ExperimentCapability, ExperimentConfig, MaskSpec,
                            ScientificArray, ScientificDefinition, known,
                            unresolved)
from backend.models.allocation import AllocationResult, AllocationSummary
from backend.registry import gate_evidence as EV
from backend.registry import gate_registry as G

_ALLOCATION_ARRAY_ID = "allocation_at"
_CURVE_AXIS = "x"


@dataclass(frozen=True)
class _GateFacts:
    """Frozen facts read from one gate's recorded files (read-only)."""

    config_id: str
    q_at: float
    e_at: float
    e_total: float
    f_at: float
    inside_fraction: float
    outside_fraction: float
    values: np.ndarray


class GateAllocationAdapter:
    """Concrete allocation adapter over the three frozen gate variants.

    Conforms to ``AllocationAdapterProtocol``. Every call pins a single registry
    revision (defaults to the module revision) and reads only registered assets.
    """

    def __init__(self, scientific_root: str | Path = G.SCIENTIFIC_ROOT_WINDOWS,
                 *, registry_revision: str | None = None):
        self._root = Path(scientific_root)
        self._registry_revision = registry_revision or G.REGISTRY_REVISION

    # ------------------------------------------------------------------ list
    def list_gates(self) -> tuple[str, ...]:
        """The exactly-three frozen gate ids, in frozen order."""
        return G.gate_ids()

    def describe_capability(self) -> dict:
        """ExperimentCapability metadata for the gate allocation task."""
        return {
            "id": "gate.allocation",
            "experiment_id": G.EXPERIMENT_ID,
            "task": "trajectory-integrated cell allocation",
            "status": "SUPPORTED",
            "available_for_configs": list(G.CONFIG_ORDER),
            "config_support": [{
                "config_id": c,
                "status": "SUPPORTED",
                "reason": "Frozen Experiment 1 cumulative cell allocation; sum(Pi_at)=E_at",
                "result_refs": [f"gate.{c}.allocation"],
            } for c in G.CONFIG_ORDER],
            "controls": [{
                "name": "gate", "kind": "ENUM",
                "allowed_values": list(G.CONFIG_ORDER),
                "combination_registry_ref": known("gate.registry"),
            }],
            "tab_policy": {
                "tab_id": "allocation", "visible_for_family": True,
                "disabled_for_configs": [],
                "unsupported_deep_link_behavior": "EXPLAIN",
            },
            "result_refs": [f"gate.{c}.allocation" for c in G.CONFIG_ORDER],
            "limitations": [{
                "id": "lim.gate.no-playback", "code": "HISTORY_PLAYBACK_UNSUPPORTED",
                "description": "No entropy-history playback or arbitrary q/time for steady-state gate",
                "affected_refs": ["gate.allocation"], "severity": "WARNING",
            }],
            "evidence_refs": [G.ASSET_ID_ANALYSIS_CSV, G.ASSET_ID_README],
        }

    def list_configs(self) -> list[ExperimentConfig]:
        return [ExperimentConfig.model_validate(c) for c in G.configs()]

    # ----------------------------------------------------------- path helpers
    def _gate_path(self, config_id: str, member: str) -> Path:
        if config_id not in G.CONFIG_ORDER:
            raise KeyError(config_id)
        return self._root / G.GATE_FREEZE_REL / "results_snapshot" / config_id / member

    # ------------------------------------------------------------- facts read
    def _read_gate_facts(self, config_id: str) -> _GateFacts:
        """Read one gate's Pi_at array and frozen summary; never mutate the source."""
        pi = self._gate_path(config_id, "Pi_at.npy")
        ent = self._gate_path(config_id, "entropy.csv")
        if not pi.exists():
            raise missing_resource(
                "MISSING_SCIENTIFIC_ASSET", "Gate cell allocation asset is absent",
                resource_type="gate_allocation", identity=known(config_id))
        try:
            values = np.load(pi, allow_pickle=False)
            values = np.asarray(values, dtype=np.float64)
        except (OSError, ValueError) as exc:  # corrupt/absent array -> typed error
            raise system_error("SOURCE_READ_ERROR", "Gate allocation could not be read",
                               status=500, availability="ERROR", resource_type="gate_allocation",
                               identity=known(config_id)) from exc
        if values.shape != G.CELL_SHAPE:
            raise system_error("CANONICAL_SCHEMA_MISMATCH",
                               "Gate allocation shape differs from the frozen 32x128 map",
                               resource_type="gate_allocation", identity=known(config_id))
        if not np.all(np.isfinite(values)):
            raise system_error("CANONICAL_SCHEMA_MISMATCH",
                               "Gate allocation contains non-finite values",
                               resource_type="gate_allocation", identity=known(config_id))
        e_at = float(np.sum(values))
        frozen = G.FROZEN_SUMMARY[config_id]
        if abs(e_at - frozen["E_at"]) > G.INTEGRAL_ABS_THRESHOLD:
            raise system_error("SOURCE_DATA_DRIFT",
                               "Gate allocation integral disagrees with the frozen budget",
                               resource_type="gate_allocation", identity=known(config_id))
        # The remaining frozen summary numbers come from the recorded files.
        row = self._read_entropy_row(config_id)
        return _GateFacts(
            config_id=config_id,
            q_at=G.MATCHED_QAT[config_id],
            e_at=frozen["E_at"],
            e_total=row["E_total"],
            f_at=row["f_at"],
            inside_fraction=frozen["inside_fraction"],
            outside_fraction=frozen["outside_fraction"],
            values=values,
        )

    def _read_entropy_row(self, config_id: str) -> dict:
        path = self._gate_path(config_id, "entropy.csv")
        if not path.exists():
            raise missing_resource(
                "MISSING_SCIENTIFIC_ASSET", "Gate entropy summary asset is absent",
                resource_type="gate_allocation", identity=known(config_id))
        with path.open(newline="", encoding="utf-8") as handle:
            row = next(csv.DictReader(handle))
        return {key: float(value) for key, value in row.items()}

    # -------------------------------------------------------------- describe
    def describe_allocation(self, experiment_id: str, config_id: str, *,
                            registry_revision: str | None = None) -> AllocationDescription:
        if experiment_id != G.EXPERIMENT_ID:
            raise unsupported_combination(
                "Allocation describes only the gate experiment",
                resource_type="experiment", identity=known(experiment_id))
        if config_id not in G.CONFIG_ORDER:
            raise missing_resource(
                "UNKNOWN_CONFIG", "No such gate configuration",
                resource_type="gate_config", identity=known(config_id))
        definition = ScientificDefinition.model_validate({
            "id": G.SEMANTIC_ID, "semantic_id": G.SEMANTIC_ID,
            "title": "Gate trajectory-integrated cell allocation",
            "definition": ("Cumulative stage-weighted q_at entropy-production contributions "
                           "allocated to cells (interior face contributions split to neighbors, "
                           "full x-boundary retained)"),
            "time_rule": "STATIC + TRAJECTORY_INTEGRATED over [0,0.08]; 1912 accepted steps",
            "spatial_rule": "Cell-centered [y,x], 32x128; sum(values)=E_at",
            "unit": {"id": "model_integrated_entropy", "system": "MODEL",
                     "quantity": "integrated entropy", "label": "model integrated entropy",
                     "si_mapping": unresolved("No established SI mapping")},
            "mask_refs": [G.MASK_ID],
            "detector": unresolved("Direct cell allocation, not a detector metric", "NOT_APPLICABLE"),
            "evidence_refs": [G.ASSET_ID_ANALYSIS_CSV, G.ASSET_ID_README],
            "limitations": [],
        })
        return AllocationDescription(
            capability=ExperimentCapability.model_validate(self.describe_capability()),
            representation_type="CELL_FIELD",
            measure_definition="cell integrated",
            coordinate_convention="Cartesian [y,x] cell centers; x=(i+.5)/128, y=(j+.5)/32",
            mask_definition=G.MASK_DEFINITION,
            definition=definition,
        )

    # -------------------------------------------------------------- metadata
    def load_allocation_metadata(self, result_id: str, *,
                                 registry_revision: str | None = None) -> AllocationResult:
        config_id = self._config_from_result(result_id)
        facts = self._read_gate_facts(config_id)
        header = self._result_header(facts)
        descriptor = self._descriptor()
        measure = self._measure()
        field = {
            "field_id": _ALLOCATION_ARRAY_ID,
            "label": "Trajectory-integrated cell allocation",
            "result": header,
            "domain": self._domain(header, measure),
            "array_ref": {"result_id": result_id, "descriptor": descriptor},
            "mask_refs": [G.MASK_ID],
        }
        summary = self._summary_payload(facts, measure)
        return AllocationResult.model_validate({
            "result": header,
            "representation_type": "CELL_FIELD",
            "fields": [field],
            "summary": summary,
        })

    # ----------------------------------------------------------------- array
    def load_allocation_array(self, result_id: str, array_id: str, *,
                              registry_revision: str | None = None) -> ScientificArray:
        config_id = self._config_from_result(result_id)
        if array_id != _ALLOCATION_ARRAY_ID:
            raise missing_resource(
                "INVALID_RESULT_ID", "No such allocation array on this result",
                resource_type="gate_allocation_array", identity=known(array_id))
        facts = self._read_gate_facts(config_id)
        header = self._result_header(facts)
        flat = [float(v) for v in facts.values.reshape(-1, order="C")]
        return ScientificArray.model_validate({
            "result": header,
            "descriptor": self._descriptor(),
            "values": flat,
        })

    # ------------------------------------------------------------------ mask
    def load_mask(self, mask_id: str, *,
                  registry_revision: str | None = None) -> MaskSpec:
        if mask_id != G.MASK_ID:
            raise missing_resource(
                "UNKNOWN_ASSET_ID", "No such gate mask",
                resource_type="mask", identity=known(mask_id))
        return MaskSpec.model_validate({
            "id": G.MASK_ID,
            "type": "GATE_CELL_SHOCK_WINDOW",
            "domain_refs": ["gate.cells"],
            "definition": G.MASK_DEFINITION,
            "parameters": [
                {"name": "half_width", "value": known(G.FRONT_WINDOW_HALF_WIDTH)},
                {"name": "front_x0", "value": known(G.FRONT_X0)},
                {"name": "front_amplitude", "value": known(G.FRONT_AMPLITUDE)},
                {"name": "front_wavenumber", "value": known(G.FRONT_WAVENUMBER)},
            ],
            "index_sets": [],
            "mask_array_refs": [],
            "scope": {
                "id": "gate.cell-window-scope",
                "description": "Cell-center shock window on the saved 32x128 cell map",
                "boundary_scope": known("x_lower pre-shock inflow; x_upper outflow; y periodic"),
                "spatial_domain_ref": known("gate.cells"),
                "mask_refs": [],
                "definition_refs": [G.SEMANTIC_ID],
            },
            "verification": dict(EV._FROZEN_VERIFICATION),
            "evidence_refs": [G.ASSET_ID_README, G.ASSET_ID_ANALYSIS_CSV],
        })

    # --------------------------------------------------------------- summary
    def load_summary_metrics(self, result_id: str, *,
                             registry_revision: str | None = None) -> AllocationSummary:
        config_id = self._config_from_result(result_id)
        facts = self._read_gate_facts(config_id)
        return AllocationSummary.model_validate(self._summary_payload(facts, self._measure()))

    # ================================================================ helpers
    def _config_from_result(self, result_id: str) -> str:
        parts = result_id.split(".")
        if len(parts) < 2 or parts[0] != G.EXPERIMENT_ID:
            raise unsupported_combination(
                "Allocation result id must belong to the gate experiment",
                resource_type="allocation_result", identity=known(result_id))
        config_id = parts[1]
        if config_id not in G.CONFIG_ORDER:
            raise missing_resource(
                "UNKNOWN_CONFIG", "No such gate configuration",
                resource_type="gate_config", identity=known(config_id))
        if parts[2:] != ["allocation"]:
            raise missing_resource(
                "INVALID_RESULT_ID", "Unsupported gate allocation result id",
                resource_type="allocation_result", identity=known(result_id))
        return config_id

    def _result_header(self, facts: _GateFacts) -> dict:
        na = unresolved("Not applicable to steady-state gate allocation", "NOT_APPLICABLE")
        return {
            "schema_version": "1.0.0",
            "result_id": f"gate.{facts.config_id}.allocation",
            "experiment_id": G.EXPERIMENT_ID,
            "config_id": facts.config_id,
            "semantic_id": G.SEMANTIC_ID,
            "data_origin": "FROZEN_PRODUCTION",
            "availability": "AVAILABLE",
            "time": {
                "sampling": "STATIC",
                "accumulation": "TRAJECTORY_INTEGRATED",
                "physical_time": known(G.FINAL_TIME),
                "interval": known({"start": 0.0, "end": G.FINAL_TIME}),
                "step_index": known(G.ACCEPTED_STEPS),
                "stage_index": na,
                "snapshot_index": na,
                "index_convention": "source_step_index preserved; 1912 accepted steps",
            },
            "scope": {
                "id": "gate.cells",
                "description": f"Gate {facts.config_id} frozen cumulative cell allocation",
                "boundary_scope": known("x_lower pre-shock inflow; x_upper outflow; y periodic"),
                "spatial_domain_ref": known("gate.cells"),
                "mask_refs": [G.MASK_ID],
                "definition_refs": [G.SEMANTIC_ID],
            },
            "unit": {"id": "model_integrated_entropy", "system": "MODEL",
                     "quantity": "integrated entropy", "label": "model integrated entropy",
                     "si_mapping": unresolved("No established SI mapping")},
            "verification": dict(EV._FROZEN_VERIFICATION),
            "provenance": {
                "evidence_refs": [f"ev.gate.{facts.config_id}.allocation"],
                "source_asset_ids": [G.pi_at_asset_id(facts.config_id),
                                     G.ASSET_ID_MATCHED_QAT, G.ASSET_ID_ANALYSIS_CSV],
                "registry_revision": self._registry_revision,
                "data_revision": G.DATA_REVISION,
                "release_id": unresolved("No release bundle created", "NOT_APPLICABLE"),
                "source_drift": unresolved("Observe all source dependencies before asserting false"),
            },
            "limitations": [dict(EV._CELL_DEFINITION_LIMITATION)],
        }

    def _descriptor(self) -> dict:
        return {
            "array_id": _ALLOCATION_ARRAY_ID,
            "dtype": "float64",
            "shape": list(G.CELL_SHAPE),
            "order": "C",
            "axes": ["y", "x"],
            "encoding": "FLAT_JSON",
            "element_count": int(G.CELL_SHAPE[0] * G.CELL_SHAPE[1]),
        }

    def _measure(self) -> dict:
        return {
            "id": G.MEASURE_ID,
            "description": "Saved cell allocation already includes native face measure, RK and time weights",
            "integral_rule": "sum(values)=E_at",
            "measure_parameters": [],
            "includes_time_weights": True,
            "includes_spatial_measure": True,
        }

    def _domain(self, header: dict, measure: dict) -> dict:
        unit = header["unit"]
        axes = [{
            "name": axis, "size": size,
            "coordinate_values": unresolved("Cell-center coordinates derived from the frozen grid"),
            "coordinate_array_ref": unresolved("No separately saved coordinate array", "NOT_APPLICABLE"),
            "unit": dict(unit),
        } for axis, size in zip(("y", "x"), G.CELL_SHAPE)]
        return {
            "id": "gate.cells",
            "coordinate_system": "CARTESIAN",
            "location_type": "CARTESIAN_CELL",
            "shape": list(G.CELL_SHAPE),
            "axes": axes,
            "extent": [{"axis": "x", "lower": G.DOMAIN_X[0], "upper": G.DOMAIN_X[1]},
                       {"axis": "y", "lower": G.DOMAIN_Y[0], "upper": G.DOMAIN_Y[1]}],
            "measure_convention": dict(measure),
            "boundary_scope": known("x_lower pre-shock inflow; x_upper outflow; y periodic"),
            "geometry_ref": unresolved("Cartesian coordinate axes", "NOT_APPLICABLE"),
            "evidence_refs": [G.pi_at_asset_id(header["config_id"]), G.ASSET_ID_README],
        }

    def _metric(self, facts: _GateFacts, *, metric_id: str, label: str,
                value: float, unit: dict, integral_rule: str,
                definition_id: str) -> dict:
        header = self._result_header(facts)
        header["result_id"] = f"gate.{facts.config_id}.summary.{metric_id}"
        header["unit"] = unit
        header["scope"]["mask_refs"] = [G.MASK_ID]
        header["scope"]["definition_refs"] = [definition_id]
        return {
            "result": header,
            "metric_id": metric_id,
            "value": known(value),
            "definition_id": definition_id,
            "detector": unresolved("Direct frozen summary value", "NOT_APPLICABLE"),
            "time_scope": header["time"],
            "display_label": label,
            "resolution_limit": unresolved("No declared resolution limit"),
        }

    def _summary_payload(self, facts: _GateFacts, measure: dict) -> dict:
        entropy_unit = {"id": "model_integrated_entropy", "system": "MODEL",
                        "quantity": "integrated entropy", "label": "model integrated entropy",
                        "si_mapping": unresolved("No established SI mapping")}
        fraction_unit = {"id": "dimensionless_fraction", "system": "DIMENSIONLESS",
                         "quantity": "fraction", "label": "dimensionless fraction",
                         "si_mapping": unresolved("Dimensionless quantity", "NOT_APPLICABLE")}
        missing = {
            "availability": "MISSING",
            "error": {
                "domain": "SCIENTIFIC", "code": "MISSING_SCIENTIFIC_ASSET",
                "message": "No stored spatial cumulative curve; a derived curve requires explicit verified processing",
                "target": {"resource_type": "spatial_curve", "identity": unresolved("No stored curve asset")},
                "retryable": False, "details": [],
                "evidence_refs": [G.ASSET_ID_README],
            },
        }
        return {
            "total_budget": {
                "availability": "AVAILABLE",
                "value": self._metric(facts, metric_id="gate_E_at", label="Integrated q_at cell budget",
                                      value=facts.e_at, unit=entropy_unit,
                                      integral_rule="sum(Pi_at)", definition_id=G.SEMANTIC_ID),
            },
            "inside": {
                "availability": "AVAILABLE",
                "value": self._metric(facts, metric_id="gate_shock_window_fraction",
                                      label="Shock-window cell fraction", value=facts.inside_fraction,
                                      unit=fraction_unit,
                                      integral_rule="sum(saved cell within fixed mask)/E_at",
                                      definition_id="gate_shock_window_fraction"),
            },
            "outside": {
                "availability": "AVAILABLE",
                "value": self._metric(facts, metric_id="gate_outside_window_fraction",
                                      label="Outside-window cell fraction", value=facts.outside_fraction,
                                      unit=fraction_unit,
                                      integral_rule="sum(saved cell outside fixed mask)/E_at",
                                      definition_id="gate_outside_window_fraction"),
            },
            "fraction_format": "FRACTION",
            "mask_refs": [G.MASK_ID],
            "measure": measure,
            "spatial_cumulative_curve": missing,
            "evidence_refs": [f"ev.gate.{facts.config_id}.allocation",
                              G.ASSET_ID_ANALYSIS_CSV, G.ASSET_ID_README],
        }
