"""Boundary/identity/failure tests; real trajectories live in the P2 acceptance runner."""
from functools import partial
import importlib
import json
from pathlib import Path
import sys
import types

import numpy as np
import pytest

from backend.solver_runtime.artifacts import sha256, target, write_json
from backend.solver_runtime.binding import ScientificBinding
from backend.solver_runtime.case8_adapter import Case8SolverAdapter, PreparedRun, worker_environment
from backend.solver_runtime.paths import run_directory
from backend.solver_runtime.worker import build_timestep, validate_samples
from scripts.run_case8 import template_request


@pytest.fixture
def isolated_adapter(tmp_path, monkeypatch):
    import backend.solver_runtime.case8_adapter as adapter_module
    workspace, source = tmp_path / "workspace", tmp_path / "source"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"source_root": str(source)}), encoding="utf-8")
    monkeypatch.setattr(adapter_module, "MANIFEST", manifest)
    monkeypatch.setattr(adapter_module, "run_directory", partial(run_directory, workspace=workspace))
    return Case8SolverAdapter(), workspace, source


def test_same_config_creates_independent_runs(isolated_adapter):
    adapter, _, source = isolated_adapter
    a = adapter.prepare_run(template_request("case8.paper.B_u"))
    b = adapter.prepare_run(template_request("case8.paper.B_u"))
    assert a.run_id != b.run_id and a.directory != b.directory
    assert (a.directory / "config.json").read_bytes() == (b.directory / "config.json").read_bytes()
    assert not source.exists()
    assert not (a.directory / "final_state.npz").exists()


def test_worker_environment_is_run_local_and_secret_free(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-secret")
    monkeypatch.setenv("SOME_TOKEN", "fixture-token")
    env = worker_environment(tmp_path)
    assert "DEEPSEEK_API_KEY" not in env and "SOME_TOKEN" not in env
    for key in ("TEMP", "TMP", "TMPDIR", "MPLCONFIGDIR", "HOME", "USERPROFILE", "XDG_CACHE_HOME"):
        assert Path(env[key]).is_relative_to(tmp_path)
    assert env["PYTHONDONTWRITEBYTECODE"] == "1" and env["OPENBLAS_NUM_THREADS"] == "1"


@pytest.mark.parametrize("steps", [0, 1, 6, -1, True, 3.0])
def test_invalid_smoke_never_creates_runtime(isolated_adapter, steps):
    adapter, workspace, _ = isolated_adapter
    with pytest.raises(ValueError):
        adapter.prepare_run(template_request("case8.fast.D_u"), smoke_steps=steps)
    assert not workspace.exists()


def test_unsupported_config_never_creates_runtime(isolated_adapter):
    adapter, workspace, _ = isolated_adapter
    request = template_request("case8.fast.D_u")
    request.config.physics.mach = 7.0
    with pytest.raises(Exception, match="未支持"):
        adapter.prepare_run(request)
    assert not workspace.exists()


def test_partial_run_is_explicit(isolated_adapter):
    adapter, _, _ = isolated_adapter
    run = adapter.prepare_run(template_request("case8.paper.D_u"), smoke_steps=3)
    status = json.loads((run.directory / "status.json").read_text(encoding="utf-8"))
    assert status["run_kind"] == "SMOKE" and status["completed_steps"] == 0


def test_result_is_unavailable_before_completion(isolated_adapter):
    adapter, _, _ = isolated_adapter
    run = adapter.prepare_run(template_request("case8.fast.D_u"))
    with pytest.raises(ValueError, match="completed result"):
        adapter.postprocess(run)


def test_output_tampering_rejected(isolated_adapter):
    adapter, _, _ = isolated_adapter
    run = adapter.prepare_run(template_request("case8.fast.D_u"))
    write_json(run.directory, "result.json", {"value": 1})
    write_json(run.directory, "provenance.json", {"outputs": [{"path": "result.json", "sha256": sha256(run.directory / "result.json")}]})
    write_json(run.directory, "status.json", {"status": "COMPLETED"})
    assert adapter.postprocess(run) == {"value": 1}
    write_json(run.directory, "result.json", {"value": 2})
    with pytest.raises(RuntimeError, match="OUTPUT_DRIFT"):
        adapter.postprocess(run)


def test_completed_run_cannot_reexecute(isolated_adapter):
    adapter, _, _ = isolated_adapter
    run = adapter.prepare_run(template_request("case8.fast.D_u"))
    write_json(run.directory, "status.json", {"status": "COMPLETED"})
    with pytest.raises(ValueError, match="only once"):
        adapter.execute(run)


def test_forged_run_directory_rejected(isolated_adapter):
    adapter, workspace, _ = isolated_adapter
    run = adapter.prepare_run(template_request("case8.fast.D_u"))
    with pytest.raises(ValueError, match="identity mismatch"):
        adapter.execute(PreparedRun(run.run_id, workspace))


def test_failed_worker_does_not_retry_or_return_reference(isolated_adapter, monkeypatch):
    import backend.solver_runtime.case8_adapter as module
    adapter, _, _ = isolated_adapter
    run = adapter.prepare_run(template_request("case8.fast.D_u"))
    before = (run.directory / "config.json").read_bytes()
    launches = []

    def failed_process(*args, **kwargs):
        launches.append(args)
        return types.SimpleNamespace(wait=lambda timeout: 1)

    monkeypatch.setattr(module.subprocess, "Popen", failed_process)
    with pytest.raises(RuntimeError, match="worker failed"):
        adapter.execute(run)
    status = json.loads((run.directory / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "FAILED" and status["failure"] == "WORKER_EXIT"
    assert len(launches) == 1
    assert (run.directory / "config.json").read_bytes() == before
    assert not (run.directory / "final_state.npz").exists()


def test_start_failure_is_persisted(isolated_adapter, monkeypatch):
    import backend.solver_runtime.case8_adapter as module
    adapter, _, _ = isolated_adapter
    run = adapter.prepare_run(template_request("case8.fast.D_u"))

    def cannot_start(*args, **kwargs):
        raise OSError("test spawn failed")

    monkeypatch.setattr(module.subprocess, "Popen", cannot_start)
    with pytest.raises(OSError, match="spawn failed"):
        adapter.execute(run)
    status = json.loads((run.directory / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "FAILED" and status["failure"] == "WORKER_START_FAILED"


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout_rejected_before_execution(isolated_adapter, timeout):
    adapter, _, _ = isolated_adapter
    run = adapter.prepare_run(template_request("case8.fast.D_u"))
    with pytest.raises(ValueError, match="timeout"):
        adapter.execute(run, timeout_seconds=timeout)
    assert not (run.directory / "solver.log").exists()


@pytest.mark.parametrize("relative", ["../outside.json", "nested/../../outside.json", "/outside.json"])
def test_artifact_escape_rejected(tmp_path, relative):
    with pytest.raises(ValueError):
        write_json(tmp_path, relative, {"x": 1})


def test_internal_linked_subdirectory_rejected(tmp_path):
    nested = tmp_path / "linked"
    actual = tmp_path / "real"
    actual.mkdir()
    if sys.platform == "win32":
        import subprocess
        import os
        subprocess.run(["pwsh", "-NoProfile", "-Command", "New-Item -ItemType Junction -Path $env:SP_LINK -Target $env:SP_TARGET -ErrorAction Stop | Out-Null"],
                       env=os.environ | {"SP_LINK": str(nested), "SP_TARGET": str(actual)}, check=True, capture_output=True)
    else:
        nested.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="Linked"):
        target(tmp_path, "linked/result.json")
    assert not (actual / "result.json").exists()


@pytest.fixture
def binding(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    source = root / "fake_science.py"
    source.write_text("VALUE = 42\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"source_root": str(root), "selection": {"fake_science": ""},
                                    "files": [{"module": "fake_science", "path": "fake_science.py", "sha256": sha256(source)}]}), encoding="utf-8")
    return ScientificBinding(manifest)


def test_drift_before_import_rejected(binding):
    (binding.root / "fake_science.py").write_text("VALUE = 43\n", encoding="utf-8")
    with pytest.raises(ImportError, match="SOURCE_DRIFT"):
        binding.find_spec("fake_science")


def test_unregistered_submodule_cannot_import(binding):
    with pytest.raises(ImportError, match="UNREGISTERED"):
        binding.find_spec("fake_science.hidden")


def test_loaded_wrong_module_rejected(binding, monkeypatch, tmp_path):
    module = types.ModuleType("fake_science")
    module.__file__ = str(tmp_path / "imposter.py")
    Path(module.__file__).write_text("VALUE = 42\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "fake_science", module)
    with pytest.raises(RuntimeError, match="IDENTITY_MISMATCH"):
        binding.loaded_modules()
    with pytest.raises(RuntimeError, match="before binding"):
        binding.install()


def test_hash_locked_import_does_not_create_bytecode(binding):
    binding.install()
    try:
        module = importlib.import_module("fake_science")
        assert module.VALUE == 42
        assert binding.loaded_modules()[0]["path"] == "fake_science.py"
        assert not (binding.root / "__pycache__").exists()
    finally:
        sys.modules.pop("fake_science", None)
        sys.meta_path.remove(binding)


def test_existing_bytecode_cannot_override_locked_source(binding):
    # -B only blocks writes. A timestamp-valid but incorrect old cache must
    # never be executed in place of the bytes whose SHA-256 was registered.
    from importlib._bootstrap_external import _code_to_timestamp_pyc
    source = binding.root / "fake_science.py"
    cached = Path(importlib.util.cache_from_source(str(source)))
    cached.parent.mkdir()
    wrong_code = compile("VALUE = 99\n", str(source), "exec")
    cached.write_bytes(_code_to_timestamp_pyc(wrong_code, int(source.stat().st_mtime), source.stat().st_size))
    cached_hash = sha256(cached)
    binding.install()
    try:
        assert importlib.import_module("fake_science").VALUE == 42
        assert sha256(cached) == cached_hash
    finally:
        sys.modules.pop("fake_science", None)
        sys.meta_path.remove(binding)


def test_missing_bytecode_guard_rejected(binding, monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    with pytest.raises(RuntimeError, match="Python -B"):
        binding.install()


def test_dynamic_timestep_uses_grid_and_final_time():
    # Uniform rho=1, u=2, v=0, sound speed=1; expected rate=3/dx+1/dy.
    state = np.array([[[1.0, 2.0, 0.0, 5.0]]])
    setup = types.SimpleNamespace(mesh=types.SimpleNamespace(dx=1 / 64, dy=1 / 16), state=state, gas=None)
    config = template_request("case8.fast.D_u").config
    protocol = build_timestep(setup, config, lambda state, gas: np.ones(state.shape[:-1]))
    assert protocol["initial_wave_rate"] == 208
    assert protocol["steps"] == 167 and protocol["dt"] == .04 / 167
    setup.mesh = types.SimpleNamespace(dx=1 / 128, dy=1 / 32)
    config.time.final_time = .08
    other = build_timestep(setup, config, lambda state, gas: np.ones(state.shape[:-1]))
    assert other["steps"] == 666 and other["dt"] == .08 / 666
    assert other["checkpoint_steps"][-1] == 666


def stage_sample():
    return {"dotE_bg": 1.0, "dotE_aa": 2.0, "dotE_at": 0.0, "dotE_total": 3.0,
            "dotE_additivity_abs_error": 0.0, "pi_at_max": 0.0}


@pytest.mark.parametrize("key,value,error", [("dotE_at", 1e-5, "ZERO_CHANNEL"),
                                              ("pi_at_max", 1e-5, "ZERO_CHANNEL"),
                                              ("dotE_bg", -1.0, "NEGATIVE"),
                                              ("dotE_bg", float("nan"), "NONFINITE"),
                                              ("dotE_additivity_abs_error", 1e-5, "ADDITIVITY")])
def test_diagnostics_fail_without_configuration_recovery(key, value, error):
    sample = stage_sample()
    sample[key] = value
    with pytest.raises(RuntimeError, match=error):
        validate_samples((sample,) * 3, 0.0)


def test_diagnostic_stage_count_guard():
    with pytest.raises(RuntimeError, match="STAGE_COUNT"):
        validate_samples((stage_sample(),) * 2, 0.0)
    validate_samples((stage_sample(),) * 3, 0.0)
