"""Fixed Case8 child-process entry. Every scientific write stays in one new run."""
import argparse
import ctypes
from ctypes import wintypes
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import sys
from time import perf_counter
import traceback

import numpy as np

from backend.core.settings import WORKSPACE_ROOT
from backend.models.v2.experiment import ValidateExperimentRequest
from backend.solver_runtime.artifacts import output_inventory, sha256, target, utc_now, write_json
from backend.solver_runtime.binding import ScientificBinding
from backend.solver_runtime.case8_adapter import MANIFEST
from backend.solver_runtime.paths import run_directory
from backend.services.v2.experiments import validate_experiment

CHANNELS = ("bg", "aa", "at", "total")
RK_WEIGHTS = (1.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0)


def peak_rss_bytes():
    if os.name != "nt":
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                               "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                                               "PagefileUsage", "PeakPagefileUsage")]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    api = ctypes.WinDLL("psapi", use_last_error=True)
    api.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not api.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.PeakWorkingSetSize)


def json_value(value):
    if isinstance(value, np.ndarray):
        return json_value(value.tolist())
    if isinstance(value, np.generic):
        return json_value(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    return value


def build_timestep(setup, config, sound_speed):
    mesh, state = setup.mesh, setup.state
    acoustic = sound_speed(state, setup.gas)
    rate = float(np.max(np.abs(state[..., 1] / state[..., 0]) / mesh.dx
                        + np.abs(state[..., 2] / state[..., 0]) / mesh.dy
                        + acoustic / mesh.dx + acoustic / mesh.dy))
    raw_dt = config.time.cfl / rate
    steps = int(np.ceil(config.time.final_time / raw_dt))
    dt = config.time.final_time / steps
    if not math.isfinite(dt) or dt <= 0 or steps > 10000:
        raise ValueError("INVALID_STEP_PROTOCOL")
    checkpoints = sorted({int(round(f * steps)) for f in config.output.checkpoint_fractions})
    return {"initial_wave_rate": rate, "raw_dt": raw_dt, "dt": dt, "steps": steps,
            "checkpoint_steps": checkpoints, "checkpoint_times": [step * dt for step in checkpoints]}


def validate_samples(samples, q_at):
    if len(samples) != 3:
        raise RuntimeError("DIAGNOSTIC_STAGE_COUNT")
    for sample in samples:
        if any(not math.isfinite(float(value)) for value in sample.values()):
            raise RuntimeError("NONFINITE_DIAGNOSTICS")
        if sample["dotE_additivity_abs_error"] > 3.0e-11:
            raise RuntimeError("DIAGNOSTIC_ADDITIVITY")
        if any(sample[f"dotE_{channel}"] < -3.0e-13 for channel in CHANNELS):
            raise RuntimeError("NEGATIVE_CHANNEL_RATE")
        if q_at == 0 and (abs(sample["dotE_at"]) > 3.0e-13 or abs(sample["pi_at_max"]) > 3.0e-13):
            raise RuntimeError("QAT_ZERO_CHANNEL_IDENTITY")


def compute(root: Path, status, *, binding: ScientificBinding):
    started = perf_counter()
    wrapper_files = [Path(__file__), WORKSPACE_ROOT / "backend/solver_runtime/case8_adapter.py",
                     WORKSPACE_ROOT / "backend/solver_runtime/binding.py", WORKSPACE_ROOT / "backend/solver_runtime/artifacts.py",
                     WORKSPACE_ROOT / "backend/solver_runtime/paths.py", WORKSPACE_ROOT / "backend/services/v2/experiments.py",
                     WORKSPACE_ROOT / "backend/registry/v2/cases.py", WORKSPACE_ROOT / "backend/models/v2/experiment.py"]
    wrapper_files.append(WORKSPACE_ROOT / "backend/solver_runtime/processes.py")
    wrapper_files.extend(WORKSPACE_ROOT / name for name in (
        "backend/postprocess/case8.py", "backend/postprocess/allocation.py", "backend/models/v2/result.py"))
    software = [{"path": p.relative_to(WORKSPACE_ROOT).as_posix(), "sha256": sha256(p)} for p in wrapper_files]
    manifest_hash = sha256(MANIFEST)
    request = ValidateExperimentRequest.model_validate_json(target(root, "request.json").read_text(encoding="utf-8"))
    validated = validate_experiment(request)
    saved = json.loads(target(root, "config.json").read_text(encoding="utf-8"))
    if validated.model_dump(mode="json") != saved:
        raise RuntimeError("RUN_CONFIG_IDENTITY_MISMATCH")
    config = validated.normalized_config
    smoke_steps = json.loads(target(root, "execution.json").read_text(encoding="utf-8"))["smoke_steps"]
    if smoke_steps is not None and (type(smoke_steps) is not int or not 2 <= smoke_steps <= 5):
        raise ValueError("Invalid smoke step limit")
    binding.install()
    from solver.cases import flagship_cross_modal_case8 as source_case
    from solver.core.euler import IdealGas, sound_speed, assert_physical
    from solver.core.finite_volume import finite_volume_rhs
    from solver.fluxes.cross_mode_ec_unified_v1 import cross_mode_ec_unified_flux
    from case8_entropy_observer import Case8EntropyObserver
    from case8_j2_driver import source_equivalent_ssprk3_step, _history_row, _hash_state
    from solver.experiments.baseline_case8_production import checkpoint_diagnostics

    # All fixed initialization fields are explicitly checked against the imported
    # source, then its one authoritative constructor receives grid and gas.
    constants = {"mach": source_case.MACH, "front_center": source_case.SHOCK_POSITION,
                 "corrugation_amplitude": source_case.CORRUGATION_AMPLITUDE, "wavelength_count": source_case.MODE,
                 "transition_cells": source_case.SHOCK_SMOOTHING_CELLS,
                 "transverse_seed_sound_speed_factor": source_case.TANGENTIAL_AMPLITUDE_FACTOR,
                 "transverse_seed_width": source_case.TANGENTIAL_ENVELOPE_WIDTH,
                 "transverse_seed_phase": source_case.PHASE}
    requested = {"mach": config.physics.mach, **config.physics.initial_condition.model_dump(exclude={"base"})}
    if requested != constants or tuple(config.grid.domain.x) != source_case.XLIM or tuple(config.grid.domain.y) != source_case.YLIM:
        raise RuntimeError("INITIALIZATION_PROTOCOL_MISMATCH")
    setup = source_case.initial_setup(n=config.grid.nx, ny=config.grid.ny, gas=IdealGas(config.physics.gamma))
    timestep = build_timestep(setup, config, sound_speed)
    dt, planned_steps = timestep["dt"], timestep["steps"]
    paper_match = validated.classification == "LIVE_PAPER_PROFILE"
    if paper_match:
        locked = source_case.locked_protocol(n=config.grid.nx, ny=config.grid.ny, gas=setup.gas)
        protocol_row = next(row for row in binding.manifest["files"] if row["role"] == "protocol")
        protocol = json.loads((binding.root / protocol_row["path"]).read_text(encoding="utf-8"))
        if (dt != locked["dt"] or dt != protocol["dt"] or planned_steps != protocol["accepted_step_expectation"]
                or timestep["checkpoint_steps"] != protocol["snapshot_steps"]):
            raise RuntimeError("PAPER_STEP_PROTOCOL_MISMATCH")
    steps = smoke_steps or planned_steps
    aa, at = config.method.q_aa, config.method.q_at
    calls = {"rhs": 0, "flux": 0, "q_aa": aa, "q_at": at, "observed_shapes": []}

    def flux(left, right, normal, gas):
        calls["flux"] += 1
        if calls["flux"] <= 2:
            calls["observed_shapes"].append({"left": list(left.shape), "right": list(right.shape), "normal": normal.tolist()})
        return cross_mode_ec_unified_flux(left, right, normal, gas, q_aa=aa, q_at=at)

    def rhs(candidate):
        calls["rhs"] += 1
        return finite_volume_rhs(candidate, setup.mesh, setup.boundaries, flux, setup.gas)

    from backend.postprocess.allocation import allocation_observer
    observer = allocation_observer(Case8EntropyObserver, setup, q_aa=aa, q_at=at, dt=dt)
    binding.loaded_modules()
    effective = {"adapter_version": "case8.adapter.p2.1", "normalized_config": config.model_dump(mode="json"),
                 "initialization": constants, "initial_state_hash": _hash_state(setup.state),
                 "upstream_primitive": setup.pre.tolist(), "downstream_primitive": setup.post.tolist(),
                 "tangential_amplitude": setup.tangential_amplitude, "rh_residual": setup.rh_residual,
                 "grid": {"nx": setup.mesh.nx, "ny": setup.mesh.ny, "dx": setup.mesh.dx, "dy": setup.mesh.dy},
                 "time": {**timestep, "requested_final_time": config.time.final_time, "executed_steps": steps,
                          "executed_final_time": steps * dt, "paper_protocol_match": paper_match},
                 "flux": {"module": cross_mode_ec_unified_flux.__module__, "q_aa": aa, "q_at": at},
                 "observer": {"q_aa": observer.q_aa, "q_at": observer.q_at, "rk_weights": list(RK_WEIGHTS),
                              "face_audit": observer.face_audit, "scope": "all unique residual faces including x boundaries; periodic y seam once"},
                 "integrator": "case8_j2_driver.source_equivalent_ssprk3_step (source stage guards 0/1/2/3)",
                 "recovery_policy": "none: no retry, CFL change, clipping, viscosity or configuration substitution"}
    write_json(root, "effective_solver_config.json", effective)
    write_json(root, "software_identity.json", {"software": software, "source_manifest_sha256": manifest_hash})
    state = np.array(setup.state, copy=True)
    np.savez_compressed(target(root, "initial_state.npz"), state=state, x=source_case._coordinates(setup.mesh)[0], y=setup.y)
    checkpoint_steps = set(timestep["checkpoint_steps"]) & set(range(steps + 1))
    checkpoint_steps.update((0, steps))
    snapshots = []

    def snapshot(step):
        faces = observer.snapshot(state)
        arrays = {f"{axis}_{key}": value for axis, fields in faces.items() for key, value in fields.items()}
        relative = f"snapshots/step_{step:06d}.npz"
        np.savez_compressed(target(root, relative), state=state, **arrays, step=step, time=step * dt)
        snapshots.append({"step": step, "time": step * dt, "path": relative, "cell_shape": list(state.shape),
                          "x_faces_shape": list(faces["x_faces"]["pi_at"].shape),
                          "y_faces_shape": list(faces["y_faces"]["pi_at"].shape)})

    snapshot(0)
    status.update(status="RUNNING", started_at=utc_now(), planned_steps=planned_steps, target_steps=steps,
                  physical_time=0.0, requested_final_time=config.time.final_time)
    write_json(root, "status.json", status)
    cumulative = {f"E_{channel}": 0.0 for channel in CHANNELS}
    max_error = 0.0
    solver_started = perf_counter()
    with target(root, "diagnostics/history.jsonl").open("x", encoding="utf-8") as history:
        for step in range(steps):
            manager_identity = os.environ.get("SHOCKPATH_MANAGER_IDENTITY")
            if manager_identity:
                from backend.solver_runtime.processes import process_identity
                manager_pid = int(manager_identity.split(":")[0])
                if process_identity(manager_pid) != manager_identity:
                    raise RuntimeError("WORKER_INTERRUPTED")
            state, samples = source_equivalent_ssprk3_step(state, rhs, setup.gas, dt, step * dt, observer=observer)
            validate_samples(samples, at)
            max_error = max(max_error, *(float(s["dotE_additivity_abs_error"]) for s in samples))
            row = _history_row(step, step * dt, dt, samples, cumulative)
            history.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            completed = step + 1
            if completed in checkpoint_steps:
                snapshot(completed)
            if completed % 50 == 0 or completed == steps:
                history.flush()
                status.update(completed_steps=completed, physical_time=completed * dt)
                write_json(root, "status.json", status)
                print(f"step={completed}/{steps} t={completed * dt:.12g}", flush=True)
    solver_seconds = perf_counter() - solver_started
    calls["evolution_flux_calls"] = calls["flux"]
    status.update(status="POSTPROCESSING")
    write_json(root, "status.json", status)
    assert_physical(state, setup.gas)
    physical, arrays = checkpoint_diagnostics(state, setup, flux, step=steps, time=steps * dt)
    if not physical["finite"] or not physical["diagnostics_available"]:
        raise RuntimeError("INVALID_FINAL_DIAGNOSTICS")
    np.savez_compressed(target(root, "final_state.npz"), state=state, accepted_steps=steps, time=steps * dt)
    np.savez_compressed(target(root, "derived/physical_fields.npz"), **arrays)
    if observer.stage_count != 3 * steps:
        raise RuntimeError("ALLOCATION_STAGE_COUNT_MISMATCH")
    np.savez_compressed(target(root, "derived/cumulative_faces.npz"), **observer.cumulative_faces)
    write_json(root, "diagnostics/physical_metrics.json", json_value(physical))
    write_json(root, "snapshots/index.json", snapshots)
    result = {"run_id": status["run_id"], "run_kind": status["run_kind"], "config_hash": validated.config_hash,
              "classification": validated.classification, "data_origin": "V2_LIVE_COMPUTATION",
              "verification": "P2_NUMERICAL_CHECKS_PASSED", "full_requested_interval_completed": smoke_steps is None,
              "started_at": status["started_at"], "finished_at": utc_now(), "accepted_steps": steps, "rejected_steps": 0,
              "dt": dt, "final_time": steps * dt, "initial_state_hash": effective["initial_state_hash"],
              "final_state_hash": _hash_state(state), "channel_totals": cumulative, "max_additivity_abs_error": max_error,
              "qat_zero_identity": "PASS" if at == 0 else "NOT_APPLICABLE", "physical_metrics": json_value(physical),
              "unavailable_metrics": [key for key, value in physical.items() if isinstance(value, float) and not math.isfinite(value)],
              "runtime": {"wall_seconds": perf_counter() - started, "solver_seconds": solver_seconds,
                          "peak_rss_bytes": peak_rss_bytes(), "python": sys.version, "platform": platform.platform(),
                          "processor": platform.processor(), "logical_cpus": os.cpu_count(),
                          "packages": {name: version(name) for name in ("numpy", "scipy", "matplotlib", "PyYAML")}},
              "actual_calls": calls,
              "limitations": ["V2 live computation with independent run identity; no inherited historical freeze.",
                              "No universal stability or optimal-coefficient claim.",
                              "Instantaneous native-face snapshots are not trajectory-integrated spatial allocation."]}
    if calls["rhs"] != 3 * steps or calls["evolution_flux_calls"] != 6 * steps:
        raise RuntimeError("RHS_CALL_COUNT_MISMATCH")
    write_json(root, "result.json", result)
    from backend.postprocess.case8 import build_result
    provisional_provenance = {"source_manifest_revision": binding.manifest["manifest_version"],
                              "source_manifest_sha256": manifest_hash, "loaded_modules": binding.loaded_modules(),
                              "software": software, "outputs": output_inventory(root)}
    scientific_result = build_result(root, provisional_provenance)
    write_json(root, "scientific_result.json", scientific_result.model_dump(mode="json"))
    outputs = output_inventory(root)
    if software != [{"path": p.relative_to(WORKSPACE_ROOT).as_posix(), "sha256": sha256(p)} for p in wrapper_files] or sha256(MANIFEST) != manifest_hash:
        raise RuntimeError("SOFTWARE_IDENTITY_DRIFT_DURING_RUN")
    write_json(root, "provenance.json", {"run_id": status["run_id"], "source_manifest_revision": binding.manifest["manifest_version"],
                                        "source_manifest_sha256": manifest_hash, "loaded_modules": binding.loaded_modules(),
                                        "software": software,
                                        "outputs": outputs, "result_sha256": sha256(root / "result.json"),
                                        "output_bytes": sum(row["size"] for row in outputs)})
    status.update(status="SMOKE_COMPLETED" if smoke_steps else "COMPLETED", finished_at=result["finished_at"])
    write_json(root, "status.json", status)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    root = run_directory(args.run_id, Path(manifest["source_root"]))
    if Path.cwd().resolve() != root or not sys.dont_write_bytecode:
        raise RuntimeError("Worker requires run-local cwd and Python -B")
    # Permanent exclusive claim prevents duplicate workers from evolving a run.
    with target(root, "worker.claim").open("x", encoding="utf-8") as claim:
        claim.write(str(os.getpid()))
    status = json.loads(target(root, "status.json").read_text(encoding="utf-8"))
    try:
        if status["status"] != "PREPARED":
            raise RuntimeError("RUN_ALREADY_STARTED")
        from backend.solver_runtime.processes import process_identity
        status.update(status="STARTING", worker_pid=os.getpid(), worker_identity=process_identity(os.getpid()))
        write_json(root, "status.json", status)
        compute(root, status, binding=ScientificBinding(MANIFEST))
    except Exception as error:
        status.update(status="FAILED", finished_at=utc_now(), failure=type(error).__name__, message=str(error))
        write_json(root, "status.json", status)
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
