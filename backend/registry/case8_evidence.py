"""Case8 evidence descriptors.

Builds real ``SourceAsset`` / ``Verification`` descriptors for checkpoints,
entropy histories and metrics. Recorded hashes are the true SHA-256 of the
scientific files. ``VERIFIED_NOT_FROZEN`` is never promoted to
``FROZEN_VERIFIED`` for per-checkpoint assets that have no upstream per-file
freeze record.
"""
from __future__ import annotations

from typing import Final

from backend.models.core import known, unresolved
from backend.registry import case8_source_constants as C

# Evidence groups (per asset class), with honest verification scope.
_CHECKPOINT_VERIFICATION: Final[dict] = {
    "status": "VERIFIED_NOT_FROZEN",
    "basis": [
        "Phase1 finite fields, actual checkpoint schedule and bitwise terminal comparison",
        "No upstream per-checkpoint freeze record",
    ],
    "verified_at": unresolved("No bound per-checkpoint verification event"),
    "observation_at": unresolved("Runtime observation not performed"),
    "evidence_refs": [],
}
_HISTORY_VERIFICATION: Final[dict] = {
    "status": "VERIFIED_NOT_FROZEN",
    "basis": [
        "J2B stage-weighted history; channel additivity PASS and terminal reproduction BITWISE",
        "Recorded SHA-256 match observed read-only",
    ],
    "verified_at": unresolved("No bound per-history verification timestamp"),
    "observation_at": unresolved("Runtime observation not performed"),
    "evidence_refs": [],
}
_METHOD_VERIFICATION: Final[dict] = {
    "status": "FROZEN_VERIFIED",
    "basis": ["Protocol lock asset recorded hash match; does not certify every checkpoint"],
    "verified_at": unresolved("No bound per-configuration verification event"),
    "observation_at": unresolved("Runtime observation not performed"),
    "evidence_refs": [],
}

_CHECKPOINT_LIMITATIONS: Final[list[dict]] = [{
    "id": "lim.checkpoint.freeze",
    "code": "NO_UPSTREAM_CHECKPOINT_HASH",
    "description": "Phase1 verified finite fields and schedule; no upstream per-checkpoint freeze record",
    "affected_refs": [],
    "severity": "INFO",
}]

_UNIT_UNKNOWN_LIMITATION: Final[dict] = {
    "id": "lim.model-units",
    "code": "SI_MAPPING_UNKNOWN",
    "description": "Model quantities have no confirmed SI mapping",
    "affected_refs": [],
    "severity": "INFO",
}


def checkpoint_asset_id(config_id: str, source_step: int) -> str:
    return C.ASSET_ID_CHECKPOINT_TEMPLATE.format(config=config_id, step=source_step)


def checkpoint_source_asset(config_id: str, source_step: int) -> dict:
    """Real SourceAsset descriptor; recorded hash is the verified file SHA-256."""
    recorded = C.CHECKPOINT_SHA256.get(config_id, {}).get(source_step)
    rel = f"corrected_physics_reproduction_v1/case8/{_dir_name(config_id)}/checkpoints/step_{source_step:06d}.npz"
    return {
        "asset_id": checkpoint_asset_id(config_id, source_step),
        "source_id": "scientific-root-v1",
        "source_display": f"Case8 {config_id} checkpoint step_{source_step:06d}.npz",
        "relative_origin": known(rel),
        "role": "DATA",
        "format": "NPZ",
        "recorded_data_hash": known(recorded) if recorded else unresolved("Recorded hash not bound in registry"),
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Observe source dependencies before asserting false"),
        "verification": dict(_CHECKPOINT_VERIFICATION),
        "canonical_selected": True,
        "limitations": [dict(_CHECKPOINT_LIMITATIONS[0])],
    }


def history_source_asset(config_id: str) -> dict:
    rel = f"jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_{config_id}/stage_weighted_history.csv"
    return {
        "asset_id": C.ASSET_ID_HISTORY_TEMPLATE.format(config=config_id),
        "source_id": "scientific-root-v1",
        "source_display": f"Case8 {config_id} stage_weighted_history.csv (1912 rows)",
        "relative_origin": known(rel),
        "role": "DATA",
        "format": "CSV",
        "recorded_data_hash": known(C.HISTORY_SHA256[config_id]),
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Observe source dependencies before asserting false"),
        "verification": dict(_HISTORY_VERIFICATION),
        "canonical_selected": True,
        "limitations": [],
    }


def method_source_asset() -> dict:
    rel = "jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json"
    return {
        "asset_id": C.ASSET_ID_METHOD,
        "source_id": "scientific-root-v1",
        "source_display": "J2B protocol lock / cross_mode_ec_unified_v1 method identity",
        "relative_origin": known(rel),
        "role": "METHOD",
        "format": "JSON",
        "recorded_data_hash": known(C.METHOD_SHA256),
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Observe source dependencies before asserting false"),
        "verification": dict(_METHOD_VERIFICATION),
        "canonical_selected": True,
        "limitations": [],
    }


def allocation_registry_metadata() -> dict:
    """D_u native-face allocation: registry metadata only (values deferred).

    The cumulative native-face allocation map is the first object a larger
    surface will consume; this window records identity/provenance so downstream
    integration can bind it without the adapter loading values now.
    """
    return {
        "result_id": "case8.D_u.allocation",
        "asset_id": C.ASSET_ID_ALLOCATION_D_U,
        "semantic_id": "Case8_face_Pi_at_integrated",
        "representation_type": "FACE_FIELD",
        "source_display": "Case8 D_u native_faces_step_001912.npz",
        "relative_origin": known(
            "jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u/snapshots/native_faces_step_001912.npz"
        ),
        "face_members": ["x_pi_bg", "x_pi_aa", "x_pi_at", "y_pi_bg", "y_pi_aa", "y_pi_at"],
        "x_face_shape": [32, 129],
        "y_face_shape": [32, 128],
        "measure": "dy*sum(x-faces) + dx*sum(y-faces) = E_at",
        "implementation_status": "IMPLEMENTATION_DEFERRED",
        "deferred_reason": "Value loading is not required for the minimal Case8 DoD",
    }


def _dir_name(config_id: str) -> str:
    return {
        "A_u": "03_case8_A_u",
        "B_u": "04_case8_B_u",
        "C_u": "06_case8_C_u",
        "D_u": "05_case8_D_u",
    }[config_id]
