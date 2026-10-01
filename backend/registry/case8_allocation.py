"""Pinned bindings for the existing D_u frozen native-face diagnostic.

No scientific execution or array I/O. Baselines and inventory identities come
from Phase1 data_asset_inventory.json and the upstream FREEZE_MANIFEST.json.
The Phase5 instantaneous native-face snapshots are not this allocation.
"""
from backend.models import ExperimentCapability, ScientificDefinition, known, unresolved
from backend.registry import case8_registry as REG

RESULT_ID = "case8.D_u.allocation"
EVIDENCE_ID = "ev.case8.D_u.allocation"
MASK_ID = "mask.case8.native-face-shock-window"
REGISTRY_REVISION = "case8-du-allocation-registry-v1"
DATA_REVISION = "case8-du-spatial-rerun-freeze-v1"
FREEZE_DIR = "Paper/fig/fig_14/Du_spatial_rerun/FREEZE"
METHOD_HASH = "98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0"

# name: (Phase1 asset identity, SHA256, role, format, original status)
ASSETS = {
    "Pi_at_trajectory_integrated.npz": (
        "asset_1930484b4ef9", "a0796191d2d5600916d22ad01163433fe5a71ca7c0daef07054b638dae2f00a5", "DATA", "NPZ", "FROZEN_VERIFIED"),
    "shock_window_final_or_definition.npz": (
        "asset_d497d3895d92", "d00d48e06df45a2f27173082864c551bbedfeffa3ed7f5f8d0b807c3681a3237", "MASK", "NPZ", "FROZEN_VERIFIED"),
    "rerun_config.json": (
        "asset_ed2281aae6da", "c6f3af05f9d72bc70cc4d38f3acc94400cfcd148a616300b09e9fc0391dce9a9", "CONFIG", "JSON", "FROZEN_VERIFIED"),
    "rerun_metrics.json": (
        "asset_865d03d50449", "132e4632536ba2aa8882545623acb1c5f183e0d5ba2b450d251e3eafa395b8ba", "ANALYSIS", "JSON", "FROZEN_VERIFIED"),
    "verification_report.json": (
        "asset_0d36bf11a1df", "cb48c862ade8149b9c75537af84f6bbe4a819aed69ad904d2ff30018fc6fb0e7", "ANALYSIS", "JSON", "FROZEN_VERIFIED"),
    "rerun_provenance.md": (
        "asset_93d8de11883e", "d3b6c05904e97b29e4794057f4c6085b55d59e7777a9dc014718b836088f48e5", "ANALYSIS", "MD", "FROZEN_VERIFIED"),
    "du_spatial_rerun_observer.py": (
        "asset_cc11e0d0f524", "000590a06dcd6c744a638f8b0dafc6185e16cea601bc19d2c63acea6d8c573e0", "METHOD", "PY", "FROZEN_VERIFIED"),
    "FREEZE_MANIFEST.json": (
        "asset_da86831d7f2a", "65349698edfa4bbfc7937ea0217cd99cde0d036eded29f15856a60008c31b1ba", "FREEZE", "JSON", "AVAILABLE_UNVERIFIED"),
}
DATA_ASSET_ID = ASSETS["Pi_at_trajectory_integrated.npz"][0]
MASK_ASSET_ID = ASSETS["shock_window_final_or_definition.npz"][0]

COORDINATE_CONVENTION = (
    "Cartesian [y,x], C order on [0,1]^2; x-normal faces: x=i/128, "
    "y=(j+0.5)/32; y-normal faces: x=(i+0.5)/128, y=j/32. "
    "Saved x_face/x_cell/y_face are loaded verbatim; y_cell is not stored."
)
BOUNDARY = (
    "x_lower pre-shock inflow; x_upper outflow; x boundary faces retained; "
    "periodic y seam counted once; duplicate residual y slot excluded"
)
MASK_DEFINITION = (
    "Independent saved native x/y-face bool masks: "
    "abs(x - (0.5 + 0.0125*sin(8*pi*y))) <= 0.08; prescribed initial front, inclusive."
)
TIME_RULE = (
    "TERMINAL/TRAJECTORY_INTEGRATED [0,0.08], 1912 accepted steps; "
    "Pi_f=sum_n dt*(pi_f_stage0/6 + pi_f_stage1/6 + 2*pi_f_stage2/3); "
    "time/RK weights already included; no additional dt or RK weighting."
)
MEASURE = {
    "id": "case8.native-face-integrated-measure",
    "description": "Native face density integrated over time; spatial face length still required",
    "integral_rule": "dy*sum(pi_at_x_faces)+dx*sum(pi_at_y_faces)",
    "measure_parameters": [{"name": "dx", "value": known(1.0/128)},
                           {"name": "dy", "value": known(1.0/32)}],
    "includes_time_weights": True,
    "includes_spatial_measure": False,
}
FACE_UNIT = {
    "id": "model_face_time_integrated_entropy", "system": "MODEL",
    "quantity": "time-integrated native-face entropy density",
    "label": "model integrated entropy per model face length",
    "si_mapping": unresolved("No established SI mapping"),
}
LIMITATIONS = [
    {"id": "lim.case8.allocation.model-units", "code": "SI_MAPPING_UNKNOWN",
     "description": "Model quantities have no established SI mapping", "affected_refs": [RESULT_ID], "severity": "INFO"},
    {"id": "lim.case8.allocation.terminal-only", "code": "TERMINAL_INTEGRAL_ONLY",
     "description": "Frozen diagnostic rerun; no intermediate cumulative maps or new CFD verification",
     "affected_refs": [RESULT_ID], "severity": "INFO"},
]

# Only saved members are registered; the derived cell map is excluded.
ARRAYS = {
    "pi_at_x_faces": ("Pi_at_trajectory_integrated.npz", (32,129), "float64", ("y","x")),
    "pi_at_y_faces": ("Pi_at_trajectory_integrated.npz", (32,128), "float64", ("y","x")),
    "x_face": ("Pi_at_trajectory_integrated.npz", (129,), "float64", ("x",)),
    "x_cell": ("Pi_at_trajectory_integrated.npz", (128,), "float64", ("x",)),
    "y_face": ("Pi_at_trajectory_integrated.npz", (32,), "float64", ("y",)),
    "x_window_mask": ("shock_window_final_or_definition.npz", (32,129), "bool", ("y","x")),
    "y_window_mask": ("shock_window_final_or_definition.npz", (32,128), "bool", ("y","x")),
}
DOMAINS = {"pi_at_x_faces": "case8.native-x-faces", "pi_at_y_faces": "case8.native-y-faces"}


def array_result_id(array_id):
    return f"{RESULT_ID}.{array_id}"


def array_ref(array_id):
    from math import prod
    _, shape, dtype, axes = ARRAYS[array_id]
    return {"result_id": array_result_id(array_id), "descriptor": {
        "array_id": array_id, "dtype": dtype, "shape": list(shape), "axes": list(axes),
        "order": "C", "encoding": "FLAT_JSON", "element_count": prod(shape)}}


def definition():
    return ScientificDefinition.model_validate({
        "id": "Case8_face_Pi_at_integrated", "semantic_id": "Case8_face_Pi_at_integrated",
        "title": "D_u trajectory-integrated native-face Pi_at",
        "definition": "Saved time-integrated cross-mode entropy density on separate x/y normal faces",
        "time_rule": TIME_RULE, "spatial_rule": MEASURE["integral_rule"] + "; " + BOUNDARY,
        "unit": FACE_UNIT, "mask_refs": [MASK_ID],
        "detector": unresolved("Allocation is not a detector metric", "NOT_APPLICABLE"),
        "evidence_refs": [EVIDENCE_ID], "limitations": LIMITATIONS,
    })


def capability():
    return ExperimentCapability.model_validate(REG.allocation_capability())


def verification(observed_at):
    return {"status": "FROZEN_VERIFIED", "basis": [
        "Existing frozen diagnostic, upstream verification gates and manifest hashes retained",
        "Runtime SHA256 of selected data/config/mask/provenance/observer/manifest dependencies matched",
        "Read-only format mapping; no current-code CFD reproduction or re-certification"],
        "verified_at": unresolved("Upstream verification timestamp not recorded"),
        "observation_at": known(observed_at), "evidence_refs": [EVIDENCE_ID]}
