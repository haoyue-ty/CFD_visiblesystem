"""Gate evidence descriptors: real SourceAsset / Verification for the three gates.

Recorded hashes are the true SHA-256 of the frozen files. Like the Case8 evidence
module this never loads a scientific array; it only builds the honest evidence
descriptors an allocation report needs. ``FROZEN_VERIFIED`` is asserted only
where the freeze package actually recorded the hash.
"""
from __future__ import annotations

from typing import Final

from backend.models.core import known, unresolved
from backend.registry import gate_registry as G

# The three-gate freeze is a completed experiment-1 certificate with recorded
# per-file SHA-256, so per-asset verification is FROZEN_VERIFIED.
_FROZEN_VERIFICATION: Final[dict] = {
    "status": "FROZEN_VERIFIED",
    "basis": [
        "PASSAGE6 Experiment 1 freeze: source-to-snapshot SHA256 equality 17/17 PASS",
        "Pi_at integral consistency abs(sum(E_at_array) - entropy.E_at) < 1e-10",
    ],
    "verified_at": unresolved("No bound per-asset verification timestamp"),
    "observation_at": unresolved("Runtime observation not performed"),
    "evidence_refs": [],
}

_CELL_DEFINITION_LIMITATION: Final[dict] = {
    "id": "lim.gate.cell-window",
    "code": "CELL_CENTER_NOT_NATIVE_FACE",
    "description": (
        "Saved cell-map front window uses a cell-center classification and is not "
        "numerically identical to the J2 native-face localization"
    ),
    "affected_refs": [],
    "severity": "INFO",
}


def pi_at_source_asset(config_id: str) -> dict:
    """Real SourceAsset descriptor for the saved cumulative cell allocation."""
    return {
        "asset_id": G.pi_at_asset_id(config_id),
        "source_id": "scientific-root-v1",
        "source_display": f"Gate {config_id} Pi_at.npy (32x128 cumulative cell allocation)",
        "relative_origin": known(G.pi_at_relative_origin(config_id)),
        "role": "DATA",
        "format": "NPY",
        "recorded_data_hash": known(G.PI_AT_SHA256[config_id]),
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Observe source dependencies before asserting false"),
        "verification": dict(_FROZEN_VERIFICATION),
        "canonical_selected": True,
        "limitations": [dict(_CELL_DEFINITION_LIMITATION)],
    }


def entropy_source_asset(config_id: str) -> dict:
    return {
        "asset_id": G.entropy_asset_id(config_id),
        "source_id": "scientific-root-v1",
        "source_display": f"Gate {config_id} entropy.csv (E_bg/E_aa/E_at/E_total/f_at)",
        "relative_origin": known(G.entropy_relative_origin(config_id)),
        "role": "DATA",
        "format": "CSV",
        "recorded_data_hash": known(G.ENTROPY_SHA256[config_id]),
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Observe source dependencies before asserting false"),
        "verification": dict(_FROZEN_VERIFICATION),
        "canonical_selected": True,
        "limitations": [],
    }


def matched_qat_source_asset() -> dict:
    return {
        "asset_id": G.ASSET_ID_MATCHED_QAT,
        "source_id": "scientific-root-v1",
        "source_display": "Gate matched q_at calibration snapshot",
        "relative_origin": known(G.matched_qat_relative_origin()),
        "role": "CONFIG",
        "format": "JSON",
        "recorded_data_hash": known(G.MATCHED_QAT_SHA256),
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Observe source dependencies before asserting false"),
        "verification": dict(_FROZEN_VERIFICATION),
        "canonical_selected": True,
        "limitations": [],
    }


def analysis_source_asset() -> dict:
    return {
        "asset_id": G.ASSET_ID_ANALYSIS_CSV,
        "source_id": "scientific-root-v1",
        "source_display": "Gate ablation analysis CSV (budgets and window fractions)",
        "relative_origin": known(G.analysis_csv_relative_origin()),
        "role": "ANALYSIS",
        "format": "CSV",
        "recorded_data_hash": known(G.ANALYSIS_CSV_SHA256),
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Observe source dependencies before asserting false"),
        "verification": dict(_FROZEN_VERIFICATION),
        "canonical_selected": True,
        "limitations": [],
    }


def readme_source_asset() -> dict:
    return {
        "asset_id": G.ASSET_ID_README,
        "source_id": "scientific-root-v1",
        "source_display": "Gate ablation README (measure and window definition)",
        "relative_origin": known(G.readme_relative_origin()),
        "role": "METHOD",
        "format": "Markdown",
        "recorded_data_hash": known(G.README_SHA256),
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Observe source dependencies before asserting false"),
        "verification": dict(_FROZEN_VERIFICATION),
        "canonical_selected": True,
        "limitations": [],
    }
