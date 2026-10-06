"""Persistent lazy sweeps on the existing single-worker queue.

Lock order is sweep then run store. No caller holding a run transaction calls tick.
Child UUIDs are persisted before enqueue so a crash cannot duplicate a trajectory.
"""
from datetime import datetime, timezone
import hashlib
import itertools
import json
from uuid import UUID, uuid4

from backend.models.v2.experiment import ValidateExperimentRequest
from backend.models.v2.run import CreateRunRequest
from backend.models.v2.sweep import SweepRequest, SweepPreview, SweepRecord, SweepList
from backend.services.v2.experiments import ExperimentError, validate_experiment
from backend.solver_runtime.artifacts import target, utc_now, write_json
from backend.solver_runtime.run_store import file_lock, TERMINAL

SWEEP_TERMINAL = frozenset(("COMPLETED", "FAILED", "CANCELLED"))
ITEM_TERMINAL = TERMINAL | {"SKIPPED"}


def candidates(body):
    # Validate the base too: unsupported physics never disappears on expansion.
    validate_experiment(ValidateExperimentRequest(config=body.config, submission=body.submission))
    requests = []
    for aa, at in itertools.product(body.q_aa_values, body.q_at_values):
        config = body.config.model_copy(deep=True)
        config.method.q_aa, config.method.q_at = aa, at
        requests.append(ValidateExperimentRequest(config=config, submission=body.submission))
    return requests


def preview(body):
    request = SweepRequest.model_validate(body.model_dump(include=set(SweepRequest.model_fields)))
    experiments = [validate_experiment(r) for r in candidates(request)]
    payload = {"version": "case8.sweep.p7.1", "request": request.model_dump(mode="json"),
               "config_hashes": [e.config_hash for e in experiments]}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return SweepPreview(sweep_hash=digest, experiments=experiments, total_tasks=len(experiments),
        max_tasks=request.max_tasks, time_budget_seconds=request.time_budget_seconds,
        warnings=["仅扫描 q_aa/q_at，所有组合均重新验证，分类由后端决定。",
            "复用单 worker，逐项入队；时间预算从提交时起计入排队、求解和后处理。",
            "预算耗尽会取消正在排队/执行的子运行并跳过未提交项；取消完成需等待 worker 停止。",
            "epsilon 尚未完成物理语义与生效验证；新 Case 需单独登记 adapter，当前不开放。",
            "扫描仅提供 Case 8 结果，不建立通用性能排行榜。"])


class SweepService:
    def __init__(self, store):
        self.store = store
        self.root = store.root / "sweeps"

    def lock(self):
        return file_lock(target(self.root, "sweeps.lock"))

    def documents(self):
        return sorted((json.loads(p.read_text(encoding="utf-8")) for p in self.root.glob("*.json")),
                      key=lambda d: (d["record"]["created_at"], d["record"]["sweep_id"]))

    def path(self, sweep_id):
        try:
            if str(UUID(sweep_id)) != sweep_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ExperimentError("UNKNOWN_SWEEP", "扫描记录不存在。", 404) from None
        return target(self.root, sweep_id + ".json")

    def read(self, sweep_id):
        path = self.path(sweep_id)
        if not path.exists():
            raise ExperimentError("UNKNOWN_SWEEP", "扫描记录不存在。", 404)
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, document, record):
        document["record"] = record.model_dump(mode="json")
        write_json(self.root, record.sweep_id + ".json", document)

    def refresh(self, document):
        record = SweepRecord.model_validate_json(json.dumps(document["record"]))
        if record.status in SWEEP_TERMINAL:
            return record
        # Reconcile the narrow crash window between child enqueue and sweep commit.
        with self.store.transaction():
            self.store.recover_index()
            index = self.store._index()
            for item, key in zip(record.items, document["child_keys"]):
                if item.status in TERMINAL and item.run:
                    continue
                identity = index["requests"].get(key)
                if identity:
                    item.run = self.store._record(identity["run_id"])
                    item.status = item.run.status
        record.settled_tasks = sum(i.status in ITEM_TERMINAL for i in record.items)
        record.successful_tasks = sum(i.status == "COMPLETED" for i in record.items)
        end = datetime.fromisoformat(record.finished_at) if record.finished_at else datetime.now(timezone.utc)
        record.elapsed_seconds = max(0., (end - datetime.fromisoformat(record.created_at)).total_seconds())
        if record.status not in SWEEP_TERMINAL:
            if record.settled_tasks == record.total_tasks:
                record.status = "FAILED" if record.failure else "CANCELLED" if record.cancel_requested else (
                    "COMPLETED" if record.successful_tasks == record.total_tasks else "FAILED")
                if record.status == "FAILED" and not record.failure:
                    record.failure = "SWEEP_CHILD_FAILED"
                record.finished_at = utc_now()
            elif any(i.run for i in record.items) and record.status == "QUEUED":
                record.status = "RUNNING"
        self.save(document, record)
        return record

    def create(self, body):
        validated = preview(body)
        if validated.sweep_hash != body.confirmed_sweep_hash:
            raise ExperimentError("SWEEP_CONFIRMATION_CONFLICT", "扫描配置或预算已变化，请重新预览并确认。", 409)
        with self.lock():
            documents = self.documents()
            for doc in documents:
                if doc["idempotency_key"] == body.idempotency_key:
                    if doc["record"]["sweep_hash"] != validated.sweep_hash:
                        raise ExperimentError("IDEMPOTENCY_CONFLICT", "该提交标识已用于其他扫描。", 409)
                    return self.refresh(doc)
            if not self.store.manager_available():
                raise ExperimentError("RUN_SERVICE_UNAVAILABLE", "后台运行服务未启动。", 503, retryable=True)
            if sum(self.refresh(d).status not in SWEEP_TERMINAL for d in documents) >= 3:
                raise ExperimentError("SWEEP_QUEUE_FULL", "最多允许三项未完成扫描，请稍后重试。", 429, retryable=True)
            sweep_id = str(uuid4())
            record = SweepRecord(sweep_id=sweep_id, sweep_hash=validated.sweep_hash, status="QUEUED",
                created_at=utc_now(), time_budget_seconds=validated.time_budget_seconds,
                max_tasks=validated.max_tasks, total_tasks=validated.total_tasks,
                warnings=validated.warnings, items=[dict(index=i, q_aa=e.normalized_config.method.q_aa,
                    q_at=e.normalized_config.method.q_at, config_hash=e.config_hash) for i, e in enumerate(validated.experiments)])
            document = {"idempotency_key": body.idempotency_key,
                "request": body.model_dump(mode="json", include=set(SweepRequest.model_fields)),
                "child_keys": [str(uuid4()) for i in range(record.total_tasks)]}
            self.save(document, record)
            return record

    def get(self, sweep_id):
        with self.lock():
            return self.refresh(self.read(sweep_id))

    def list(self, query):
        with self.lock():
            records = [self.refresh(d) for d in reversed(self.documents())]
            return SweepList(sweeps=records[query.offset:query.offset+query.limit], total=len(records), offset=query.offset, limit=query.limit)

    def stop(self, document, record, *, timeout=False):
        record.cancel_requested = True
        record.status = "CANCELLING"
        if timeout:
            record.failure = "SWEEP_TIME_BUDGET_EXCEEDED"
        # Persist intent before cancelling children; restart safely repeats it.
        self.save(document, record)
        for item in record.items:
            if item.run and item.status not in TERMINAL:
                item.run = self.store.cancel(item.run.run_id)
                item.status = item.run.status
            elif item.status == "PENDING":
                item.status = "SKIPPED"
        self.save(document, record)
        return self.refresh(document)

    def cancel(self, sweep_id):
        with self.lock():
            document = self.read(sweep_id)
            record = self.refresh(document)
            return record if record.status in SWEEP_TERMINAL else self.stop(document, record)

    def tick(self):
        with self.lock():
            documents = self.documents()
            records = []
            for doc in documents:
                record = self.refresh(doc)
                if record.status in SWEEP_TERMINAL:
                    continue
                if record.cancel_requested or record.elapsed_seconds >= record.time_budget_seconds:
                    record = self.stop(doc, record, timeout=bool(record.failure) or (
                        not record.cancel_requested and record.elapsed_seconds >= record.time_budget_seconds))
                records.append((doc, record))
            # A previous sweep must settle before the next expands into the queue.
            for doc, record in records:
                if record.status in SWEEP_TERMINAL:
                    continue
                if record.cancel_requested or any(i.run and i.status not in TERMINAL for i in record.items):
                    return
                item = next((i for i in record.items if i.status == "PENDING"), None)
                if item is None:
                    return
                try:
                    request = SweepRequest.model_validate_json(json.dumps(doc["request"]))
                    candidate = candidates(request)[item.index]
                    item.run = self.store.create(CreateRunRequest(**candidate.model_dump(),
                        idempotency_key=doc["child_keys"][item.index], confirmed_config_hash=item.config_hash))
                except (ExperimentError, ValueError) as error:
                    if isinstance(error, ExperimentError) and error.code in ("RUN_QUEUE_FULL", "RUN_SERVICE_UNAVAILABLE"):
                        return
                    record.failure = "SWEEP_VALIDATION_CHANGED"
                    self.stop(doc, record)
                    return
                item.status = item.run.status
                record.status = "RUNNING"
                self.save(doc, record)
                return
