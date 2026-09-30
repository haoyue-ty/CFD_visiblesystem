"""Case8 canonical registry: configurations, capabilities and snapshot schedule.

Pure metadata derived from the read-only scientific source and the frozen
schema. The registry never loads scientific arrays; it supplies the stable
identities the adapter uses to locate and read real files.
"""
from __future__ import annotations

from typing import Final

from backend.models.core import known, unresolved
from backend.registry import case8_evidence as EV
from backend.registry import case8_semantics as SEM
from backend.registry import case8_source_constants as C

EXPERIMENT_ID: Final[str] = "case8"
REGISTRY_REVISION: Final[str] = "case8-registry-v1"
DATA_REVISION: Final[str] = "case8-corrected-j2b-v1"

_MASK_REF: Final[str] = "mask.case8.native-face-shock-window"


def _dimensionless_unit(spec: dict) -> dict:
    return dict(spec)


def protocol_spec() -> dict:
    return {
        "method_name": known(C.METHOD_NAME),
        "method_hash": known(C.METHOD_SHA256),
        "grid": known({
            "coordinate_system": "CARTESIAN",
            "dimensions": [{"axis": "y", "size": C.GRID_NY}, {"axis": "x", "size": C.GRID_NX}],
            "extent": [
                {"axis": "x", "lower": C.DOMAIN_X[0], "upper": C.DOMAIN_X[1]},
                {"axis": "y", "lower": C.DOMAIN_Y[0], "upper": C.DOMAIN_Y[1]},
            ],
        }),
        "integrator": known("SSP-RK3"),
        "reconstruction": known("first-order / none"),
        "final_time": known(C.FINAL_TIME),
        "boundary_scope": known("x_lower pre-shock inflow; x_upper outflow; y periodic"),
        "protocol_asset_refs": [C.ASSET_ID_METHOD],
    }


def config(config_id: str) -> dict:
    if config_id not in C.CONFIG_ORDER:
        raise KeyError(config_id)
    dim = _dimensionless_unit(SEM.UNIT_DIMENSIONLESS)
    return {
        "id": config_id,
        "experiment_id": EXPERIMENT_ID,
        "name": f"Case8 {config_id}",
        "parameters": [
            {"name": "q_aa", "value": known(C.CONFIG_QAA[config_id]), "unit": dict(dim)},
            {"name": "q_at", "value": known(C.CONFIG_QAT[config_id]), "unit": dict(dim)},
            {"name": "CFL", "value": known(C.CFL), "unit": dict(SEM.UNIT_CFL)},
            {"name": "gate", "value": known("Acoustic"), "unit": dict(SEM.UNIT_CATEGORICAL)},
        ],
        "protocol": protocol_spec(),
        "verification": {
            "status": "VERIFIED_NOT_FROZEN",
            "basis": ["J2B physical_reproduction BITWISE at 1912 accepted steps, T=0.08"],
            "verified_at": unresolved("No bound per-configuration verification event"),
            "observation_at": unresolved("Runtime observation not performed"),
            "evidence_refs": [C.ASSET_ID_METHOD],
        },
        "limitations": [],
        "evidence_refs": [C.ASSET_ID_METHOD],
    }


def config_ids() -> tuple[str, ...]:
    return C.CONFIG_ORDER


def snapshot_schedule(config_id: str) -> tuple[dict, ...]:
    """The six real recorded snapshots. snapshot_index is 1-based; step 0 is index 1."""
    if config_id not in C.CONFIG_ORDER:
        raise KeyError(config_id)
    out = []
    for i, source_step in enumerate(C.SNAPSHOT_SOURCE_STEPS, start=1):
        out.append({"snapshot_index": i, "source_step_index": source_step})
    return tuple(out)


def allocation_capability() -> dict:
    config_support = []
    for cid in C.CONFIG_ORDER:
        if cid == "D_u":
            config_support.append({
                "config_id": cid, "status": "SUPPORTED",
                "reason": "Existing frozen diagnostic rerun",
                "result_refs": ["case8.D_u.allocation"],
            })
        else:
            config_support.append({
                "config_id": cid, "status": "MISSING",
                "reason": "No saved cumulative native-face map; scalar zero-channel does not create a spatial asset",
                "result_refs": [],
            })
    return {
        "id": "case8.allocation",
        "experiment_id": EXPERIMENT_ID,
        "task": "trajectory-integrated native-face allocation",
        "status": "PARTIAL",
        "available_for_configs": ["D_u"],
        "config_support": config_support,
        "controls": [{
            "name": "config", "kind": "ENUM",
            "allowed_values": list(C.CONFIG_ORDER),
            "combination_registry_ref": known("case8.configs"),
        }],
        "tab_policy": {
            "tab_id": "allocation", "visible_for_family": True,
            "disabled_for_configs": ["A_u", "B_u", "C_u"],
            "unsupported_deep_link_behavior": "EXPLAIN",
        },
        "result_refs": ["case8.D_u.allocation"],
        "limitations": [{
            "id": "lim.case8.allocation-configs",
            "code": "D_U_ONLY_DIAGNOSTIC_RERUN",
            "description": "Only D_u has saved cumulative native-face maps",
            "affected_refs": ["case8.allocation"], "severity": "WARNING",
        }],
        "evidence_refs": ["ev.case8.D_u.allocation"],
    }


def snapshot_capability() -> dict:
    config_support = [{
        "config_id": cid, "status": "SUPPORTED",
        "reason": "Six real recorded snapshots; density/pressure/front stored",
        "result_refs": [f"case8.{cid}.snapshot.{i}" for i in range(1, 7)],
    } for cid in C.CONFIG_ORDER]
    return {
        "id": "case8.flow-snapshots",
        "experiment_id": EXPERIMENT_ID,
        "task": "recorded instantaneous flow snapshots",
        "status": "SUPPORTED",
        "available_for_configs": list(C.CONFIG_ORDER),
        "config_support": config_support,
        "controls": [{
            "name": "config", "kind": "ENUM", "allowed_values": list(C.CONFIG_ORDER),
            "combination_registry_ref": known("case8.configs"),
        }],
        "tab_policy": {
            "tab_id": "flow", "visible_for_family": True,
            "disabled_for_configs": [], "unsupported_deep_link_behavior": "EXPLAIN",
        },
        "result_refs": [f"case8.{cid}.snapshot.{i}" for cid in C.CONFIG_ORDER for i in range(1, 7)],
        "limitations": [{
            "id": "lim.case8.dense-fields", "code": "DISCRETE_RECORDED_ONLY",
            "description": "No per-step full state or all-stage spatial fields",
            "affected_refs": ["case8"], "severity": "WARNING",
        }],
        "evidence_refs": [EV.checkpoint_asset_id(c, s) for c in C.CONFIG_ORDER for s in C.SNAPSHOT_SOURCE_STEPS],
    }


def entropy_capability() -> dict:
    config_support = [{
        "config_id": cid, "status": "SUPPORTED",
        "reason": "1912 accepted-step records with cumulative and step-increment entropy",
        "result_refs": [f"case8.{cid}.entropy"],
    } for cid in C.CONFIG_ORDER]
    return {
        "id": "case8.entropy-history",
        "experiment_id": EXPERIMENT_ID,
        "task": "accepted-step entropy history",
        "status": "SUPPORTED",
        "available_for_configs": list(C.CONFIG_ORDER),
        "config_support": config_support,
        "controls": [{
            "name": "config", "kind": "ENUM", "allowed_values": list(C.CONFIG_ORDER),
            "combination_registry_ref": known("case8.configs"),
        }],
        "tab_policy": {
            "tab_id": "entropy", "visible_for_family": True,
            "disabled_for_configs": [], "unsupported_deep_link_behavior": "EXPLAIN",
        },
        "result_refs": [f"case8.{cid}.entropy" for cid in C.CONFIG_ORDER],
        "limitations": [],
        "evidence_refs": [C.ASSET_ID_HISTORY_TEMPLATE.format(config=c) for c in C.CONFIG_ORDER],
    }


def capabilities() -> list[dict]:
    return [snapshot_capability(), entropy_capability(), allocation_capability()]


def allocation_registry() -> dict:
    """D_u allocation entry: metadata present, values IMPLEMENTATION_DEFERRED.

    A/B/C explicitly never create a zero cumulative map.
    """
    meta = EV.allocation_registry_metadata()
    return {
        "result_id": meta["result_id"],
        "semantic_id": meta["semantic_id"],
        "representation_type": meta["representation_type"],
        "config_id": "D_u",
        "experiment_id": EXPERIMENT_ID,
        "implementation_status": "IMPLEMENTATION_DEFERRED",
        "source_asset": EV.allocation_registry_metadata(),
        "excluded_configs": {
            "A_u": "MISSING", "B_u": "MISSING", "C_u": "MISSING",
        },
    }


def registry_document() -> dict:
    """Complete registry view (metadata only)."""
    return {
        "experiment_id": EXPERIMENT_ID,
        "registry_revision": REGISTRY_REVISION,
        "data_revision": DATA_REVISION,
        "method": {"name": C.METHOD_NAME, "sha256": C.METHOD_SHA256},
        "configs": [config(c) for c in C.CONFIG_ORDER],
        "capabilities": capabilities(),
        "snapshot_schedule": {c: [dict(x) for x in snapshot_schedule(c)] for c in C.CONFIG_ORDER},
        "history_series": SEM.HISTORY_SERIES,
        "stored_flow_fields": SEM.STORED_FLOW_FIELDS,
        "definitions": SEM.DEFINITIONS,
        "allocation": allocation_registry(),
    }
