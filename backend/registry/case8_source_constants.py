"""Real, hash-verified Case8 source locations and recorded hashes.

All values in this module are transcribed from the read-only scientific root
``D:\\Paper\\passage6`` and its Phase-1 asset inventory. Nothing here is
interpolated, rounded, or synthesised. The adapter never writes to the source.
"""
from __future__ import annotations

from typing import Final

SCIENTIFIC_ROOT_WINDOWS: Final[str] = r"D:\Paper\passage6"

# --- Case8 corrected production checkpoints (snapshot assets) ---------------
# relative to SCIENTIFIC_ROOT_WINDOWS
CHECKPOINT_DIRS: Final[dict[str, str]] = {
    "A_u": r"corrected_physics_reproduction_v1\case8\03_case8_A_u\checkpoints",
    "B_u": r"corrected_physics_reproduction_v1\case8\04_case8_B_u\checkpoints",
    "C_u": r"corrected_physics_reproduction_v1\case8\06_case8_C_u\checkpoints",
    "D_u": r"corrected_physics_reproduction_v1\case8\05_case8_D_u\checkpoints",
}

# Recorded snapshot schedule: USER_VISIBLE_1_BASED_RECORDED_INDEX -> source file
SNAPSHOT_SOURCE_STEPS: Final[tuple[int, ...]] = (0, 382, 765, 1147, 1530, 1912)

# --- J2B formal entropy-diagnostics run root (1912-row histories) ----------
J2B_RUN_ROOT_REL: Final[str] = r"jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\runs"

HISTORY_REL_TEMPLATE: Final[str] = r"case8_{config}\stage_weighted_history.csv"

# --- Method identity -------------------------------------------------------
METHOD_NAME: Final[str] = "cross_mode_ec_unified_v1"
METHOD_SHA256: Final[str] = "98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0"

# --- Recorded geometry / protocol (J2B_PROTOCOL_LOCK.json) ------------------
GRID_NX: Final[int] = 128
GRID_NY: Final[int] = 32
DOMAIN_X: Final[tuple[float, float]] = (0.0, 1.0)
DOMAIN_Y: Final[tuple[float, float]] = (0.0, 1.0)
FINAL_TIME: Final[float] = 0.08
ACCEPTED_STEPS: Final[int] = 1912
CFL: Final[float] = 0.05
DT: Final[float] = 4.184100418410042e-05
GAS_GAMMA: Final[float] = 1.4
FRONT_WINDOW_HALF_WIDTH: Final[float] = 0.08

CONFIG_ORDER: Final[tuple[str, ...]] = ("A_u", "B_u", "C_u", "D_u")
CONFIG_QAA: Final[dict[str, float]] = {"A_u": 13.2, "B_u": 3.96, "C_u": 13.2, "D_u": 3.96}
CONFIG_QAT: Final[dict[str, float]] = {"A_u": 0.0, "B_u": 0.0, "C_u": 0.396, "D_u": 0.396}

# --- Recorded per-file SHA-256 (source of truth for drift detection) -------
HISTORY_SHA256: Final[dict[str, str]] = {
    "A_u": "f0eb1003e3842f03610af5f8b86f51010940df095cbbdee06f0609717746ca7d",
    "B_u": "f145079e96569d836b0b17c6f5b6bddec2a7528a6cc1596b66daae15561d6924",
    "C_u": "c39fd65dfe4b6d0f6cc9019da9c46495fc0b87e75cf821de9087e007eafc4770",
    "D_u": "a4fe0ec332b623df3ed7001fd9839ba7ad8c474924588dae419f4e8741db1ea9",
}

CHECKPOINT_SHA256: Final[dict[str, dict[int, str]]] = {
    # D_u terminal checkpoint recorded hash (Phase-1 asset_f4323c28384b).
    "D_u": {1912: "3ab44eb9febe7fbe5d8f76e00ef0b31afd4b01bceb2676ed609f4f9860d62093"},
}

# --- Phase-1 canonical asset identities ------------------------------------
ASSET_ID_CHECKPOINT_TEMPLATE: Final[str] = "asset.case8.{config}.step{step}"
ASSET_ID_HISTORY_TEMPLATE: Final[str] = "asset.case8.{config}.entropy-history"
ASSET_ID_ALLOCATION_D_U: Final[str] = "asset.case8.D_u.native-face-allocation"
ASSET_ID_METHOD: Final[str] = "asset_8d15c3f16f95"

HISTORY_COLUMNS: Final[tuple[str, ...]] = (
    "E_aa", "E_at", "E_bg", "E_total", "I_J_domain", "I_J_front",
    "I_pi_at_domain", "I_pi_at_front", "I_pt_z_norm2_domain", "I_pt_z_norm2_front",
    "J_max_s0", "J_max_s1", "J_max_s2", "config",
    "deltaE_aa", "deltaE_at", "deltaE_bg", "deltaE_total",
    "delta_J_domain", "delta_J_front", "delta_pi_at_domain", "delta_pi_at_front",
    "delta_pt_z_norm2_domain", "delta_pt_z_norm2_front",
    "dotE_aa_s0", "dotE_aa_s1", "dotE_aa_s2",
    "dotE_additivity_abs_error_s0", "dotE_additivity_abs_error_s1", "dotE_additivity_abs_error_s2",
    "dotE_additivity_rel_error_s0", "dotE_additivity_rel_error_s1", "dotE_additivity_rel_error_s2",
    "dotE_at_s0", "dotE_at_s1", "dotE_at_s2",
    "dotE_bg_s0", "dotE_bg_s1", "dotE_bg_s2",
    "dotE_total_s0", "dotE_total_s1", "dotE_total_s2",
    "dt", "pi_at_max_s0", "pi_at_max_s1", "pi_at_max_s2",
    "pt_z_norm2_max_s0", "pt_z_norm2_max_s1", "pt_z_norm2_max_s2",
    "run_id", "step", "time_end", "time_start",
)
