"""Supplement P2 with all-coefficient smoke checks and source-step equivalence."""
import json
import subprocess
import sys

import numpy as np

from backend.core.settings import WORKSPACE_ROOT
from backend.solver_runtime.artifacts import write_json
from backend.solver_runtime.case8_adapter import Case8SolverAdapter, PreparedRun, worker_environment
from scripts.run_case8 import template_request


def main():
    adapter = Case8SolverAdapter()
    main_report = json.loads((WORKSPACE_ROOT / "docs/v2/p2_solver_acceptance.json").read_text(encoding="utf-8"))
    runs = {}
    for name in ("B_u", "D_u"):
        row = next(r for r in main_report["runs"] if r["label"] == "smoke_" + name)
        runs[name] = PreparedRun(row["run_id"], WORKSPACE_ROOT / "runtime/runs" / row["run_id"])
    for name in ("A_u", "C_u"):
        run = adapter.prepare_run(template_request("case8.paper." + name), smoke_steps=3)
        adapter.execute(run)
        runs[name] = run
    checks = {}
    for name, run in runs.items():
        completed = subprocess.run([sys.executable, "-B", "-m", "scripts.verification.v2_p2_equivalence", "--run-id", run.run_id],
                                   cwd=run.directory, env=worker_environment(run.directory), capture_output=True, text=True, check=True)
        checks[name] = json.loads(completed.stdout)
    effects = {}
    for left, right in (("A_u", "B_u"), ("C_u", "D_u")):
        a_result, b_result = adapter.postprocess(runs[left]), adapter.postprocess(runs[right])
        if (a_result["initial_state_hash"] != b_result["initial_state_hash"]
                or a_result["dt"] != b_result["dt"] or a_result["accepted_steps"] != b_result["accepted_steps"]):
            raise RuntimeError("q_aa comparison initial/time protocol mismatch")
        with np.load(runs[left].directory / "final_state.npz") as a, np.load(runs[right].directory / "final_state.npz") as b:
            delta = float(np.max(np.abs(a["state"] - b["state"])))
        if delta <= 0:
            raise RuntimeError("q_aa did not change actual trajectory")
        effects[left + "_vs_" + right] = {"status": "PASS", "same_grid_time_initialization": True, "final_state_max_abs_difference": delta}
    write_json(WORKSPACE_ROOT / "docs/v2", "p2_source_equivalence.json", {"status": "PASS", "source_equivalence": checks, "q_aa_effect": effects})
    print(json.dumps({"status": "PASS", "q_aa_effect": effects, "run_ids": {name: run.run_id for name, run in runs.items()}}))


if __name__ == "__main__":
    main()
