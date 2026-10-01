"""Gate experiment registry: the three frozen matched gate variants.

Pure metadata transcribed from the read-only PASSAGE6 Experiment 1 freeze
``D:\\Paper\\passage6\\experiments\\gate_ablation\\FREEZE`` and its checksums.
Like the Case8 registry this module never loads a scientific array; it supplies
the stable identities the adapter uses to locate and read real files.

Only three gates exist: ``Acoustic``, ``Pressure``, ``Ungated``. There is no
fourth gate, no arbitrary ``q_at``, and no interpolation between matched values.
"""
from __future__ import annotations

from typing import Final

from backend.models.core import known, unresolved

EXPERIMENT_ID: Final[str] = "gate"
REGISTRY_REVISION: Final[str] = "gate-registry-v1"
DATA_REVISION: Final[str] = "gate-ablation-frozen-v1"

# Read-only scientific root and the frozen experiment-1 package.
SCIENTIFIC_ROOT_WINDOWS: Final[str] = r"D:\Paper\passage6"
GATE_FREEZE_REL: Final[str] = "experiments/gate_ablation/FREEZE"

# --- The three gate identities (frozen order: Acoustic, Pressure, Ungated) --
GATE_ID: Final[str] = "gate"
CONFIG_ORDER: Final[tuple[str, ...]] = ("Acoustic", "Pressure", "Ungated")

# Matched q_at captured from calibration_snapshot/matched_qat.json. These are
# exact matched values, never a slider value and never an interpolated value.
MATCHED_QAT: Final[dict[str, float]] = {
    "Acoustic": 0.4,
    "Pressure": 0.31018332312583474,
    "Ungated": 0.03483470441226932,
}

# Gate form label, from MANIFEST.md (J_acoustic / |p_R-p_L|/(p_R+p_L) / C=1).
GATE_FORM: Final[dict[str, str]] = {
    "Acoustic": "J_acoustic",
    "Pressure": "abs(p_R-p_L)/(p_R+p_L+1e-14)",
    "Ungated": "C=1",
}

# --- Frozen geometry / protocol (shared Case8 protocol) --------------------
GRID_NX: Final[int] = 128
GRID_NY: Final[int] = 32
CELL_SHAPE: Final[tuple[int, int]] = (32, 128)
DOMAIN_X: Final[tuple[float, float]] = (0.0, 1.0)
DOMAIN_Y: Final[tuple[float, float]] = (0.0, 1.0)
FINAL_TIME: Final[float] = 0.08
ACCEPTED_STEPS: Final[int] = 1912
CFL: Final[float] = 0.05
DT: Final[float] = 4.184100418410042e-05
Q_AA: Final[float] = 3.96
FRONT_WINDOW_HALF_WIDTH: Final[float] = 0.08
FRONT_X0: Final[float] = 0.5
FRONT_AMPLITUDE: Final[float] = 0.0125
FRONT_WAVENUMBER: Final[float] = 8.0

# Frozen cell-map integral-consistency threshold (README: <1e-10).
INTEGRAL_ABS_THRESHOLD: Final[float] = 1e-10

# --- Per-gate relative origins (relative to SCIENTIFIC_ROOT_WINDOWS) --------
_ASSET_ID_PI_AT: Final[dict[str, str]] = {
    "Acoustic": "asset_a11ef6fc4e6e",
    "Pressure": "asset_6850b4bab5cc",
    "Ungated": "asset_4dce11517608",
}
_ASSET_ID_ENTROPY: Final[dict[str, str]] = {
    "Acoustic": "asset_ae5b2b6cb267",
    "Pressure": "asset_0923c6c4651e",
    "Ungated": "asset_03954c7706b9",
}

# Recorded SHA-256 for the three cell-allocation assets (checksums.txt).
PI_AT_SHA256: Final[dict[str, str]] = {
    "Acoustic": "35adfd76a205fdd811f03aac557b4dcb5e7603d29a6bed2d2ba4a302c580f874",
    "Pressure": "17754e75e9d207541ecb70a3619e994d27affc203781431eec2c3ed79c700d22",
    "Ungated": "7d89e836f2fb2b4990442d50765c2878a07a2946f5c997bba92338a19b6dddec",
}
ENTROPY_SHA256: Final[dict[str, str]] = {
    "Acoustic": "828aab3b457192d2f1d6298641589945b348dab0204b366de91505b7ce5a4fb2",
    "Pressure": "4ea3ad89034f56c54d63122dec7091ff4705c81ffb455290d4c6666e7b49723e",
    "Ungated": "4180999af27d5ac405bb3a628b6bf9c8d899cc91cba6e9c532fd1defecf9b5af",
}

# Frozen supporting assets referenced by an allocation / its evidence.
ASSET_ID_ENTROPY_TEMPLATE: Final[str] = "asset.gate.{gate}.entropy-summary"
ASSET_ID_MATCHED_QAT: Final[str] = "asset_aef55f8d1d5a"          # matched_qat.json
ASSET_ID_ANALYSIS_CSV: Final[str] = "asset_513157e8d9c4"          # gate_ablation_analysis.csv
ASSET_ID_README: Final[str] = "asset_846c9246cf3b"               # README.md
MATCHED_QAT_SHA256: Final[str] = "5b6d50aa67378958419bdbdea243f4a9d46a89eca67a8e343159ff068654fa07"
ANALYSIS_CSV_SHA256: Final[str] = "ca9aada125ffbd198dc562b834574720fe8f4e862cc48ca9b9b8739fd97fc25b"
README_SHA256: Final[str] = "153f3a52efe04a633804ef3f70ccd4d5f6bc471154e5be87783c43229bbda776"

METHOD_NAME: Final[str] = "cross_mode_ec_unified_v1"
METHOD_SHA256: Final[str] = "98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0"

# Frozen mask identity (05 §8.1): Gate cell shock window, distinct from the
# Case8 native-face mask.
MASK_ID: Final[str] = "mask.gate.cell-window"
MASK_DEFINITION: Final[str] = (
    "Fixed cell-center shock window abs(x_i-x_s(y_j))<=0.08 with the prescribed "
    "front x_s(y)=0.5+0.0125 sin(8 pi y); cell-center classification, not native-face"
)
MEASURE_ID: Final[str] = "gate.integrated-cell-sum"
SEMANTIC_ID: Final[str] = "Gate_cell_Pi_at_integrated"

# --- Frozen summary values (transcribed from gate_ablation_analysis.csv) ----
# E_at is the authoritative cell budget; R_front / outside are the saved fixed
# window fractions. Values are never re-normalised or re-derived by an adapter.
FROZEN_SUMMARY: Final[dict[str, dict[str, float]]] = {
    "Acoustic": {
        "E_at": 0.0028004425253788713,
        "E_total": 2.016657946919806,
        "f_at": 0.0013886551904631118,
        "inside_fraction": 0.9983067757919961,
        "outside_fraction": 0.0016932242080059982,
    },
    "Pressure": {
        "E_at": 0.0028430539591530325,
        "E_total": 2.0166591670473593,
        "f_at": 0.001409784065452973,
        "inside_fraction": 0.9916868280217838,
        "outside_fraction": 0.008313171978215123,
    },
    "Ungated": {
        "E_at": 0.0028272752981764065,
        "E_total": 2.0170469005767218,
        "f_at": 0.0014016904105541726,
        "inside_fraction": 0.8923001329707689,
        "outside_fraction": 0.10769986702923035,
    },
}


def pi_at_relative_origin(config_id: str) -> str:
    if config_id not in CONFIG_ORDER:
        raise KeyError(config_id)
    return f"{GATE_FREEZE_REL}/results_snapshot/{config_id}/Pi_at.npy"


def entropy_relative_origin(config_id: str) -> str:
    if config_id not in CONFIG_ORDER:
        raise KeyError(config_id)
    return f"{GATE_FREEZE_REL}/results_snapshot/{config_id}/entropy.csv"


def matched_qat_relative_origin() -> str:
    return f"{GATE_FREEZE_REL}/calibration_snapshot/matched_qat.json"


def analysis_csv_relative_origin() -> str:
    return f"{GATE_FREEZE_REL}/gate_ablation_analysis.csv"


def readme_relative_origin() -> str:
    return f"{GATE_FREEZE_REL}/README.md"


def pi_at_asset_id(config_id: str) -> str:
    if config_id not in CONFIG_ORDER:
        raise KeyError(config_id)
    return _ASSET_ID_PI_AT[config_id]


def entropy_asset_id(config_id: str) -> str:
    if config_id not in CONFIG_ORDER:
        raise KeyError(config_id)
    return _ASSET_ID_ENTROPY[config_id]


def gate_ids() -> tuple[str, ...]:
    return CONFIG_ORDER


def _unit_model_entropy() -> dict:
    return {
        "id": "model_integrated_entropy", "system": "MODEL",
        "quantity": "integrated entropy", "label": "model integrated entropy",
        "si_mapping": unresolved("No established SI mapping"),
    }


def _unit_fraction() -> dict:
    return {
        "id": "dimensionless_fraction", "system": "DIMENSIONLESS",
        "quantity": "fraction", "label": "dimensionless fraction",
        "si_mapping": unresolved("Dimensionless quantity", "NOT_APPLICABLE"),
    }


def config(config_id: str) -> dict:
    """Frozen ExperimentConfig for one gate (metadata only)."""
    if config_id not in CONFIG_ORDER:
        raise KeyError(config_id)
    return {
        "id": config_id,
        "experiment_id": EXPERIMENT_ID,
        "name": f"Gate {config_id}",
        "parameters": [
            {"name": "q_at", "value": known(MATCHED_QAT[config_id]), "unit": _unit_model_entropy()},
            {"name": "q_aa", "value": known(Q_AA), "unit": _unit_model_entropy()},
            {"name": "CFL", "value": known(CFL), "unit": {
                "id": "dimensionless_cfl", "system": "DIMENSIONLESS", "quantity": "CFL",
                "label": "dimensionless", "si_mapping": unresolved("Dimensionless ratio", "NOT_APPLICABLE")}},
            {"name": "gate", "value": known(config_id), "unit": {
                "id": "categorical", "system": "UNKNOWN", "quantity": "gate category",
                "label": "category", "si_mapping": unresolved("Categorical parameter", "NOT_APPLICABLE")}},
        ],
        "protocol": {
            "method_name": known(METHOD_NAME),
            "method_hash": known(METHOD_SHA256),
            "grid": known({
                "coordinate_system": "CARTESIAN",
                "dimensions": [{"axis": "y", "size": GRID_NY}, {"axis": "x", "size": GRID_NX}],
                "extent": [
                    {"axis": "x", "lower": DOMAIN_X[0], "upper": DOMAIN_X[1]},
                    {"axis": "y", "lower": DOMAIN_Y[0], "upper": DOMAIN_Y[1]},
                ],
            }),
            "integrator": known("SSP-RK3"),
            "reconstruction": known("first-order / none"),
            "final_time": known(FINAL_TIME),
            "boundary_scope": known("x_lower pre-shock inflow; x_upper outflow; y periodic"),
            "protocol_asset_refs": [ASSET_ID_README],
        },
        "verification": {
            "status": "FROZEN_VERIFIED",
            "basis": [
                "PASSAGE6 Experiment 1 freeze: source-to-snapshot SHA256 17/17 PASS",
                "Pi_at integral consistency abs(sum - E_at) < 1e-10 for all three gates",
            ],
            "verified_at": unresolved("No bound per-configuration verification event"),
            "observation_at": unresolved("Runtime observation not performed"),
            "evidence_refs": [ASSET_ID_README, ASSET_ID_ANALYSIS_CSV],
        },
        "limitations": [],
        "evidence_refs": [pi_at_asset_id(config_id), ASSET_ID_ANALYSIS_CSV],
    }


def configs() -> list[dict]:
    return [config(c) for c in CONFIG_ORDER]


def gate_registry() -> dict:
    """GateRegistry metadata (05 §9): experiment, configs, map shape, comparison."""
    return {
        "experiment_id": EXPERIMENT_ID,
        "configs": configs(),
        "map_shape": list(CELL_SHAPE),
        "comparison_id": "gate.comparison",
        "evidence_refs": [ASSET_ID_ANALYSIS_CSV, ASSET_ID_README],
    }


def allocation_registry() -> dict:
    """Per-gate allocation registry entries: supported, values FROZEN_PRODUCTION."""
    return {c: {
        "result_id": f"gate.{c}.allocation",
        "semantic_id": SEMANTIC_ID,
        "representation_type": "CELL_FIELD",
        "config_id": c,
        "experiment_id": EXPERIMENT_ID,
        "map_shape": list(CELL_SHAPE),
        "source_asset": pi_at_asset_id(c),
        "implementation_status": "SUPPORTED",
    } for c in CONFIG_ORDER}


def registry_document() -> dict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "registry_revision": REGISTRY_REVISION,
        "data_revision": DATA_REVISION,
        "method": {"name": METHOD_NAME, "sha256": METHOD_SHA256},
        "gate_registry": gate_registry(),
        "allocation": allocation_registry(),
    }
