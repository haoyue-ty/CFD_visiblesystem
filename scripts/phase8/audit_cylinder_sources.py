"""Read-only audit of the selected Cylinder sources and frozen Phase 8 scope.

Never import scientific drivers: inspect their text/AST and saved outputs only.
The only write target is the software worktree's Phase 8 handoff directory.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import numpy as np

from backend.models.core import ResourceSlot, ScientificLimitation, known, unresolved
from backend.models.evidence import EvidenceRecord

WORKTREE = Path(__file__).resolve().parents[2]
SOURCE_ROOT = Path("D:/Paper/passage6")
J2 = SOURCE_ROOT / "jcp_extension_v1/J2_entropy_diagnostics"
CANONICAL = J2 / "J2C_cylinder_formal_v2"
SEMANTICS = J2 / "J2C_S0_localization_semantics"
EXCLUDED = SOURCE_ROOT / "Paper/fig/fig_15/FREEZE"
BASE_COMMIT = "69a318b65b9378066b9a55e429dfca162cef32af"
CONFIGS = ("A_u", "B_u", "D_u")
CHANNELS = ("bg", "aa", "at", "total")
STEPS = (0, 2439, 4878, 7318, 9757)
FAMILIES = {"radial_interior": (31, 128), "angular_interior": (32, 128)}
FIELDS = ("pi_bg", "pi_aa", "pi_at", "pi_total", "J", "pt_z_norm2")
GEOMETRY = ("face_measure", "unit_normal_x", "unit_normal_y", "x_face", "y_face", "r_face", "theta_face")
OUTPUT = WORKTREE / "docs/handoffs/phase8/PHASE8_CYLINDER_SOURCE_MAP.json"


def require_config(config_id: str) -> str:
    """Bootstrap selection gate, not an HTTP handler or scientific adapter."""
    if config_id == "C_u":
        raise ValueError("422 UNSUPPORTED_COMBINATION: Cylinder C_u is unsupported")
    if config_id not in CONFIGS:
        raise ValueError("404 UNKNOWN_CONFIG")
    return config_id


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def inventory(paths: list[Path]) -> list[dict]:
    return [{"path": p.relative_to(SOURCE_ROOT).as_posix(), "sha256": digest(p),
             "size_bytes": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns}
            for p in sorted(set(paths))]


def assignment(path: Path, name: str):
    """Read literal scientific constants without executing any scientific code."""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Literal {name} absent from {path.name}")


def function_literal(path: Path, function: str, name: str):
    node = next(n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef) and n.name == function)
    for statement in node.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in statement.targets):
            return ast.literal_eval(statement.value)
    raise AssertionError(f"Literal {function}.{name} missing")


def frozen_prerequisites() -> dict:
    manifest = read_json(WORKTREE / "docs/PHASE4_FREEZE_MANIFEST.json")
    checks = []
    for f in manifest["documents"] + [f for f in manifest["upstream_documents"] if f["role"] == "PHASE3_IA"]:
        p = WORKTREE / "docs" / Path(f["path"]).name
        actual = digest(p)
        assert actual == f["sha256"].lower(), p.name
        # Read all four documents. Their hashes freeze the complete contents.
        p.read_text(encoding="utf-8")
        checks.append({"path": p.relative_to(WORKTREE).as_posix(), "sha256": actual, "unchanged": True})
    phase7 = read_json(WORKTREE / "docs/handoffs/phase7/PHASE7_SPECTRAL_FREEZE_MANIFEST.json")
    archive = WORKTREE / "docs/handoffs/phase8/PHASE7_ACCEPTED_BASELINE.zip"
    # Retain the exact mixed-line-ending accepted bytes independently of the
    # mutable checkout, which will itself receive the integrated Phase8 slice.
    with zipfile.ZipFile(archive) as baseline_archive:
        accepted_bytes = {name: baseline_archive.read(name) for name in baseline_archive.namelist()}
    assert set(accepted_bytes) == ({item["path"] for item in phase7["accepted_files"]}
                                   | set(phase7["prerequisite_freeze_sha256"]))
    prerequisite_hashes = []
    for rel, expected in phase7["prerequisite_freeze_sha256"].items():
        assert hashlib.sha256(accepted_bytes[rel]).hexdigest() == expected
        assert digest(WORKTREE / rel) == expected
        prerequisite_hashes.append({"path": rel, "frozen_windows_sha256": expected,
                                    "checkout_sha256": digest(WORKTREE / rel), "content_unchanged": True})
    assert read_json(WORKTREE / "docs/PHASE5_CASE8_FREEZE.json")["PHASE5_CASE8_STATUS"] == "FROZEN_ACCEPTED"
    assert "PHASE6_ALLOCATION_STATUS=FROZEN_ACCEPTED" in (WORKTREE / "docs/handoffs/phase6/PHASE6_ALLOCATION_FREEZE.md").read_text()
    assert phase7["status"] == "FROZEN_ACCEPTED"
    # Bind the original accepted bytes and the materialized baseline separately
    # from the authorized Window1--3 integration changes. A bootstrap-only audit
    # must not require the integrated application's catalog to remain bootstrap.
    integrated_paths = set(subprocess.check_output(
        ["git", "diff", "--name-only", BASE_COMMIT, "aaf478da6b9c6302f4843b7c76b5466b686b960a"],
        cwd=WORKTREE, text=True).splitlines())
    integrated_paths.add(".gitattributes")  # exact Phase5 CRLF checkout preservation
    # Window2 Closure is authorized to evolve these shared software interfaces.
    # The historical accepted archives, prerequisite hashes, scientific sources,
    # and all other accepted files remain subject to the exact original checks.
    closure_api_seams = {
        "backend/api/evidence.py", "backend/api/registry.py", "backend/api/system.py",
        "backend/core/app.py", "backend/schemas/requests.py", "backend/services/spectral_resources.py",
        "config/openapi.json", "frontend/src/types/generated/api.d.ts", "tests/test_bootstrap.py",
        "tests/window2_case8_api/conftest.py", "tests/window2_case8_api/test_case8_api_contract.py",
    }
    normalized = []
    integration_changes = []
    later_software_changes = []
    for item in phase7["accepted_files"]:
        previous, current = accepted_bytes[item["path"]], WORKTREE / item["path"]
        assert hashlib.sha256(previous).hexdigest() == item["sha256"], f"Accepted source changed: {item['path']}"
        baseline = subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{item['path']}"], cwd=WORKTREE)
        assert previous.replace(b"\r\n", b"\n") == baseline.replace(b"\r\n", b"\n")
        if previous.replace(b"\r\n", b"\n") != current.read_bytes().replace(b"\r\n", b"\n"):
            assert item["path"] in integrated_paths | closure_api_seams, f"Unapproved frozen slice change: {item['path']}"
            if item["path"] != ".gitattributes":
                delivered = subprocess.check_output(["git", "show", f"aaf478da6b9c6302f4843b7c76b5466b686b960a:{item['path']}"], cwd=WORKTREE)
                if current.read_bytes().replace(b"\r\n", b"\n") != delivered.replace(b"\r\n", b"\n"):
                    assert item["path"] in closure_api_seams, f"Unapproved later change: {item['path']}"
                    later_software_changes.append({"path": item["path"], "accepted_phase8_sha256": hashlib.sha256(delivered).hexdigest(),
                                                   "current_sha256": digest(current), "authorization": "Phase9B Window2 frozen CLO01–05 API integration"})
            integration_changes.append(item["path"])
            continue
        if digest(current) != item["sha256"]:
            normalized.append(item["path"])
    return {"phase4_documents": checks, "prerequisite_freeze_hashes": prerequisite_hashes,
            "phase5": "FROZEN_ACCEPTED", "phase6": "FROZEN_ACCEPTED",
            "phase7": "FROZEN_ACCEPTED", "phase7_accepted_files_verified": len(phase7["accepted_files"]),
            "phase7_manifest_sha256": digest(WORKTREE / "docs/handoffs/phase7/PHASE7_SPECTRAL_FREEZE_MANIFEST.json"),
            "checkout_line_ending_only_differences": normalized,
            "authorized_integration_changes": integration_changes,
            "authorized_later_software_changes": later_software_changes,
            "phase7_acceptance_semantics": "Original 161/161 SHA256 match; materialized baseline equals accepted text; Phase8 delivery is retained by Git and later Closure software seam observations are recorded separately."}


def history_series(columns: list[str]) -> list[dict]:
    series = []
    for channel in CHANNELS:
        for prefix, canonical, accumulation, definition in (
            ("E", f"E_{channel}_cumulative", "CUMULATIVE", "sum accepted-step deltaE through this endpoint"),
            ("deltaE", f"delta_E_{channel}", "PER_STEP_INCREMENT", "dt * (rate_s0/6 + rate_s1/6 + 2*rate_s2/3)"),
        ):
            series.append({"series_id": canonical, "source_column": f"{prefix}_{channel}_int", "channel": channel,
                           "sampling": "PER_STEP", "accumulation": accumulation, "definition": definition,
                           "unit": {"system": "MODEL", "label": "model integrated entropy", "si_mapping": "UNKNOWN"},
                           "scope": "INTERIOR_ONLY", "time_coordinate": "time_end"})
        for stage in range(3):
            col = f"dotE_{channel}_int_s{stage}"
            series.append({"series_id": col, "source_column": col, "channel": channel, "stage_index": stage,
                           "sampling": "PER_STEP_WITH_STAGE_COLUMN", "accumulation": "NONE",
                           "definition": "instantaneous sum(face_measure * pi_channel) over both interior face families at the saved RK stage input",
                           "unit": {"system": "MODEL", "label": "model integrated entropy rate", "si_mapping": "UNKNOWN"},
                           "scope": "INTERIOR_ONLY", "time_coordinate": "time_start/time_end plus explicit stage_index; not an endpoint rate"})
    for prefix, quantity in (("J_max_int", "J"), ("Pt_z_norm2_max_int", "Pt_z_norm2"), ("Pi_at_max_int", "Pi_at"),
                             ("absolute_additivity_error", "entropy rate residual"), ("relative_additivity_error", "relative entropy rate residual")):
        for stage in range(3):
            col = f"{prefix}_s{stage}"
            series.append({"series_id": col, "source_column": col, "sampling": "PER_STEP_WITH_STAGE_COLUMN",
                           "stage_index": stage, "accumulation": "NONE", "scope": "INTERIOR_ONLY",
                           "definition": "max over both interior face families at this RK stage" if "max" in prefix else
                           ("abs(dotE_total-dotE_bg-dotE_aa-dotE_at)" if prefix == "absolute_additivity_error" else
                            "absolute_additivity_error/max(1,abs(dotE_total))"),
                           "unit": {"system": "DIMENSIONLESS" if prefix == "relative_additivity_error" else "MODEL",
                                    "label": "1" if prefix == "relative_additivity_error" else f"model {quantity}", "si_mapping": "UNKNOWN"}})
    assert {s["source_column"] for s in series} == set(columns) - {"config", "run_id", "step", "dt", "time_start", "time_end"}
    return series


def inspect_history(path: Path, result: dict) -> dict:
    rows = csv_rows(path)
    assert len(rows) == 9757
    assert [int(r["step"]) for r in rows] == list(range(9757))
    t0 = np.array([float(r["time_start"]) for r in rows])
    t1 = np.array([float(r["time_end"]) for r in rows])
    dt = np.array([float(r["dt"]) for r in rows])
    assert t0[0] == 0.0 and t1[-1] == 2.0 and np.all(t1 > t0)
    np.testing.assert_allclose(t0[1:], t1[:-1], rtol=0, atol=5e-16)
    np.testing.assert_allclose(t1-t0, dt, rtol=0, atol=5e-16)
    for c in CHANNELS:
        increments = np.array([float(r[f"deltaE_{c}_int"]) for r in rows])
        rates = np.array([[float(r[f"dotE_{c}_int_s{s}"]) for s in range(3)] for r in rows])
        cumulative = np.array([float(r[f"E_{c}_int"]) for r in rows])
        np.testing.assert_allclose(increments, dt * (rates @ np.array([1/6, 1/6, 2/3])), rtol=2e-15, atol=1e-17)
        np.testing.assert_allclose(cumulative, np.cumsum(increments), rtol=0, atol=0)
        assert cumulative[-1] == result["channel_totals"][c]
        if result["q_at"] == 0 and c == "at":
            assert np.count_nonzero(increments) == np.count_nonzero(cumulative) == np.count_nonzero(rates) == 0
    columns = list(rows[0])
    return {"source": path.relative_to(SOURCE_ROOT).as_posix(), "record_count": len(rows), "columns": columns,
            "source_step_range": [0, 9756], "completed_step_range": [1, 9757],
            "mapping": "step_index=source_step_index+1; row is one accepted-step interval, cumulative value at time_end",
            "first_interval": [float(t0[0]), float(t1[0])], "last_interval": [float(t0[-1]), float(t1[-1])],
            "scope": "INTERIOR_ONLY", "rk_weights": [1/6, 1/6, 2/3], "series": history_series(columns),
            "channel_semantics": {"bg": "saved background diagnostic channel", "aa": "saved acoustic-acoustic diagnostic channel",
                                  "at": "saved acoustic-transverse cross-mode diagnostic channel", "total": "bg+aa+at (audited additivity)"},
            "validation": "all rows: numbering, interval continuity, RK increments, cumulative sums and terminal totals checked"}


def inspect_snapshots(run: Path) -> list[dict]:
    files = sorted((run / "snapshots").glob("*.npz"))
    assert len(files) == 5
    snapshots = []
    for index, (path, step) in enumerate(zip(files, STEPS), 1):
        with np.load(path, allow_pickle=False) as z:
            assert int(z["step"].item()) == step
            expected = {"step", "time"} | {f"{f}_{k}" for f in FAMILIES for k in FIELDS + GEOMETRY}
            assert set(z.files) == expected
            members = {k: {"shape": list(z[k].shape), "dtype": str(z[k].dtype)} for k in z.files}
            for family, shape in FAMILIES.items():
                for key in FIELDS + GEOMETRY:
                    assert z[f"{family}_{key}"].shape == shape
                    assert np.isfinite(z[f"{family}_{key}"]).all()
                assert (z[f"{family}_face_measure"] > 0).all()
                np.testing.assert_allclose(z[f"{family}_unit_normal_x"]**2+z[f"{family}_unit_normal_y"]**2, 1, atol=5e-16)
                np.testing.assert_allclose(np.hypot(z[f"{family}_x_face"], z[f"{family}_y_face"]), z[f"{family}_r_face"], atol=2e-15)
                np.testing.assert_allclose(z[f"{family}_pi_total"], sum(z[f"{family}_pi_{c}"] for c in CHANNELS[:3]), atol=1e-12)
            snapshots.append({"snapshot_index": index, "step_index": step, "source_step_index": step,
                              "physical_time": float(z["time"].item()), "source": path.relative_to(SOURCE_ROOT).as_posix(),
                              "sampling": "MULTI_SNAPSHOT", "accumulation": "NONE", "scope": "INTERIOR_ONLY",
                              "members": members, "field_members": [f"{f}_{k}" for f in FAMILIES for k in FIELDS],
                              "geometry_members": [f"{f}_{k}" for f in FAMILIES for k in GEOMETRY],
                              "missing_primitive_fields": ["density", "pressure", "velocity", "primitive_state"]})
    return snapshots


def inspect_allocation(run: Path, result: dict, geometry: dict) -> dict:
    path = run / "spatial_cumulative.npz"
    with np.load(path, allow_pickle=False) as z:
        assert set(z.files) == {"bins", "channel_bg", "channel_aa", "channel_at", "channel_total",
                                "activity_J", "activity_Pt_z_norm2", "activity_Pi_at", "shock_at", "shock_J", "shock_Pt_z_norm2"}
        assert z["bins"].shape == (17,) and np.all(np.diff(z["bins"]) > 0)
        sums = {}
        fractions = {}
        for c in CHANNELS:
            a = z[f"channel_{c}"]
            assert a.shape == (16,) and np.isfinite(a).all()
            sums[c] = float(a.sum())
            np.testing.assert_allclose(sums[c], result["channel_totals"][c], rtol=1e-13, atol=1e-14)
            fractions[c] = {"definition": f"channel_{c}[bin]/sum(channel_{c})", "unit": "1", "accumulation": "TRAJECTORY_INTEGRATED",
                            "availability": "AVAILABLE" if sums[c] != 0 else "UNSUPPORTED",
                            "reason": "zero channel denominator; do not present numeric zero fractions" if sums[c] == 0 else "positive denominator",
                            "sum": float((a/sums[c]).sum()) if sums[c] else None}
        np.testing.assert_allclose(z["channel_total"], z["channel_bg"]+z["channel_aa"]+z["channel_at"], rtol=1e-13, atol=1e-14)
        np.testing.assert_array_equal(z["activity_Pi_at"], z["channel_at"])
        front = float(z["shock_at"].item())
        fraction = front/sums["at"] if sums["at"] else None
        return {"source": path.relative_to(SOURCE_ROOT).as_posix(), "representations": ["ANGULAR_SECTORS", "REGION_SCALAR"],
                "sector_count": 16, "bin_edges": z["bins"].tolist(), "bin_edges_count": 17, "angular_unit": "radian",
                "channel_members": [f"channel_{c}" for c in CHANNELS], "channel_totals": sums, "sector_fractions": fractions,
                "activity_members": ["activity_J", "activity_Pt_z_norm2", "activity_Pi_at"],
                "activity_semantics": "face-measured, stage-weighted cumulative sums; not instantaneous maxima or a 2D field",
                "front_band": {"representation": "REGION_SCALAR", "source_member": "shock_at", "scalar": front,
                               "fraction": fraction, "fraction_availability": "AVAILABLE" if fraction is not None else "UNSUPPORTED",
                               "definition": "shock_at/sum(channel_at); undefined if denominator is zero",
                               "accumulation": "TRAJECTORY_INTEGRATED", "scope": "INTERIOR_ONLY",
                               "mask": {"id": "mask.cylinder.fixed-A-front", "type": "CYLINDER_FIXED_FRONT_BAND",
                                        "policy": "FIXED_A_U_AUTHORITATIVE_RADIAL_ANCHORS", **geometry,
                                        "angular_scope": "unwrap source anchors; linear radial interpolation only between min/max unwrapped angles; NaN outside",
                                        "predicate": "finite(interpolated_front_radius) and abs(r_face-interpolated_front_radius)<=0.16",
                                        "stored_mask_array": "MISSING; predicate/anchors available, no mask bitmap saved in canonical run"}},
                "sampling": "STATIC", "accumulation": "TRAJECTORY_INTEGRATED", "scope": "INTERIOR_ONLY",
                "measure_convention": "dt * RK_weight * native_face_measure * pi_channel already included; do not multiply again",
                "cumulative_2d": "MISSING", "prohibited_derivations": ["instantaneous frames to cumulative 2D", "sectors interpolated to 2D heatmap"]}


def missing_contract(method_hash: str) -> dict:
    evidence_id, target = "ev.missing.cylinder-cumulative2d", "missing_cylinder_trajectory_spatial_pi_at"
    limitation = ScientificLimitation(id="lim.cylinder.no-cumulative-map", code="NO_FULL_CUMULATIVE_2D",
        description="Selected J2C formal v2 saves cumulative angular sectors and fixed-band scalars, without full-trajectory 2D Pi_at. A separate Fig15 diagnostic rerun exists outside this frozen contract.",
        affected_refs=[target], severity="WARNING").model_dump(mode="json")
    verification = {"status": "MISSING", "basis": ["Selected canonical NPZ member inventory and frozen 05 section 12"],
                    "verified_at": unresolved("Scientific verification timestamp not established"),
                    "observation_at": unresolved("Audit metadata is not a scientific verification date"), "evidence_refs": [evidence_id]}
    missing = unresolved("Not saved by selected J2C formal v2; separate Fig15 rerun excluded by frozen scope", "MISSING")
    asset = {"asset_id": target, "source_id": "J2C_cylinder_formal_v2", "source_display": "Selected Cylinder full-trajectory cumulative 2D Pi_at",
             "relative_origin": missing, "role": "MISSING_REFERENCE", "format": "UNKNOWN", "recorded_data_hash": missing,
             "current_data_hash": missing, "data_drift": unresolved("No selected asset to compare"), "verification": verification,
             "canonical_selected": True, "limitations": [limitation]}
    evidence = {"schema_version": "1.0.0", "evidence_id": evidence_id, "result_ids": [], "result_contexts": [],
                "experiment_id": known("cylinder"), "config_id": unresolved("Experiment-wide selected dataset gap", "NOT_APPLICABLE"),
                "config": unresolved("Experiment-wide gap", "NOT_APPLICABLE"), "definitions": [], "masks": [],
                "method_name": known("cross_mode_ec_unified_v1"), "method_hash": known(method_hash),
                "recorded_source_hash": known(method_hash), "current_source_hash": known(method_hash),
                "source_observations": [], "source_assets": [asset], "data_hash": missing,
                "freeze_reference": unresolved("Gap is frozen by the software contract, not a numeric scientific freeze"),
                "processing": [], "verification": verification, "limitations": [limitation],
                "source_drift": unresolved("Missing resource has no complete source dependency bundle"),
                "created_at": unresolved("No source creation time for missing resource"), "verified_at": verification["verified_at"],
                "related_evidence_refs": [], "superseded_by": unresolved("No contract supersession", "NOT_APPLICABLE")}
    slot = {"availability": "MISSING", "error": {"domain": "SCIENTIFIC", "code": "MISSING_SCIENTIFIC_ASSET",
            "message": "Full trajectory cumulative 2D Pi_at is unavailable in the selected frozen Cylinder dataset",
            "target": {"resource_type": "cumulative_2d", "identity": known(target)}, "retryable": False,
            "details": [], "evidence_refs": [evidence_id]}}
    return {"Evidence": EvidenceRecord.model_validate(evidence).model_dump(mode="json"),
            "ScientificLimitation": limitation, "ResourceSlot": ResourceSlot[dict].model_validate(slot).model_dump(mode="json")}


def audit() -> dict:
    prerequisites = frozen_prerequisites()
    protocol_file = CANONICAL / "J2C_V2_PROTOCOL_LOCK.json"
    protocol = read_json(protocol_file)
    assert tuple(protocol["configurations"]) == CONFIGS and tuple(protocol["snapshot_steps"]) == STEPS
    assert protocol["protocol"] == {"dt": 0.00020498103925386903, "final_time": 2.0, "gamma": 1.4,
                                    "mach": 3.0, "nr": 32, "ntheta": 128, "r_inner": 0.5, "r_outer": 8.0, "steps": 9757, "stretch": 3.0}
    driver = CANONICAL / "analysis/cylinder_j2c_v2.py"
    assert function_literal(driver, "protocol_lock", "expected") == protocol["protocol"]
    assert assignment(driver, "CONFIGURATIONS") == protocol["configurations"]
    assert assignment(SOURCE_ROOT / "solver/experiments/corrected_cylinder_dispatcher.py", "CONFIGURATIONS") == protocol["configurations"]
    status = read_json(CANONICAL / "J2C_V2_STATUS.json")
    assert status["j2c_v2_gate"] == "PASS" and status["primary_budget_scope"] == "INTERIOR_ONLY"
    references = [SOURCE_ROOT / v for refs in protocol["references"].values() for v in refs.values()]
    dependencies = [SOURCE_ROOT / p for p in (
        "solver/core/time_integrator.py", "solver/experiments/cylinder_b2_4_production.py", "solver/experiments/corrected_cylinder_dispatcher.py",
        "solver/core/curvilinear_mesh.py", "solver/diagnostics/cylinder.py", "solver/fluxes/cross_mode_ec_unified_v1.py",
        "solver/fluxes/chandrashekar_es.py", "solver/fluxes/unbounded_cross_mode.py", "solver/core/entropy.py", "solver/fluxes/sos_v4.py",
        "jcp_extension_v1/J2_entropy_diagnostics/diagnostics/channel_entropy_diagnostics.py",
        "unified_corrected_method_v3/CERTIFICATION_MANIFEST.json")]
    # Audit the whole selected trees, including extra candidates, not all passage6.
    roots = (CANONICAL, SEMANTICS, EXCLUDED)
    files = [p for root in roots for p in root.rglob("*") if p.is_file()] + references + dependencies
    before = inventory(files)
    method_hash = digest(SOURCE_ROOT / "solver/fluxes/cross_mode_ec_unified_v1.py")
    assert method_hash == assignment(driver, "EXPECTED_METHOD_HASH")
    assert digest(SOURCE_ROOT / "solver/core/time_integrator.py") == protocol["authoritative_advance"]["source_sha256"]
    geometry = protocol["shock_localization_geometry"]
    assert geometry["radial_half_width"] == 0.16
    assert digest(SOURCE_ROOT / geometry["source"]) == geometry["source_sha256"]
    with np.load(SOURCE_ROOT / geometry["source"], allow_pickle=False) as z:
        np.testing.assert_array_equal(z["front_angles"], geometry["front_angles"])
        np.testing.assert_array_equal(z["front_radii"], geometry["front_radii"])
    result_hashes = {r["path"]: r["sha256"] for r in csv_rows(CANONICAL / "provenance/result_hashes.csv")}
    runs = {}
    for config in CONFIGS:
        require_config(config)
        run = CANONICAL / "runs" / f"cylinder_{config}"
        result = read_json(run / "run_result.json")
        assert result["config"] == config and result["accepted_steps"] == 9757 and result["final_time"] == 2.0
        assert {k: result[k] for k in ("q_aa", "q_at")} == protocol["configurations"][config]
        for path in run.rglob("*"):
            if path.is_file():
                assert digest(path) == result_hashes[path.relative_to(CANONICAL).as_posix()]
        with np.load(run / "final_state.npz", allow_pickle=False) as z, np.load(SOURCE_ROOT / protocol["references"][config]["state"], allow_pickle=False) as authoritative:
            np.testing.assert_array_equal(z["state"], authoritative["state"])
            assert int(z["accepted_steps"].item()) == 9757 and float(z["time"].item()) == 2.0
            final_members = {k: {"shape": list(z[k].shape), "dtype": str(z[k].dtype)} for k in z.files}
        runs[config] = {"source_run_id": f"cylinder_{config}", "config_id": config, "parameters": protocol["configurations"][config],
                        "snapshot_source": inspect_snapshots(run), "history_source": inspect_history(run / "stage_weighted_history.csv", result),
                        "allocation_source": inspect_allocation(run, result, geometry),
                        "metrics_source": {"path": (run / "physical_metrics.json").relative_to(SOURCE_ROOT).as_posix(),
                                           "available_keys": [k for k, v in result["physical_metrics"].items() if v is not None],
                                           "unavailable_keys": [k for k, v in result["physical_metrics"].items() if v is None],
                                           "time": 2.0, "sampling": "FINAL_STATE", "null_policy": "unavailable metadata, never numeric zero",
                                           "detector_source": "solver/diagnostics/cylinder.py",
                                           "width_definition": "radial pressure W10-90: steepest local p50 anchor; nearest physically ordered p90/p10; detector-limited",
                                           "HF_RMS_definition": "8 upstream +/-12 degree rays, quadratic detrend in unwrapped angle, neighboring 3-point high-pass; RMS normalized by local radial spacing",
                                           "HF_RMS_unit": "local radial cell spacing (dimensionless)", "width_unit": "model length; SI UNKNOWN",
                                           "high_mode_energy_definition": "rfft(front residual), k>=max(2,ray_count//4), sum(abs(modes)^2)/ray_count^2; model length squared",
                                           "saved_reference_metrics_match": all(v == 0 for v in result["physical_metric_differences"].values())},
                        "terminal_state_source": {"path": (run / "final_state.npz").relative_to(SOURCE_ROOT).as_posix(),
                                                  "members": final_members, "authoritative_reproduction": "BITWISE", "primitive_movie": "MISSING"},
                        "verification_state": {"upstream_gate": "PASS", "run_assets_match_recorded_hashes": True,
                                               "audit_checks": "PASS", "scientific_verification_promotion": False}}
    # This independent rerun is a real source, but cannot silently supersede the
    # selected Phase4 dataset. Verify and report it without registering its arrays.
    manifest = read_json(EXCLUDED / "FREEZE_MANIFEST.json")
    for item in manifest["files"]:
        assert digest(EXCLUDED / item["relative_path"]) == item["sha256"]
    integral = sum(float((np.load(EXCLUDED / f"A_at_{family}_faces.npy", allow_pickle=False) *
                          np.load(EXCLUDED / f"{family}_face_measure.npy", allow_pickle=False)).sum()) for family in ("radial", "angular"))
    expected_total = runs["D_u"]["allocation_source"]["channel_totals"]["at"]
    np.testing.assert_allclose(integral, expected_total, rtol=1e-12)
    after = inventory(files)
    # Check names too: rglob again to catch creations/removals within selected roots.
    after_files = [p for root in roots for p in root.rglob("*") if p.is_file()] + references + dependencies
    assert before == after == inventory(after_files), "Scientific sources changed during audit"
    assets = []
    for i, item in enumerate(before):
        p = SOURCE_ROOT / item["path"]
        recorded = result_hashes.get(p.relative_to(CANONICAL).as_posix()) if p.is_relative_to(CANONICAL) else None
        assets.append({"asset_id": f"phase8.source.{i:03d}", **item,
                       "selection": "OFF_CONTRACT_CANDIDATE" if p.is_relative_to(EXCLUDED) else
                       ("CANONICAL_RUN_DATA" if p.is_relative_to(CANONICAL / "runs") else "AUDIT_DEPENDENCY"),
                       "recorded_sha256": recorded,
                       "verification_state": "MATCHES_UPSTREAM_RECORDED_HASH" if recorded == item["sha256"] else
                       ("RECORDED_HASH_DRIFT" if recorded else "CURRENT_HASH_OBSERVED_ONLY")})
    return {"schema": "SHOCKPATH_PHASE8_SOURCE_MAP_V1", "window": "0_PHASE8_BOOTSTRAP", "status": "PASS_WITH_SCOPE_DISCREPANCY",
            "phase8_base_commit": BASE_COMMIT, "branch": "phase8/bootstrap", "worktree": str(WORKTREE),
            "baseline_resolution": {"original_branch": "phase7/spectral-adapter", "original_worktree_clean": False,
                                    "phase7_original_accepted_state": "WORKING_TREE", "ancestor_commit": "088909baa13733999c75148a315326d6be819f19",
                                    "materialized_branch": "phase7/spectral-integration", "accepted_files_sha256_matched": 161,
                                    "original_branch_worktree_and_index_preserved": True,
                                    "policy": "All Phase8 development windows MUST branch from phase8_base_commit, not current original HEAD"},
            "frozen_prerequisites": prerequisites, "scientific_source_root": str(SOURCE_ROOT), "source_access": "READ_ONLY",
            "canonical_experiment_ids": ["cylinder"], "cross_flow_experiment_ids": ["case8", "cylinder"],
            "source_experiment_id": protocol["case"], "source_dataset_id": "J2C_cylinder_formal_v2",
            "config_ids": list(CONFIGS), "rejected_configs": {"C_u": {"availability": "UNSUPPORTED", "http_status": 422, "code": "UNSUPPORTED_COMBINATION"}},
            "protocol_source": {"path": protocol_file.relative_to(SOURCE_ROOT).as_posix(), "protocol": protocol["protocol"],
                                "grid": "O-grid", "method": protocol["method"], "method_hash": method_hash,
                                "configurations": protocol["configurations"], "snapshot_steps": protocol["snapshot_steps"],
                                "verification_state": "protocol constants match literal driver/dispatcher; raw records and authoritative states match"},
            "snapshot_identity_convention": "USER_VISIBLE_1_BASED_RECORDED_INDEX; completed accepted-step index preserved separately",
            "snapshot_field_semantics": {"pi_bg": "instantaneous background entropy-production density",
                                         "pi_aa": "instantaneous acoustic-acoustic entropy-production density",
                                         "pi_at": "instantaneous acoustic-transverse entropy-production density",
                                         "pi_total": "instantaneous total entropy-production density, bg+aa+at",
                                         "J": "instantaneous native-face J diagnostic; not an integrated entropy budget",
                                         "pt_z_norm2": "instantaneous transverse opportunity norm squared; not entropy production"},
            "mask_source": {"protocol_geometry": geometry, "definition_source": driver.relative_to(SOURCE_ROOT).as_posix(),
                            "semantics_source": (SEMANTICS / "CYLINDER_LOCALIZATION_TRACE.md").relative_to(SOURCE_ROOT).as_posix(),
                            "source_symbol": "_front_mask; spatial_stage_increment", "stored_mask_bitmap": "MISSING"},
            "runs": runs, "source_files": assets, "missing_assets": {"cumulative_2d": missing_contract(method_hash),
                "snapshot_primitive_movie": "MISSING; only instantaneous diagnostic faces and final conservative state are selected"},
            "cross_flow": {"schema": "CrossFlowComparison", "left": "case8", "right": "cylinder", "default_configs": ["D_u", "D_u"],
                           "schema_binding": "docs/05_DATA_SCHEMA.md section 12; descriptors here are audit metadata, not delivered comparison results",
                           "comparison_fields": ["comparison_id", "left", "right", "comparability", "ranking_policy", "limitations", "evidence_refs"],
                           "side_fields": ["experiment_id", "config_id", "protocol", "budget", "metrics", "allocation", "front_band", "snapshot_refs", "history_refs", "evidence_refs"],
                           "left_configs": ["A_u", "B_u", "C_u", "D_u"], "right_configs": list(CONFIGS),
                           "left_cumulative_map_scope": "D_u only; A/B/C map MISSING with budgets/metrics retained",
                           "left_front_band_scope": "UNSUPPORTED; no Cylinder band concept on Case8",
                           "ranking_policy": "NO_UNIFIED_RANKING", "default_comparability": "DESCRIPTIVE_ONLY",
                           "rules": [{"left_definition_id": l, "right_definition_id": r, "status": "DESCRIPTIVE_ONLY", "reason": reason,
                                      "mapping_ref": unresolved("No declared mapping", "NOT_APPLICABLE")} for l, r, reason in (
                               ("case8.native_face_localization", "cylinder.fixed_radial_front_band_fraction", "different masks, face sets and geometry"),
                               ("case8.high_k_energy", "cylinder.front_HF_RMS", "Fourier high-k energy/fraction versus spacing-normalized local three-point HF RMS"),
                               ("case8.cartesian_width", "cylinder.radial_bow_front_width", "different Cartesian/radial detectors and detector floors"),
                               ("case8.entropy_budget", "cylinder.entropy_budget", "different budget and boundary scopes, Cartesian/O-grid geometry and horizons T=.08/T=2"))],
                           "source": (SEMANTICS / "CROSS_CASE_COMPARABILITY.md").relative_to(SOURCE_ROOT).as_posix(),
                           "no_unified_score_or_winner": True},
            "source_discrepancies": [{"id": "OFF_CONTRACT_CUMULATIVE_2D_EXISTS", "configuration": "D_u", "path": EXCLUDED.relative_to(SOURCE_ROOT).as_posix(),
                                     "freeze_id": manifest["freeze_id"], "run_kind": manifest["run_kind"], "manifest_sha256": digest(EXCLUDED / "FREEZE_MANIFEST.json"),
                                     "manifest_files_verified": len(manifest["files"]), "native_face_field_integral": integral,
                                     "availability_in_source_root": "AVAILABLE", "availability_in_frozen_phase8_contract": "MISSING",
                                     "selected_for_phase8": False, "reason": "Frozen 03/04/05/06 and user require the J2C formal v2 selected scope with MISSING cumulative_2d",
                                     "next_action": "Resolve source-selection contradiction explicitly before any future contract/capability expansion; keep frozen representation for this bootstrap"}],
            "source_preservation": {"scope": "Complete selected J2C formal v2, J2C S0, Fig15 FREEZE trees plus protocol references and listed dependencies; not whole passage6",
                                    "file_count": len(before), "before_inventory": before, "after_inventory": after,
                                    "comparison": "relative paths + SHA256 + size + mtime_ns", "status": "PASS"},
            "scientific_files_modified": False, "cfd_runs_started": 0,
            "implementation_boundary": {"adapter": False, "api": False, "vue": False, "contract_03_04_05_06_modified": False,
                                        "scope": ["Mach3 Cylinder", "Case8-Cylinder descriptive comparison"],
                                        "excluded": ["Entropy Closure", "Mechanism Explorer", "Explore Guided Flow", "Accounts", "UI polish"]}}


def main() -> None:
    result = audit()
    # Fixed software output path, verified outside the READ ONLY science root.
    assert OUTPUT.is_relative_to(WORKTREE) and not OUTPUT.is_relative_to(SOURCE_ROOT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"SOURCE_AUDIT={result['status']};files={result['source_preservation']['file_count']};snapshots=15;history=3x9757")


if __name__ == "__main__":
    main()
