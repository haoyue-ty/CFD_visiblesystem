"""P2 standalone adapter; Flask never imports the scientific solver."""
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from backend.core.settings import WORKSPACE_ROOT
from backend.models.v2.experiment import ValidateExperimentRequest
from backend.services.v2.experiments import validate_experiment
from backend.solver_runtime.artifacts import utc_now, write_json
from backend.solver_runtime.paths import run_directory

MANIFEST = WORKSPACE_ROOT / "docs/v2/source_manifest_p2.json"


def worker_environment(root: Path):
    env = os.environ.copy()
    # No secret is needed to compute CFD; do not propagate AI credentials.
    for key in list(env):
        if any(word in key.upper() for word in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")):
            env.pop(key)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(WORKSPACE_ROOT),
                "TEMP": str(root / "tmp"), "TMP": str(root / "tmp"), "TMPDIR": str(root / "tmp"),
                "MPLCONFIGDIR": str(root / "cache/matplotlib"), "XDG_CACHE_HOME": str(root / "cache"),
                "MPLBACKEND": "Agg", "HOME": str(root / "cache"), "USERPROFILE": str(root / "cache"),
                "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
    return env


@dataclass(frozen=True)
class PreparedRun:
    run_id: str
    directory: Path


class Case8SolverAdapter:
    def validate_config(self, request: ValidateExperimentRequest):
        return validate_experiment(request)

    def prepare_run(self, request: ValidateExperimentRequest, *, smoke_steps: int | None = None) -> PreparedRun:
        validated = self.validate_config(request)
        if smoke_steps is not None and (type(smoke_steps) is not int or not 2 <= smoke_steps <= 5):
            raise ValueError("Smoke certification requires 2..5 steps")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        run_id = str(uuid4())
        directory = run_directory(run_id, Path(manifest["source_root"]))
        directory.mkdir(parents=True, exist_ok=False)
        write_json(directory, "config.json", validated.model_dump(mode="json"))
        write_json(directory, "request.json", request.model_dump(mode="json"))
        write_json(directory, "execution.json", {"smoke_steps": smoke_steps})
        write_json(directory, "status.json", {"run_id": run_id, "status": "PREPARED", "created_at": utc_now(),
                                              "run_kind": "SMOKE" if smoke_steps else "FULL", "completed_steps": 0})
        return PreparedRun(run_id, directory)

    def execute(self, run: PreparedRun, *, timeout_seconds: float = 1800):
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("Worker timeout must be finite and positive")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        root = run_directory(run.run_id, Path(manifest["source_root"]))
        if root != run.directory or not root.is_dir():
            raise ValueError("Run directory identity mismatch")
        if json.loads((root / "status.json").read_text(encoding="utf-8"))["status"] != "PREPARED":
            raise ValueError("Each run can execute only once; prepare a new identity")
        for name in ("tmp", "cache"):
            from backend.solver_runtime.artifacts import target
            target(root, name + "/.owned").touch()
        env = worker_environment(root)
        from backend.solver_runtime.artifacts import target
        # Claim before spawning so two callers cannot race the same worker.
        target(root, "launch.claim").open("x", encoding="utf-8").close()
        with target(root, "solver.log").open("a", encoding="utf-8") as log:
            try:
                process = subprocess.Popen([sys.executable, "-B", "-m", "backend.solver_runtime.worker", "--run-id", run.run_id],
                                           cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
            except OSError:
                status = json.loads((root / "status.json").read_text(encoding="utf-8"))
                write_json(root, "status.json", {**status, "status": "FAILED", "finished_at": utc_now(), "failure": "WORKER_START_FAILED"})
                raise
            try:
                code = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
                else:
                    process.kill()
                process.wait()
                status = json.loads((root / "status.json").read_text(encoding="utf-8"))
                write_json(root, "status.json", {**status, "status": "FAILED", "finished_at": utc_now(), "failure": "WORKER_TIMEOUT"})
                raise RuntimeError(f"WORKER_TIMEOUT: {run.run_id}")
        status = json.loads((root / "status.json").read_text(encoding="utf-8"))
        if code or status["status"] not in ("COMPLETED", "SMOKE_COMPLETED"):
            if status["status"] != "FAILED":
                write_json(root, "status.json", {**status, "status": "FAILED", "finished_at": utc_now(), "failure": "WORKER_EXIT"})
            raise RuntimeError(f"Case8 worker failed: {run.run_id}; inspect solver.log")
        return self.postprocess(run)

    def postprocess(self, run: PreparedRun):
        """Read the worker's verified deterministic artifacts; no fallback to V1."""
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        root = run_directory(run.run_id, Path(manifest["source_root"]))
        if root != run.directory:
            raise ValueError("Run directory identity mismatch")
        from backend.solver_runtime.artifacts import sha256, target
        status = json.loads(target(root, "status.json").read_text(encoding="utf-8"))
        if status["status"] not in ("COMPLETED", "SMOKE_COMPLETED"):
            raise ValueError("Run has no completed result")
        provenance = json.loads(target(root, "provenance.json").read_text(encoding="utf-8"))
        for row in provenance["outputs"]:
            if sha256(target(root, row["path"])) != row["sha256"]:
                raise RuntimeError(f"RUN_OUTPUT_DRIFT: {row['path']}")
        scientific_path = target(root, "scientific_result.json")
        if scientific_path.exists():
            from backend.models.v2.result import ScientificRunResult
            from backend.postprocess.case8 import content_hash
            scientific = ScientificRunResult.model_validate_json(scientific_path.read_text(encoding="utf-8"))
            if scientific.identity.run_id != run.run_id or content_hash(scientific.model_dump(mode="json")) != scientific.result_hash:
                raise RuntimeError("SCIENTIFIC_RESULT_IDENTITY_MISMATCH")
        return json.loads(target(root, "result.json").read_text(encoding="utf-8"))
