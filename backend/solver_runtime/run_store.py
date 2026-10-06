"""Cross-process transactions and atomic, server-owned Run records."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

from backend.models.v2.experiment import ValidateExperimentRequest
from backend.models.v2.run import RunRecord, RunList
from backend.services.v2.experiments import ExperimentError, validate_experiment
from backend.solver_runtime.artifacts import target, utc_now, write_json
from backend.solver_runtime.case8_adapter import Case8SolverAdapter, MANIFEST, PreparedRun
from backend.solver_runtime.paths import runtime_root, run_directory
from backend.solver_runtime.processes import process_identity

TERMINAL = frozenset(("COMPLETED", "FAILED", "CANCELLED"))
ACTIVE = frozenset(("STARTING", "RUNNING", "POSTPROCESSING"))


@contextmanager
def file_lock(path, *, blocking=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + 10
        acquired = False
        while not acquired:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError:
                if not blocking or time.monotonic() >= deadline:
                    raise RuntimeError("Runtime lock is already owned") from None
                time.sleep(.025)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class RunStore:
    def __init__(self, settings, *, workspace=None, source=None, adapter=None):
        from backend.core.settings import WORKSPACE_ROOT
        self.settings = settings
        self.workspace = workspace or WORKSPACE_ROOT
        self.source = source or Path(json.loads(MANIFEST.read_text(encoding="utf-8"))["source_root"])
        self.root = runtime_root(self.source, workspace=self.workspace)
        self.control = self.root / "queue"
        self.adapter = adapter or Case8SolverAdapter()

    @contextmanager
    def transaction(self):
        with file_lock(target(self.control, "store.lock")):
            yield

    def directory(self, run_id):
        try:
            return run_directory(run_id, self.source, workspace=self.workspace)
        except (ValueError, TypeError, AttributeError):
            raise ExperimentError("UNKNOWN_RUN", "运行记录不存在。", 404) from None

    def _index(self):
        path = target(self.control, "index.json")
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"runs": [], "requests": {}}

    def _document(self, run_id):
        root = self.directory(run_id)
        if not root.is_dir():
            raise ExperimentError("UNKNOWN_RUN", "运行记录不存在。", 404)
        path = target(root, "run_control.json")
        if not path.exists():
            raise ExperimentError("UNKNOWN_RUN", "运行记录不存在。", 404)
        return json.loads(path.read_text(encoding="utf-8"))

    def _record(self, run_id):
        return RunRecord.model_validate_json(json.dumps(self._document(run_id)["record"]))

    def _commit(self, record, *, event=True):
        root = self.directory(record.run_id)
        path = target(root, "run_control.json")
        document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"events": []}
        events = document["events"]
        if event:
            record.last_event_id += 1
            events.append({"id": record.last_event_id, "type": "run", "data": record.model_dump(mode="json")})
        write_json(root, "run_control.json", {**document, "record": record.model_dump(mode="json"), "events": events})
        return record

    def get(self, run_id):
        with self.transaction():
            record = self._record(run_id)
        log = target(self.directory(run_id), "solver.log")
        if log.exists():
            # Only numerical progress lines are public; tracebacks contain local paths.
            with log.open("rb") as stream:
                stream.seek(max(0, log.stat().st_size - 8192))
                text = stream.read().decode("utf-8", errors="replace")
            import re
            record.log_tail = [line for line in text.splitlines() if re.fullmatch(r"step=\d+/\d+ t=[0-9.eE+-]+", line)][-20:]
        return record

    def list(self, query):
        with self.transaction():
            records = [self._record(run_id) for run_id in reversed(self._index()["runs"])]
        if query.status:
            records = [r for r in records if r.status == query.status]
        return RunList(runs=records[query.offset:query.offset + query.limit], total=len(records),
                       offset=query.offset, limit=query.limit)

    def manager_available(self):
        path = target(self.control, "manager.json")
        if not path.exists():
            return False
        info = json.loads(path.read_text(encoding="utf-8"))
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(info["heartbeat_at"])).total_seconds()
        return (info["status"] == "RUNNING" and age < 10
                and process_identity(info["pid"]) == info["identity"])

    def create(self, body):
        request = ValidateExperimentRequest(config=body.config, submission=body.submission)
        validated = validate_experiment(request)
        if body.confirmed_config_hash != validated.config_hash:
            raise ExperimentError("CONFIG_CONFIRMATION_CONFLICT", "配置已变化，请重新验证与确认。", 409)
        digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        with self.transaction():
            self.recover_index()
            index = self._index()
            previous = index["requests"].get(body.idempotency_key)
            if previous:
                if previous["digest"] != digest:
                    raise ExperimentError("IDEMPOTENCY_CONFLICT", "该提交标识已用于其他配置。", 409)
                return self._record(previous["run_id"])
            if not self.manager_available():
                raise ExperimentError("RUN_SERVICE_UNAVAILABLE", "后台运行服务未启动，请启动服务后重试。", 503, retryable=True)
            if sum(self._record(r).status == "QUEUED" for r in index["runs"]) >= self.settings.max_queued_runs:
                raise ExperimentError("RUN_QUEUE_FULL", "运行队列已满，请稍后重试。", 429, retryable=True)
            run = self.adapter.prepare_run(request)
            record = RunRecord(run_id=run.run_id, status="QUEUED", created_at=utc_now(),
                               requested_final_time=validated.normalized_config.time.final_time, experiment=validated)
            self._commit(record)
            document = self._document(run.run_id)
            document["request_identity"] = {"key": body.idempotency_key, "digest": digest}
            write_json(run.directory, "run_control.json", document)
            index["runs"].append(run.run_id)
            index["requests"][body.idempotency_key] = {"run_id": run.run_id, "digest": digest}
            write_json(self.control, "index.json", index)
            return record

    def recover_index(self):
        """Repair a crash between the Run commit and the queue-index commit."""
        index = self._index()
        runs_root = self.root / "runs"
        if runs_root.exists():
            for path in runs_root.iterdir():
                if not path.is_dir() or path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                    continue
                control = path / "run_control.json"
                if not control.exists() or path.name in index["runs"]:
                    continue
                document = self._document(path.name)
                identity = document.get("request_identity")
                record = self._record(path.name)
                if identity:
                    previous = index["requests"].get(identity["key"])
                    if previous and previous["run_id"] != path.name:
                        raise RuntimeError("Duplicate persisted request identity")
                    index["requests"][identity["key"]] = {"run_id": path.name, "digest": identity["digest"]}
                else:
                    record.status, record.failure, record.finished_at = "FAILED", "PREPARATION_INTERRUPTED", utc_now()
                    self._commit(record)
                index["runs"].append(path.name)
        write_json(self.control, "index.json", index)

    def cancel(self, run_id):
        with self.transaction():
            record = self._record(run_id)
            if record.status in TERMINAL or record.cancel_requested:
                return record
            record.cancel_requested = True
            if record.status == "QUEUED":
                record.status, record.finished_at = "CANCELLED", utc_now()
            return self._commit(record)

    def events(self, run_id, after):
        with self.transaction():
            document = self._document(run_id)
            return [e for e in document["events"] if e["id"] > after]

    def queued(self):
        with self.transaction():
            self.recover_index()
            return next((self._record(r) for r in self._index()["runs"] if self._record(r).status == "QUEUED"), None)

    def heartbeat(self, manager_id):
        write_json(self.control, "manager.json", {"pid": os.getpid(), "identity": manager_id,
                                                "heartbeat_at": utc_now(), "status": "RUNNING"})
