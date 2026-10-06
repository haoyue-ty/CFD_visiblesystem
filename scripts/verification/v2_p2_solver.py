"""Serial real CFD acceptance and repeated benchmark for the P2 adapter."""
import csv
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from backend.core.settings import WORKSPACE_ROOT
from backend.solver_runtime.artifacts import sha256, utc_now, write_json
from backend.solver_runtime.case8_adapter import Case8SolverAdapter, MANIFEST
from scripts.run_case8 import template_request

OUT = WORKSPACE_ROOT / "docs/v2"


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def compare_reference(run, reference_root, entropy_root):
    """Declared before integration: no changing tolerances after seeing results."""
    atol, rtol = 1e-12, 1e-10
    with np.load(run.directory / "final_state.npz") as data:
        state = data["state"]
    with np.load(reference_root / "final_state.npz") as data:
        reference = data["state"]
    check(state.shape == reference.shape, "Reference shape mismatch")
    delta = np.abs(state - reference)
    state_ok = np.allclose(state, reference, atol=atol, rtol=rtol)
    bitwise = np.array_equal(state, reference)
    metrics = json.loads((run.directory / "diagnostics/physical_metrics.json").read_text(encoding="utf-8"))
    reference_metrics = json.loads((reference_root / "case_row.json").read_text(encoding="utf-8"))
    metric_errors = {}
    for key, value in metrics.items():
        if key in reference_metrics and isinstance(value, (float, int)) and not isinstance(value, bool):
            expected = reference_metrics[key]
            check(expected is not None and np.isclose(value, expected, atol=atol, rtol=rtol), f"Metric mismatch: {key}")
            metric_errors[key] = abs(value - expected)
    history = [json.loads(line) for line in (run.directory / "diagnostics/history.jsonl").read_text(encoding="utf-8").splitlines()]
    with (entropy_root / "stage_weighted_history.csv").open(encoding="utf-8", newline="") as stream:
        reference_history = list(csv.DictReader(stream))
    check(len(history) == len(reference_history) == 1912, "History length mismatch")
    history_errors = {}
    for key in history[0]:
        actual = np.array([row[key] for row in history], dtype=float)
        expected = np.array([float(row[key]) for row in reference_history])
        check(np.allclose(actual, expected, atol=atol, rtol=rtol), f"History mismatch: {key}")
        history_errors[key] = float(np.max(np.abs(actual - expected)))
    check(state_ok, "Reference final state mismatch")
    return {"status": "PASS", "state_comparison": "BITWISE" if bitwise else "NUMERICALLY_EQUIVALENT",
            "absolute_tolerance": atol, "relative_tolerance": rtol, "state_max_abs_error": float(delta.max()),
            "state_l2_relative_error": float(np.linalg.norm(delta) / np.linalg.norm(reference)),
            "metric_abs_errors": metric_errors, "history_max_abs_errors": history_errors,
            "history_rows": len(history), "note": "Only recorded global channel/stage columns compared; localization integrals deferred to P4."}


def main():
    adapter = Case8SolverAdapter()
    source = Path(json.loads(MANIFEST.read_text(encoding="utf-8"))["source_root"])
    reference_root = source / "corrected_physics_reproduction_v1/case8/05_case8_D_u"
    entropy_root = source / "jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u"
    reference_files = [reference_root / "final_state.npz", reference_root / "case_row.json",
                       entropy_root / "run_result.json", entropy_root / "stage_weighted_history.csv"]
    references = [{"path": p.relative_to(source).as_posix(), "sha256": sha256(p)} for p in reference_files]
    report = {"status": "RUNNING", "started_at": utc_now(), "source_manifest_sha256": sha256(MANIFEST),
              "comparison_rule": {"atol": 1e-12, "rtol": 1e-10, "preferred": "bitwise"},
              "references_before": references, "runs": []}
    write_json(OUT, "p2_solver_acceptance.json", report)

    def execute(label, request, smoke=None):
        run = adapter.prepare_run(request, smoke_steps=smoke)
        print(json.dumps({"label": label, "run_id": run.run_id, "status": "STARTING"}), flush=True)
        started = perf_counter()
        try:
            result = adapter.execute(run)
        except Exception:
            report.update(status="FAIL", failed_run_id=run.run_id, failed_label=label)
            write_json(OUT, "p2_solver_acceptance.json", report)
            raise
        wall = perf_counter() - started
        provenance = json.loads((run.directory / "provenance.json").read_text(encoding="utf-8"))
        effective = json.loads((run.directory / "effective_solver_config.json").read_text(encoding="utf-8"))
        calls = result["actual_calls"]
        check(calls["q_aa"] == request.config.method.q_aa and calls["q_at"] == request.config.method.q_at, "Flux arguments mismatch")
        check(calls["rhs"] == 3 * result["accepted_steps"] and calls["evolution_flux_calls"] == 6 * result["accepted_steps"], "Actual numerical call mismatch")
        entry = {"label": label, "run_id": run.run_id, "run_kind": result["run_kind"],
                 "started_at": result["started_at"], "finished_at": result["finished_at"],
                 "config_hash": result["config_hash"], "initial_state_hash": result["initial_state_hash"],
                 "final_state_hash": result["final_state_hash"], "effective_time": effective["time"],
                 "effective_grid": effective["grid"], "actual_calls": calls,
                 "channel_totals": result["channel_totals"], "qat_zero_identity": result["qat_zero_identity"],
                 "runtime": {**result["runtime"], "subprocess_total_wall_seconds": wall},
                 "scientific_output_bytes": provenance["output_bytes"],
                 "total_directory_bytes": sum(p.stat().st_size for p in run.directory.rglob("*") if p.is_file()),
                 "result_sha256": provenance["result_sha256"], "output_inventory": provenance["outputs"],
                 "loaded_modules": provenance["loaded_modules"], "status": "PASS"}
        report["runs"].append(entry)
        write_json(OUT, "p2_solver_acceptance.json", report)
        print(json.dumps({"label": label, "run_id": run.run_id, "status": "PASS", "wall_seconds": wall}), flush=True)
        return run, result

    execute("smoke_B_u", template_request("case8.paper.B_u"), 3)
    execute("smoke_D_u", template_request("case8.paper.D_u"), 3)
    request_a = template_request("case8.fast.D_u")
    request_a.config.method.q_at = 0.0
    run_a, result_a = execute("Run_A_B_u_coefficients_fast_grid", request_a)
    run_b, result_b = execute("Run_B_D_u_coefficients_fast_grid_repeat_1", template_request("case8.fast.D_u"))
    check(result_a["initial_state_hash"] == result_b["initial_state_hash"], "A/B initialization mismatch")
    check(result_a["dt"] == result_b["dt"] and result_a["accepted_steps"] == result_b["accepted_steps"], "A/B time protocol mismatch")
    check(result_a["channel_totals"]["E_at"] == 0.0, "Zero channel not exactly zero")
    check(result_b["channel_totals"]["E_at"] > 0.0, "Positive channel did not enter observer")
    with np.load(run_a.directory / "final_state.npz") as a, np.load(run_b.directory / "final_state.npz") as b:
        delta = float(np.max(np.abs(a["state"] - b["state"])))
    check(delta > 0, "q_at had no state effect")
    report["parameter_effect"] = {"status": "PASS", "shared_initial_state_hash": result_a["initial_state_hash"],
                                  "final_state_max_abs_difference": delta, "q_at_zero_E_at": result_a["channel_totals"]["E_at"],
                                  "q_at_positive_E_at": result_b["channel_totals"]["E_at"]}
    for repeat in (2, 3):
        _, result = execute(f"fast_D_u_repeat_{repeat}", template_request("case8.fast.D_u"))
        check(result["final_state_hash"] == result_b["final_state_hash"], "Repeated fast trajectory differs")
    paper, _ = execute("paper_D_u_full_protocol", template_request("case8.paper.D_u"))
    report["reference_comparison"] = compare_reference(paper, reference_root, entropy_root)
    check(references == [{"path": p.relative_to(source).as_posix(), "sha256": sha256(p)} for p in reference_files], "Reference drift")
    repeats = [row for row in report["runs"] if row["label"] in ("Run_B_D_u_coefficients_fast_grid_repeat_1", "fast_D_u_repeat_2", "fast_D_u_repeat_3")]
    walls = [row["runtime"]["subprocess_total_wall_seconds"] for row in repeats]
    report["fast_benchmark"] = {"status": "PASS", "repeats": 3, "failures": 0, "wall_seconds": walls,
                                "median_wall_seconds": float(np.median(walls)), "min_wall_seconds": min(walls), "max_wall_seconds": max(walls),
                                "peak_rss_bytes": [row["runtime"]["peak_rss_bytes"] for row in repeats],
                                "output_bytes": [row["total_directory_bytes"] for row in repeats],
                                "state_hash_identical": True,
                                "scope": "64x16 CFL=.05 T=.04 q_aa=3.96 q_at=.396; local serial process, one BLAS/OMP thread; no ETA promise"}
    report.update(status="PASS", finished_at=utc_now())
    write_json(OUT, "p2_solver_acceptance.json", report)
    print(json.dumps({"status": "PASS", "fast_benchmark": report["fast_benchmark"],
                      "reference": report["reference_comparison"]["state_comparison"]}), flush=True)


if __name__ == "__main__":
    main()
