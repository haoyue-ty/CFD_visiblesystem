from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
from pathlib import Path
import types
from uuid import uuid4

import pytest

from backend import create_app
from backend.core.settings import Settings
from backend.models.v2.run import CreateRunRequest, RunListQuery
from backend.services.v2.experiments import ExperimentError, validate_experiment
from backend.solver_runtime.artifacts import write_json
from backend.solver_runtime.case8_adapter import Case8SolverAdapter
from backend.solver_runtime.paths import run_directory
from backend.solver_runtime.run_store import RunStore, file_lock
from backend.solver_runtime.run_manager import RunManager
from scripts.run_case8 import template_request


def body(qat=.396, key=None):
    request = template_request("case8.fast.D_u")
    request.config.method.q_at = qat
    return CreateRunRequest(**request.model_dump(), idempotency_key=key or str(uuid4()),
                            confirmed_config_hash=validate_experiment(request).config_hash)


@pytest.fixture
def store(tmp_path, monkeypatch):
    import backend.solver_runtime.case8_adapter as adapter_module
    workspace, source = tmp_path / "workspace", tmp_path / "source"
    source.mkdir()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"source_root": str(source)}), encoding="utf-8")
    monkeypatch.setattr(adapter_module, "MANIFEST", manifest)
    monkeypatch.setattr(adapter_module, "run_directory", partial(run_directory, workspace=workspace))
    result = RunStore(Settings(), workspace=workspace, source=source, adapter=Case8SolverAdapter())
    monkeypatch.setattr(result, "manager_available", lambda: True)
    return result


@pytest.fixture
def client(store):
    return create_app(run_store=store, case8_adapter=None, allocation_adapter=None, spectral_adapter=None,
                      cylinder_adapter=None, closure_adapter=None).test_client()


def test_concurrent_retries_create_one_persistent_run(store):
    request = body()
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(lambda _: store.create(request), range(8)))
    assert len({r.run_id for r in records}) == 1
    other_store = RunStore(store.settings, workspace=store.workspace, source=store.source)
    assert other_store.get(records[0].run_id).status == "QUEUED"
    assert store.list(RunListQuery()).total == 1
    assert len(list((store.root / "runs").iterdir())) == 1


def test_new_key_means_new_run_and_changed_request_key_conflicts(store):
    original = body()
    a = store.create(original)
    b = store.create(body())
    assert a.run_id != b.run_id
    with pytest.raises(ExperimentError, match="提交标识"):
        store.create(body(0., original.idempotency_key))


def test_confirmation_revision_and_input_revalidated_before_queue(store):
    request = body()
    request.confirmed_config_hash = "0" * 64
    with pytest.raises(ExperimentError) as error:
        store.create(request)
    assert error.value.code == "CONFIG_CONFIRMATION_CONFLICT"
    request = body()
    request.config.physics.mach = 7.
    with pytest.raises(ExperimentError) as error:
        store.create(request)
    assert error.value.code == "UNSUPPORTED_PARAMETER"
    assert store.list(RunListQuery()).total == 0


def test_queue_limit_retry_and_queued_cancel(store):
    records = [store.create(body()) for _ in range(3)]
    with pytest.raises(ExperimentError) as error:
        store.create(body())
    assert error.value.code == "RUN_QUEUE_FULL"
    assert store.cancel(records[1].run_id).status == "CANCELLED"
    assert store.cancel(records[1].run_id).last_event_id == 2
    assert store.queued().run_id == records[0].run_id
    assert store.create(body()).status == "QUEUED"


def test_offline_submission_never_creates_run(store, monkeypatch):
    monkeypatch.setattr(store, "manager_available", lambda: False)
    with pytest.raises(ExperimentError) as error:
        store.create(body())
    assert error.value.status == 503
    assert store.list(RunListQuery()).total == 0


@pytest.mark.parametrize("identity", ["../escape", "bad", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", str(uuid4())])
def test_unknown_id_does_not_create_directory(store, identity):
    with pytest.raises(ExperimentError) as error:
        store.get(identity)
    assert error.value.status == 404
    assert not (store.root / "runs").exists()


def test_api_accepts_202_without_starting_process(client, store, monkeypatch):
    import backend.solver_runtime.run_manager as module
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("API started a process"))
    response = client.post("/api/v2/runs", json=body().model_dump(mode="json"))
    assert response.status_code == 202
    run = response.json["data"]
    assert run["status"] == "QUEUED" and run["worker_pid"] is None
    root = store.directory(run["run_id"])
    assert not (root / "launch.claim").exists() and not (root / "final_state.npz").exists()
    assert client.get("/api/v2/cases").json["data"]["cases"][0]["execution_available"]
    assert client.get("/api/v2/runs?offset=0&limit=1&status=QUEUED").json["data"]["total"] == 1


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=1&limit=2", "path=anything", "status=UNKNOWN"])
def test_api_rejects_bad_pagination(client, query):
    assert client.get("/api/v2/runs?" + query).status_code == 400


def test_unknown_run_errors_identify_run_resource(client):
    response = client.get("/api/v2/runs/" + str(uuid4()))
    assert response.status_code == 404
    assert response.json["error"]["code"] == "UNKNOWN_RUN"
    assert response.json["error"]["target"]["resource_type"] == "run"
    assert response.json["request_id"] == response.headers["X-Request-ID"]


def test_sse_replays_monotonic_ids_and_releases_capacity(client, store):
    record = store.create(body())
    store.cancel(record.run_id)
    url = f"/api/v2/runs/{record.run_id}/events"
    response = client.get(url, headers={"Last-Event-ID": "1"}, buffered=False)
    assert response.status_code == 200
    chunks = iter(response.response)
    assert b"retry:" in next(chunks)
    event = next(chunks)
    assert b"id: 2" in event and b"CANCELLED" in event and b"id: 1" not in event
    response.close()
    assert client.get(url, headers={"Last-Event-ID": "-1"}).status_code == 400
    assert client.get(url + "?after=99999").status_code == 400
    store.settings.max_sse_connections = 1


def test_event_slots_keep_normal_api_available(store):
    store.settings.max_sse_connections = 1
    client = create_app(run_store=store, case8_adapter=None, allocation_adapter=None, spectral_adapter=None,
                        cylinder_adapter=None, closure_adapter=None).test_client()
    record = store.create(body())
    url = f"/api/v2/runs/{record.run_id}/events"
    response = client.get(url, buffered=False)
    assert client.get(url).status_code == 429
    assert client.get("/api/v2/cases").status_code == 200
    response.close()
    retry = client.get(url, buffered=False)
    assert retry.status_code == 200
    retry.close()


def test_cancel_final_record_does_not_change_terminal_status(store):
    record = store.create(body())
    with store.transaction():
        record.status = "COMPLETED"
        store._commit(record)
    assert store.cancel(record.run_id).status == "COMPLETED"
    assert not store.get(record.run_id).cancel_requested


def test_recovery_marks_interrupted_and_preserves_queue(store, monkeypatch):
    interrupted = store.create(body())
    queued = store.create(body())
    with store.transaction():
        interrupted.status, interrupted.worker_pid, interrupted.worker_identity = "RUNNING", 12345, "old-identity"
        store._commit(interrupted)
    killed = []
    monkeypatch.setattr("backend.solver_runtime.run_manager.terminate_worker", lambda *args: killed.append(args))
    RunManager(store).recover()
    assert killed == [(12345, "old-identity")]
    assert store.get(interrupted.run_id).failure == "WORKER_INTERRUPTED"
    assert store.get(interrupted.run_id).status == "FAILED"
    assert store.get(queued.run_id).status == "QUEUED"


def test_recovery_repairs_index_without_losing_idempotency(store):
    request = body()
    record = store.create(request)
    write_json(store.control, "index.json", {"runs": [], "requests": {}})
    RunManager(store).recover()
    assert store.create(request).run_id == record.run_id
    assert store.list(RunListQuery()).total == 1


def test_api_crash_index_gap_is_repaired_before_retry_or_dispatch(store):
    request = body()
    record = store.create(request)
    write_json(store.control, "index.json", {"runs": [], "requests": {}})
    assert store.create(request).run_id == record.run_id
    write_json(store.control, "index.json", {"runs": [], "requests": {}})
    assert store.queued().run_id == record.run_id
    assert store.list(RunListQuery()).total == 1


def test_worker_crash_is_failed_once(store, monkeypatch):
    import backend.solver_runtime.run_manager as module
    record = store.create(body())
    calls = []
    def spawn(*args, **kwargs):
        calls.append(args)
        return types.SimpleNamespace(pid=99999, poll=lambda: 1, returncode=1)
    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    RunManager(store).execute(record.run_id)
    assert store.get(record.run_id).status == "FAILED"
    assert store.get(record.run_id).failure == "WORKER_EXIT"
    RunManager(store).execute(record.run_id)
    assert len(calls) == 1


def test_completed_process_output_drift_never_publishes_success(store, monkeypatch):
    import backend.solver_runtime.run_manager as module
    record = store.create(body())
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: types.SimpleNamespace(pid=99999, poll=lambda: 0, returncode=0))
    def drift(*args):
        raise RuntimeError("RUN_OUTPUT_DRIFT")
    monkeypatch.setattr(store.adapter, "postprocess", drift)
    RunManager(store).execute(record.run_id)
    assert store.get(record.run_id).status == "FAILED"


def test_only_one_manager_can_hold_leader_lock(store):
    path = store.control / "manager.lock"
    with file_lock(path, blocking=False):
        with pytest.raises(RuntimeError, match="already owned"):
            with file_lock(path, blocking=False):
                pytest.fail("duplicate leader")


def test_incomplete_and_cancelled_results_not_served(client, store):
    record = store.create(body())
    url = f"/api/v2/runs/{record.run_id}"
    assert client.get(url + "/history").json["data"]["rows"] == []
    assert client.get(url + "/snapshots").json["data"]["availability"] == "PENDING"
    assert client.get(url + "/snapshot/step_000478").status_code == 409
    assert client.post(url + "/cancel").json["data"]["status"] == "CANCELLED"
    assert client.get(url + "/snapshot/step_000478").status_code == 409


def test_mutable_control_and_temporary_files_are_not_scientific_identity(tmp_path):
    from backend.solver_runtime.artifacts import output_inventory
    write_json(tmp_path, "run_control.json", {"status": "RUNNING"})
    write_json(tmp_path, "result.json", {"rho": 1})
    (tmp_path / "run_control.json.tmp").write_text("in progress")
    before = output_inventory(tmp_path)
    write_json(tmp_path, "run_control.json", {"status": "COMPLETED"})
    assert output_inventory(tmp_path) == before
    assert [row["path"] for row in before] == ["result.json"]


def test_three_entry_modes_share_run_validation_without_automatic_launch(store):
    records = []
    for mode in ("template", "form", "natural_language"):
        request = body()
        request.submission.input_mode = mode
        if mode == "natural_language":
            request.submission.natural_language_text = "使用 D_u fast 模板"
            request.submission.parser_version = "case8.nl.p1.1"
        records.append(store.create(request))
    assert len({r.experiment.config_hash for r in records}) == 1
    assert len({r.run_id for r in records}) == 3
    assert all(r.status == "QUEUED" and r.worker_pid is None for r in records)


def test_cancel_wins_during_output_validation(store, monkeypatch):
    import backend.solver_runtime.run_manager as module
    record = store.create(body())
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: types.SimpleNamespace(pid=99999, poll=lambda: 0, returncode=0))
    def completed(run):
        store.cancel(run.run_id)
        return {"full_requested_interval_completed": True, "accepted_steps": 478, "final_time": .04}
    monkeypatch.setattr(store.adapter, "postprocess", completed)
    RunManager(store).execute(record.run_id)
    final = store.get(record.run_id)
    assert final.status == "CANCELLED" and final.cancel_requested
    assert final.failure is None


def test_recovery_finishes_already_requested_cancel(store, monkeypatch):
    record = store.create(body())
    with store.transaction():
        record.status, record.cancel_requested = "RUNNING", True
        store._commit(record)
    RunManager(store).recover()
    assert store.get(record.run_id).status == "CANCELLED"
    assert store.get(record.run_id).failure is None


def test_capacity_audit_tolerates_concurrent_atomic_commit(tmp_path):
    from backend.solver_runtime.run_manager import directory_bytes
    path = tmp_path / "result.json"
    path.write_bytes(b"1234")
    (tmp_path / "status.json.tmp").write_bytes(b"temporary")
    class ReplacingName:
        name = "status.json"
        def is_file(self):
            return True
        def stat(self):
            raise FileNotFoundError("renamed during commit")
    root = types.SimpleNamespace(rglob=lambda pattern: [path, ReplacingName(), tmp_path / "status.json.tmp"])
    assert directory_bytes(root) == 4
