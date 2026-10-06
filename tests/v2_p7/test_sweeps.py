from concurrent.futures import ThreadPoolExecutor
import json
from uuid import uuid4

import pytest

from backend.models.v2.sweep import SweepRequest, CreateSweepRequest, SweepListQuery
from backend.models.v2.run import CreateRunRequest, RunListQuery
from backend.services.v2.experiments import ExperimentError
from backend.services.v2.sweeps import SweepService, candidates, preview
from backend.solver_runtime.artifacts import write_json
from backend.solver_runtime.run_manager import RunManager
from scripts.run_case8 import template_request
from tests.v2_p3.test_runs import store, client


def request(**updates):
    return SweepRequest(**{**template_request('case8.fast.D_u').model_dump(),
        'q_aa_values': [3.96, 13.2], 'q_at_values': [0., .396], 'max_tasks': 4,
        'time_budget_seconds': 300., **updates})


def create_body(**updates):
    r = request(**updates)
    return CreateSweepRequest(**r.model_dump(), idempotency_key=str(uuid4()), confirmed_sweep_hash=preview(r).sweep_hash)


def test_preview_validates_all_candidates_without_queue_or_manager(store, monkeypatch):
    monkeypatch.setattr(store, 'manager_available', lambda: False)
    p = preview(request())
    assert p.total_tasks == 4
    assert [e.normalized_config.method.q_at for e in p.experiments] == [0., .396, 0., .396]
    assert p.experiments[1].classification == 'LIVE_FAST_RUN'
    assert all(e.classification == 'CUSTOM_RUN' for i, e in enumerate(p.experiments) if i != 1)
    assert not (store.root/'runs').exists()
    with pytest.raises(ExperimentError) as error:
        SweepService(store).create(create_body())
    assert error.value.code == 'RUN_SERVICE_UNAVAILABLE'


@pytest.mark.parametrize('change', [dict(max_tasks=3), dict(q_aa_values=[3.96,3.96]), dict(q_at_values=[]),
    dict(q_aa_values=[True]), dict(q_at_values=[float('nan')]), dict(time_budget_seconds=0.), dict(max_tasks=True)])
def test_invalid_requests_rejected(change):
    with pytest.raises(ValueError): request(**change)


def test_unverified_coefficients_and_physics_rejected(store):
    for r in (request(q_aa_values=[5.]), request(q_at_values=[.2])):
        with pytest.raises(ExperimentError) as error: preview(r)
        assert error.value.code == 'UNSUPPORTED_PARAMETER'
    r = request(); r.config.physics.initial_condition.corrugation_amplitude = .001
    with pytest.raises(ExperimentError): preview(r)
    assert not (store.root/'runs').exists()


def test_concurrent_retries_and_changed_confirmation(store):
    service = SweepService(store); body = create_body()
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda _: service.create(body), range(4)))
    assert len({r.sweep_id for r in records}) == 1
    assert service.list(SweepListQuery()).total == 1
    changed = body.model_copy(deep=True); changed.time_budget_seconds = 301.
    with pytest.raises(ExperimentError) as error: service.create(changed)
    assert error.value.code == 'SWEEP_CONFIRMATION_CONFLICT'
    changed.confirmed_sweep_hash = preview(changed).sweep_hash
    with pytest.raises(ExperimentError) as error: service.create(changed)
    assert error.value.code == 'IDEMPOTENCY_CONFLICT'


def test_lazy_serial_dispatch_and_progress_survive_restart(store):
    service = SweepService(store); sweep = service.create(create_body())
    assert store.list(RunListQuery()).total == 0
    ids = []
    for n in range(4):
        SweepService(store).tick()
        r = service.get(sweep.sweep_id)
        assert r.items[n].status == 'QUEUED'
        ids.append(r.items[n].run.run_id)
        service.tick()  # Never enqueue another child while this one is live.
        assert store.list(RunListQuery()).total == n+1
        with store.transaction():
            child = store._record(ids[-1]); child.status = 'COMPLETED'; store._commit(child)
    service.tick()
    r = service.get(sweep.sweep_id)
    assert r.status == 'COMPLETED' and r.successful_tasks == r.settled_tasks == 4
    assert len(set(ids)) == 4
    assert service.cancel(r.sweep_id).status == 'COMPLETED'


def test_crash_between_enqueue_and_sweep_commit_reconciles_identity(store):
    service = SweepService(store); body = create_body(); sweep = service.create(body)
    doc = service.read(sweep.sweep_id)
    candidate = candidates(body)[0]
    child = store.create(CreateRunRequest(**candidate.model_dump(), idempotency_key=doc['child_keys'][0],
        confirmed_config_hash=sweep.items[0].config_hash))
    assert doc['record']['items'][0]['run'] is None
    r = SweepService(store).get(sweep.sweep_id)
    assert r.items[0].run.run_id == child.run_id
    service.tick()
    assert store.list(RunListQuery()).total == 1
    assert service.cancel(sweep.sweep_id).status == 'CANCELLED'


def test_cancel_pending_and_queued_prevents_expansion(store):
    service = SweepService(store)
    a = service.create(create_body())
    assert service.cancel(a.sweep_id).status == 'CANCELLED'
    assert all(i.status == 'SKIPPED' for i in service.get(a.sweep_id).items)
    b = service.create(create_body()); service.tick()
    r = service.cancel(b.sweep_id)
    assert r.status == 'CANCELLED' and r.items[0].run.status == 'CANCELLED'
    service.tick()
    assert store.list(RunListQuery()).total == 1


def test_active_cancel_waits_for_worker_and_budget_is_persistent(store):
    service = SweepService(store); sweep = service.create(create_body()); service.tick()
    child = service.get(sweep.sweep_id).items[0].run
    with store.transaction():
        child.status = 'RUNNING'; store._commit(child)
    doc = service.read(sweep.sweep_id); doc['record']['created_at'] = '2020-01-01T00:00:00+00:00'
    write_json(service.root,sweep.sweep_id+'.json',doc)
    service.tick()
    r = service.get(sweep.sweep_id)
    assert r.status == 'CANCELLING' and r.failure == 'SWEEP_TIME_BUDGET_EXCEEDED'
    assert r.items[0].run.cancel_requested and all(i.status == 'SKIPPED' for i in r.items[1:])
    with store.transaction():
        child = store._record(child.run_id); child.status = 'CANCELLED'; store._commit(child)
    r = service.get(sweep.sweep_id)
    assert r.status == 'FAILED' and r.settled_tasks == 4 and r.successful_tasks == 0


def test_queue_full_retries_and_sweep_failure_and_recovery(store):
    from tests.v2_p3.test_runs import body
    unrelated = [store.create(body()) for _ in range(3)]
    service = SweepService(store); a = service.create(create_body()); b = service.create(create_body())
    service.tick(); assert not any(i.run for i in service.get(a.sweep_id).items)
    for r in unrelated: store.cancel(r.run_id)
    service.tick(); r = service.get(a.sweep_id).items[0].run
    with store.transaction():
        r.status = 'RUNNING'; store._commit(r)
    RunManager(store).recover()
    assert service.get(a.sweep_id).items[0].run.failure == 'WORKER_INTERRUPTED'
    service.tick()
    assert service.get(a.sweep_id).items[1].run
    assert not any(i.run for i in service.get(b.sweep_id).items)
    service.cancel(a.sweep_id); service.tick()
    assert service.get(b.sweep_id).items[0].run


def test_api_contract_unknown_fields_and_budget(client, store):
    payload = request().model_dump(mode='json')
    response = client.post('/api/v2/sweeps/preview',json=payload)
    assert response.status_code == 200 and response.json['data']['total_tasks'] == 4
    for key,value in [('epsilon',.001),('command','bad')]:
        assert client.post('/api/v2/sweeps/preview',json={**payload,key:value}).status_code == 400
    bad = json.loads(json.dumps(payload)); bad['config']['physics']['epsilon'] = .001
    assert client.post('/api/v2/sweeps/preview',json=bad).status_code == 400
    created = client.post('/api/v2/sweeps',json=create_body().model_dump(mode='json'))
    assert created.status_code == 202
    r=created.json['data']; assert r['status'] == 'QUEUED'
    assert client.get('/api/v2/sweeps').json['data']['total'] == 1
    assert client.get('/api/v2/sweeps/'+r['sweep_id']).status_code == 200
    assert client.get('/api/v2/sweeps/nope').status_code == 404
    assert client.get('/api/v2/sweeps/nope').json['error']['target']['resource_type'] == 'sweep'
    assert client.get('/api/v2/sweeps/'+r['sweep_id']+'?path=secret').status_code == 400
    assert client.post('/api/v2/sweeps/'+r['sweep_id']+'/cancel').json['data']['status'] == 'CANCELLED'


def test_active_sweep_limit_and_finished_slots_reusable(store):
    service = SweepService(store); records = [service.create(create_body()) for _ in range(3)]
    with pytest.raises(ExperimentError) as error: service.create(create_body())
    assert error.value.code == 'SWEEP_QUEUE_FULL'
    service.cancel(records[0].sweep_id)
    assert service.create(create_body()).status == 'QUEUED'


def test_capability_changes_fail_sweep_without_crashing_manager_or_starting_run(store, monkeypatch):
    service = SweepService(store); record = service.create(create_body())
    def changed(*args): raise ExperimentError('CAPABILITY_REVISION_CONFLICT','能力版本已更新',409)
    monkeypatch.setattr('backend.services.v2.sweeps.validate_experiment',changed)
    service.tick()
    r = service.get(record.sweep_id)
    assert r.status == 'FAILED' and r.failure == 'SWEEP_VALIDATION_CHANGED'
    assert all(i.status == 'SKIPPED' and i.run is None for i in r.items)
    assert not (store.root/'runs').exists()
