"""Read-only source-step equivalence and independent RK-weight audit of a smoke Run.

Invoke from that run's cwd with the same isolated cache environment as the worker.
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np

from backend.solver_runtime.artifacts import sha256
from backend.solver_runtime.binding import ScientificBinding
from backend.solver_runtime.case8_adapter import MANIFEST
from backend.solver_runtime.paths import run_directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    binding = ScientificBinding(MANIFEST)
    root = run_directory(args.run_id, binding.root)
    if Path.cwd().resolve() != root or not Path(os.environ["MPLCONFIGDIR"]).resolve().is_relative_to(root):
        raise RuntimeError("Equivalence verifier requires run-local cwd/cache")
    result = json.loads((root / "result.json").read_text(encoding="utf-8"))
    if result["run_kind"] != "SMOKE" or result["accepted_steps"] > 5:
        raise ValueError("Equivalence verifier only accepts a smoke Run")
    effective = json.loads((root / "effective_solver_config.json").read_text(encoding="utf-8"))
    binding.install()
    from solver.cases.flagship_cross_modal_case8 import initial_setup
    from solver.core.explicit_ssprk import advance_ssprk3_step, Ssprk3StepFailure
    from solver.core.finite_volume import finite_volume_rhs
    from solver.fluxes.cross_mode_ec_unified_v1 import cross_mode_ec_unified_flux
    from solver.core.euler import IdealGas

    setup = initial_setup(n=effective["grid"]["nx"], ny=effective["grid"]["ny"],
                          gas=IdealGas(effective["normalized_config"]["physics"]["gamma"]))
    aa, at = effective["flux"]["q_aa"], effective["flux"]["q_at"]
    flux = lambda l, r, n, g: cross_mode_ec_unified_flux(l, r, n, g, q_aa=aa, q_at=at)
    rhs = lambda state: finite_volume_rhs(state, setup.mesh, setup.boundaries, flux, setup.gas)
    state = np.array(setup.state, copy=True)
    for step in range(result["accepted_steps"]):
        state = advance_ssprk3_step(state, rhs, setup.gas, result["dt"], step * result["dt"])
    with np.load(root / "final_state.npz") as data:
        observed_state = data["state"]
    if not np.array_equal(state, observed_state):
        raise RuntimeError("Observer trajectory differs from direct source SSP-RK3")
    invalid = state.copy()
    invalid[0, 0, 0] = -1
    try:
        advance_ssprk3_step(invalid, rhs, setup.gas, result["dt"], 0.0)
    except Ssprk3StepFailure:
        stage_guard = "PASS"
    else:
        raise RuntimeError("Invalid initial state bypassed source stage guard")
    cumulative = {channel: 0.0 for channel in ("bg", "aa", "at", "total")}
    max_weight_error = 0.0
    for line in (root / "diagnostics/history.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        for channel in cumulative:
            increment = row["dt"] * (row[f"dotE_{channel}_s0"] / 6 + row[f"dotE_{channel}_s1"] / 6 + 2 * row[f"dotE_{channel}_s2"] / 3)
            cumulative[channel] += increment
            error = max(abs(increment - row[f"deltaE_{channel}"]), abs(cumulative[channel] - row[f"E_{channel}"]))
            if error > 1e-12:
                raise RuntimeError("RK history weighting mismatch")
            max_weight_error = max(max_weight_error, error)
    print(json.dumps({"status": "PASS", "run_id": args.run_id, "source_ssprk3_state_equivalence": "BITWISE",
                      "invalid_state_guard": stage_guard, "rk_history_max_abs_error": max_weight_error,
                      "result_sha256": sha256(root / "result.json"), "loaded_modules": binding.loaded_modules()}))


if __name__ == "__main__":
    main()
