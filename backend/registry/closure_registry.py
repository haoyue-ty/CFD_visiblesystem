"""Explicit five-run selection and Window0-bound scientific semantics.

Source-map IDs are internal locators. Public SourceAssets retain Phase1 IDs.
Numeric histories and summaries are always read from the real frozen sources.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from backend.core.errors import system_error, unsupported_combination
from backend.models.core import known, unresolved

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "data/closure/source_manifest.json").read_text(encoding="utf-8"))
_map_bytes = (ROOT / "docs/handoffs/phase9/PHASE9_CLOSURE_SOURCE_MAP.json").read_bytes()
if hashlib.sha256(_map_bytes).hexdigest() != "fcc71bfa3cecb719b5d74943e639b836107af0e9837d7650dcee0f6088a9fc26":
    raise RuntimeError("Window0 closure source map drift")
SOURCE_MAP = json.loads(_map_bytes)
SCIENTIFIC_ROOT = "D:/Paper/passage6"
BASE = "experiments/entropy_budget_closure"
REGISTRY_REVISION = "closure-registry-v1"
DATA_REVISION = "closure-frozen-fcc71bfa3cec"
COMPARISON_ID = "entropy-closure.D_u.temporal-refinement"
REFINEMENT_EVIDENCE = "ev.entropy-closure.D_u.temporal-refinement"
RUN_IDS = ("D_u-cfl-0.2", "D_u-cfl-0.1", "D_u-cfl-0.05", "D_u-cfl-0.025", "B_u-cfl-0.05")
RUNS = {run["run_id"]: run for run in SOURCE_MAP["runs"]}
if tuple(RUNS) != RUN_IDS:
    raise RuntimeError("Window0 closure run set differs from the explicit allowlist")
ASSETS = MANIFEST["assets"]
LOCATORS = {asset["source_map_id"]: path for path, asset in ASSETS.items()}
for _asset in SOURCE_MAP["source_assets"]:
    _path = f"{BASE}/{_asset['relative_path_from_closure']}"
    if ASSETS[_path]["sha256"] != _asset["sha256"] or ASSETS[_path]["source_map_id"] != _asset["asset_id"]:
        raise RuntimeError("Closure asset bindings differ from Window0")
for _identity in SOURCE_MAP["verification"]["source_identity_checks"]:
    _path = Path(_identity["path"]).relative_to(Path(SCIENTIFIC_ROOT)).as_posix()
    if ASSETS[_path]["sha256"] != _identity["frozen_sha256"]:
        raise RuntimeError("Closure imported method identity differs from Window0")
STAGE_COLUMNS = tuple(RUNS[RUN_IDS[0]]["stage_fields"])
STEP_COLUMNS = tuple(RUNS[RUN_IDS[0]]["step_fields"])
STAGE_SERIES = tuple(field for field in STAGE_COLUMNS if field not in ("step", "stage"))
STEP_SERIES = tuple(field for field in STEP_COLUMNS if field != "step")
TERMINAL_FIELDS = ("S0", "ST", "DeltaS_total", "E_bg_total", "E_aa_total", "E_at_total", "E_obs_total", "R_total", "eps_time_total")
DEFINITIONS = SOURCE_MAP["definitions"]
UNITS = SOURCE_MAP["units"]
NA = unresolved("Not applicable to this scalar diagnostic", "NOT_APPLICABLE")
STAGE_CLOCK = "Original t_stage_or_step_time = containing accepted step time_n for all three stages; actual stage-state physical time NOT_ESTABLISHED; no synthetic stage times."
STEP_CLOCK = "Recorded time_np1 endpoint with [time_n,time_np1] interval; S_n refers to time_n; source and canonical accepted steps both 1..N."
INDEX_CONVENTION = "Point ordinal 0-based; completed accepted step 1..N unchanged; source stage 1/2/3 maps to canonical 0/1/2. "
LIMITATIONS = [
    {"id": "lim.closure.fully-discrete", "code": "FULLY_DISCRETE_DIAGNOSTIC", "description": "Fully-discrete temporal residuals are diagnostics, not an exact entropy identity or a new entropy theorem; frozen periodic Case7 first-order FV, SSP-RK3 only.", "affected_refs": [], "severity": "WARNING"},
    {"id": "lim.closure.stage-clock", "code": "STAGE_STATE_TIME_NOT_ESTABLISHED", "description": STAGE_CLOCK, "affected_refs": [], "severity": "INFO"},
    {"id": "lim.closure.no-trajectory", "code": "SPATIAL_TRAJECTORY_MISSING", "description": "No saved spatial trajectory; no spatial replay or substitute fields from other cases or CFLs.", "affected_refs": [], "severity": "INFO"},
    {"id": "lim.closure.channel-attribution", "code": "INTERFACE_PRODUCTION_ATTRIBUTION", "description": "Channel budgets attribute interface production; they are not separate state entropies. Only R_time_cumulative is a recorded cumulative history column.", "affected_refs": [], "severity": "INFO"},
    {"id": "lim.closure.units", "code": "SI_MAPPING_UNKNOWN", "description": "Model quantities have no established SI mapping.", "affected_refs": [], "severity": "INFO"},
]
METHOD_PATH = "solver/fluxes/cross_mode_ec_unified_v1.py"
METHOD_HASH = SOURCE_MAP["protocol"]["method_sha256"]
IMPORTED_METHODS = tuple(path for path in ASSETS if not path.startswith(BASE + "/"))
COMMON = tuple(f"{BASE}/{name}" for name in (
    "FREEZE/FREEZE_MANIFEST.json", "FREEZE/FREEZE_HASHES.sha256", "FREEZE/FREEZE_STATUS.txt",
    "FREEZE/frozen_config.json", "FREEZE/frozen_imported_solver_hashes.json", "FREEZE/frozen_experiment_report.md",
    "FREEZE/README.md", "run_entropy_budget_closure.py",
)) + IMPORTED_METHODS
SUMMARY_PATH = f"{BASE}/FREEZE/frozen_temporal_refinement_summary.csv"
SLOPES_PATH = f"{BASE}/FREEZE/frozen_temporal_slopes.csv"
AUDIT_PATH = f"{BASE}/FREEZE/frozen_audit_summary.json"


def require_run(run_id):
    if isinstance(run_id, str) and run_id in RUN_IDS:
        return RUNS[run_id]
    if isinstance(run_id, str) and re.fullmatch(r"(?:B_u|D_u)-cfl-(?:[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)", run_id):
        raise unsupported_combination("Recognized closure configuration and CFL are outside the frozen five-run selection",
            resource_type="closure_run", identity=known(run_id),
            details=[{"field": "run_id", "issue": "No recorded production run for this combination", "allowed_values": list(RUN_IDS)}])
    raise system_error("INVALID_RESULT_ID", "Closure run identity is not registered", status=404,
        availability="MISSING", resource_type="closure_run")


def run_path(run_id, filename):
    return f"{BASE}/outputs/{require_run(run_id)['source_run_id']}/{filename}"


def evidence_id(run_id, group):
    require_run(run_id)
    return f"ev.entropy-closure.{run_id}.{group}"


def result_id(run_id, group, field):
    require_run(run_id)
    return f"entropy-closure.{run_id}.{group}.{field}"


def verification(ev, basis=(), status="FROZEN_VERIFIED"):
    return {"status": status, "basis": ["Window0 audited frozen SHA-256 bindings; current selected bytes observed before decoding", *basis],
        "verified_at": unresolved("Frozen scientific verification timestamp not recorded"),
        "observation_at": unresolved("Runtime observation is not a scientific verification timestamp"), "evidence_refs": [ev]}


def time(sampling, accumulation="NONE", *, physical_time=None, interval=None, step=None, stage=None, rule=""):
    return {"sampling": sampling, "accumulation": accumulation,
        "physical_time": known(physical_time) if physical_time is not None else NA,
        "interval": known(interval) if interval is not None else NA,
        "step_index": known(step) if step is not None else NA,
        "stage_index": known(stage) if stage is not None else NA, "snapshot_index": NA,
        "index_convention": INDEX_CONVENTION + (STAGE_CLOCK if sampling == "PER_STAGE" else STEP_CLOCK if sampling == "PER_STEP" else rule)}


def definition(field):
    if field in DEFINITIONS:
        return DEFINITIONS[field]
    if field == "dt_eff":
        return {"definition_id": "phase9.closure.dt_eff", "definition": "Recorded effective fixed dt=T/accepted_steps in frozen run summary.", "unit_ref": "model_time", "accumulation": "NONE", "time_rule": "Frozen T=10 common endpoint"}
    if field == "refinement_slope" or field.startswith("pairwise_slope"):
        return {"definition_id": f"phase9.closure.{field}", "definition": SOURCE_MAP["refinement"]["frozen_global_definition" if field == "refinement_slope" else "frozen_pairwise_definition"], "unit_ref": "dimensionless", "accumulation": "NONE", "time_rule": "Existing frozen fit against dt_eff over D_u .2/.1/.05/.025; no Phase9 refit."}
    raise KeyError(field)
