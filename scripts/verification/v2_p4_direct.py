"""Independent locked-source final detector/Euler comparison, run-local process."""
import argparse
import json
from pathlib import Path

import numpy as np

from backend.solver_runtime.binding import ScientificBinding
from backend.solver_runtime.case8_adapter import MANIFEST
from backend.solver_runtime.paths import run_directory
from backend.postprocess.case8 import primitive_fields


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    binding = ScientificBinding(MANIFEST)
    root = run_directory(args.run_id, binding.root)
    if Path.cwd().resolve() != root:
        raise ValueError("Direct verifier requires run-local cwd")
    binding.install()
    from solver.cases.flagship_cross_modal_case8 import initial_setup
    from solver.core.euler import IdealGas, pressure, conservative_to_primitive, sound_speed
    from solver.fluxes.cross_mode_ec_unified_v1 import cross_mode_ec_unified_flux
    from solver.experiments.baseline_case8_production import checkpoint_diagnostics
    effective = json.loads((root / "effective_solver_config.json").read_text())
    summary = json.loads((root / "result.json").read_text())
    config = effective["normalized_config"]
    gas = IdealGas(config["physics"]["gamma"])
    setup = initial_setup(n=config["grid"]["nx"], ny=config["grid"]["ny"], gas=gas)
    errors = {}
    snapshots = json.loads((root / "snapshots/index.json").read_text())
    for row in snapshots:
        with np.load(root / row["path"], allow_pickle=False) as data:
            state = data["state"]
        own = primitive_fields(state, gas.gamma)
        primitive = conservative_to_primitive(state, gas)
        speed = np.sqrt(primitive[..., 1]**2 + primitive[..., 2]**2)
        direct = dict(density=primitive[..., 0], pressure=pressure(state, gas), velocity_x=primitive[..., 1],
                      velocity_y=primitive[..., 2], speed=speed, mach=speed/sound_speed(state, gas))
        for key in own:
            np.testing.assert_allclose(own[key], direct[key], rtol=2e-14, atol=2e-14)
            errors[key] = max(errors.get(key, 0), float(np.max(np.abs(own[key]-direct[key]))))
    with np.load(root / "final_state.npz", allow_pickle=False) as data:
        state = data["state"]
    method = config["method"]
    flux = lambda l, r, n, g: cross_mode_ec_unified_flux(l, r, n, g, q_aa=method["q_aa"], q_at=method["q_at"])
    direct_metrics, _ = checkpoint_diagnostics(state, setup, flux, step=summary["accepted_steps"], time=summary["final_time"])
    metric_errors = {}
    for key in ("front_width_mean", "front_rms", "front_high_k_fraction"):
        assert direct_metrics[key] == summary["physical_metrics"][key]
        metric_errors[key] = 0.
    print(json.dumps(dict(status="PASS", run_id=args.run_id, field_max_abs_errors=errors, metric_abs_errors=metric_errors,
                         snapshots_compared=len(snapshots), loaded_modules=binding.loaded_modules())))


if __name__ == "__main__":
    main()
