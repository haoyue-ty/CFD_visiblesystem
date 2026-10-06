"""Explicit single-leader daemon. App factories and exports never start it."""
import json
import os
import subprocess
import sys
import time

from backend.core.settings import Settings
from backend.solver_runtime.artifacts import target, utc_now, write_json
from backend.solver_runtime.case8_adapter import PreparedRun, worker_environment
from backend.solver_runtime.processes import process_identity, terminate_worker
from backend.solver_runtime.run_store import ACTIVE, TERMINAL, RunStore, file_lock


def directory_bytes(root):
    total = 0
    for path in root.rglob("*"):
        if path.name.endswith(".tmp"):
            continue
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            # Atomic worker commits may remove a transient name during enumeration.
            continue
    return total


class RunManager:
    def __init__(self, store):
        self.store = store
        self.identity = process_identity(os.getpid())
        from backend.services.v2.sweeps import SweepService
        self.sweeps = SweepService(store)

    def recover(self):
        # Queue survives; an interrupted numerical trajectory is never resumed.
        with self.store.transaction():
            self.store.recover_index()
            for run_id in self.store._index()["runs"]:
                record = self.store._record(run_id)
                if record.status in ACTIVE:
                    root = self.store.directory(run_id)
                    status_path = target(root, "status.json")
                    status = json.loads(status_path.read_text(encoding="utf-8"))
                    pid = record.worker_pid or status.get("worker_pid")
                    identity = record.worker_identity or status.get("worker_identity")
                    if pid:
                        terminate_worker(pid, identity)
                    record.status = "CANCELLED" if record.cancel_requested else "FAILED"
                    record.failure = None if record.cancel_requested else "WORKER_INTERRUPTED"
                    record.finished_at = utc_now()
                    self.store._commit(record)
                    write_json(root, "status.json", {**status, "status": record.status, "failure": record.failure})

    def execute(self, run_id):
        root = self.store.directory(run_id)
        process = None
        with target(root, "solver.log").open("a", encoding="utf-8") as log:
            try:
                with self.store.transaction():
                    record = self.store._record(run_id)
                    if record.status != "QUEUED":
                        return
                    record.status, record.started_at = "STARTING", utc_now()
                    record.manager_identity = self.identity
                    self.store._commit(record)
                    target(root, "launch.claim").open("x").close()
                    env = worker_environment(root)
                    env["SHOCKPATH_MANAGER_IDENTITY"] = self.identity
                    process = subprocess.Popen([sys.executable, "-B", "-m", "backend.solver_runtime.worker",
                                                "--run-id", run_id], cwd=root, env=env,
                                               stdout=log, stderr=subprocess.STDOUT)
                    record.worker_pid = process.pid
                    record.worker_identity = process_identity(process.pid)
                    self.store._commit(record)
                started = time.monotonic()
                while True:
                    self.store.heartbeat(self.identity)
                    self.sweeps.tick()
                    with self.store.transaction():
                        record = self.store._record(run_id)
                        status = json.loads(target(root, "status.json").read_text(encoding="utf-8"))
                        stopped = process.poll() is not None
                        failure = None
                        if record.cancel_requested:
                            failure = "CANCELLED"
                        elif time.monotonic() - started > self.store.settings.max_run_seconds:
                            failure = "WORKER_TIMEOUT"
                        elif directory_bytes(root) > self.store.settings.max_run_output_bytes:
                            failure = "RUN_OUTPUT_LIMIT"
                        if failure:
                            terminate_worker(process.pid, record.worker_identity)
                            process.wait(timeout=10)
                            record.status = "CANCELLED" if failure == "CANCELLED" else "FAILED"
                            record.failure = None if failure == "CANCELLED" else failure
                            record.finished_at = utc_now()
                            self.store._commit(record)
                            write_json(root, "status.json", {**status, "status": record.status, "failure": record.failure})
                            return
                        if not stopped:
                            changed = (status.get("completed_steps", 0) != record.completed_steps
                                       or status["status"] in ACTIVE and status["status"] != record.status)
                            if status["status"] in ACTIVE:
                                record.status = status["status"]
                            record.completed_steps = status.get("completed_steps", 0)
                            record.planned_steps = status.get("planned_steps")
                            record.physical_time = status.get("physical_time", 0.0)
                            record.heartbeat_at = utc_now()
                            self.store._commit(record, event=changed)
                    if stopped:
                        break
                    time.sleep(.25)
                if process.returncode != 0:
                    raise RuntimeError("WORKER_EXIT")
                with self.store.transaction():
                    record = self.store._record(run_id)
                    status = json.loads(target(root, "status.json").read_text(encoding="utf-8"))
                    record.completed_steps = status.get("completed_steps", record.completed_steps)
                    record.physical_time = status.get("physical_time", record.physical_time)
                    record.planned_steps = status.get("planned_steps", record.planned_steps)
                    if record.status == "STARTING":
                        record.status = "RUNNING"
                        self.store._commit(record)
                    record.status = "POSTPROCESSING"
                    self.store._commit(record)
                # Validate hashes and deterministic result before publishing COMPLETED.
                result = self.store.adapter.postprocess(PreparedRun(run_id, root))
                if not result["full_requested_interval_completed"]:
                    raise RuntimeError("INCOMPLETE_INTERVAL")
                with self.store.transaction():
                    record = self.store._record(run_id)
                    record.status = "CANCELLED" if record.cancel_requested else "COMPLETED"
                    record.completed_steps, record.physical_time = result["accepted_steps"], result["final_time"]
                    record.planned_steps = result["accepted_steps"]
                    record.finished_at, record.heartbeat_at = utc_now(), utc_now()
                    self.store._commit(record)
            except Exception as error:
                if process and process.poll() is None:
                    terminate_worker(process.pid, process_identity(process.pid))
                    process.wait(timeout=10)
                with self.store.transaction():
                    record = self.store._record(run_id)
                    if record.status not in TERMINAL:
                        record.status = "CANCELLED" if record.cancel_requested else "FAILED"
                        record.failure = None if record.cancel_requested else (
                            str(error) if str(error) in ("WORKER_EXIT", "INCOMPLETE_INTERVAL") else "WORKER_FAILED")
                        record.finished_at = utc_now()
                        self.store._commit(record)

    def run(self):
        with file_lock(target(self.store.control, "manager.lock"), blocking=False):
            self.recover()
            try:
                while True:
                    self.store.heartbeat(self.identity)
                    self.sweeps.tick()
                    record = self.store.queued()
                    if record:
                        self.execute(record.run_id)
                    else:
                        time.sleep(.25)
            finally:
                write_json(self.store.control, "manager.json", {"pid": os.getpid(), "identity": self.identity,
                                                              "heartbeat_at": utc_now(), "status": "STOPPED"})


if __name__ == "__main__":
    RunManager(RunStore(Settings.from_env())).run()
