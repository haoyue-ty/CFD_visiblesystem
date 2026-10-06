"""Numerical contracts and scientific absence semantics, isolated test artifacts."""
import json

import numpy as np
import pytest

from backend.postprocess.case8 import primitive_fields, content_hash
from backend.postprocess.allocation import allocation_observer
from backend.services.v2.results import ScientificResultService
from backend.solver_runtime.artifacts import write_json, output_inventory
from tests.v2_p3.test_runs import store, client, body


@pytest.fixture
def complete(store):
    record = store.create(body())
    root = store.directory(record.run_id)
    config = record.experiment.normalized_config
    nx, ny = config.grid.nx, config.grid.ny
    state = np.zeros((ny, nx, 4))
    state[..., 0], state[..., 1], state[..., 2], state[..., 3] = 2., 6., 8., 35.
    x, y = (np.arange(nx) + .5)/nx, (np.arange(ny) + .5)/ny
    np.savez(root / "initial_state.npz", state=state, x=x, y=y)
    faces = {f"{axis}_pi_{c}": np.zeros((ny, nx + 1 if axis == 'x_faces' else nx))
             for axis in ("x_faces", "y_faces") for c in ("bg", "aa", "at")}
    (root / "snapshots").mkdir(exist_ok=True)
    np.savez(root / "snapshots/step_000001.npz", state=state, step=1, time=.04, **faces)
    write_json(root, "snapshots/index.json", [dict(step=1, time=.04, cell_shape=[ny, nx, 4])])
    write_json(root, "effective_solver_config.json", {"normalized_config": config.model_dump(mode="json"), "observer": {"scope": "all native faces, periodic y once"}})
    row = dict(step=0, time_end=.04, time_start=0., dt=.04)
    for c in ("bg", "aa", "at", "total"):
        row.update({f"dotE_{c}_s{s}": 0. for s in range(3)})
        row.update({f"deltaE_{c}": 0., f"E_{c}": 0.})
    (root / "diagnostics").mkdir(exist_ok=True)
    (root / "diagnostics/history.jsonl").write_text(json.dumps(row) + '\n', encoding="utf-8")
    (root / "derived").mkdir(exist_ok=True)
    np.savez(root / "derived/physical_fields.npz", front=np.ones(ny), width=np.zeros(ny))
    write_json(root, "result.json", dict(run_id=record.run_id, config_hash=record.experiment.config_hash,
        accepted_steps=1, final_time=.04, dt=.04, started_at="2026-10-03T00:00:00Z", finished_at="2026-10-03T00:00:01Z",
        verification="NUMERICAL_CHECKS_PASSED", channel_totals={f"E_{c}": 0. for c in ("bg", "aa", "at", "total")},
        physical_metrics=dict(front_width_mean=0., front_rms=0., front_high_k_fraction=0.),
        runtime=dict(wall_seconds=1., solver_seconds=.5, peak_rss_bytes=1000)))
    def inventory():
        write_json(root, "provenance.json", dict(outputs=output_inventory(root), software=[], source_manifest_revision="test",
            source_manifest_sha256="1"*64, loaded_modules=[dict(module="solver.fluxes.cross_mode_ec_unified_v1", path="solver/fluxes/cross_mode_ec_unified_v1.py", sha256="2"*64)]))
    inventory()
    store.adapter.postprocess = lambda run: None  # Synthetic artifacts never launch scientific code.
    with store.transaction():
        record.status = "COMPLETED"
        store._commit(record)
    return root, record, inventory


def test_ideal_gas_field_algebra():
    state = np.array([[[2., 6., 8., 35.]]])
    fields = primitive_fields(state, 1.4)
    for key, expected in dict(density=2., pressure=4., velocity_x=3., velocity_y=4., speed=5., mach=5/np.sqrt(2.8)).items():
        assert fields[key].item() == pytest.approx(expected)


@pytest.mark.parametrize("state", [np.zeros((2, 3, 4)), np.full((2, 3, 4), np.nan), np.ones((2, 3, 3)), np.array([[[1., 20., 0., 1.]]])])
def test_invalid_conservative_fields_fail(state):
    with pytest.raises(ValueError):
        primitive_fields(state, 1.4)


def test_allocation_stage_weights_exclude_snapshot_observation():
    class Source:
        def __init__(self, *args, **kwargs): pass
        def _face_diagnostics(self, state):
            return tuple({f"pi_{c}": np.ones(shape)*state for c in ("bg", "aa", "at")} for shape in ((2, 4), (2, 3)))
        def observe_stage(self, state):
            self._face_diagnostics(state)
            return {"dotE_at": float(state)}
        def snapshot(self, state): return self._face_diagnostics(state)
    observer = allocation_observer(Source, None, q_aa=3.96, q_at=.396, dt=.2)
    for value in (1, 2, 3, 4, 5, 6):
        observer.observe_stage(value)
        observer.snapshot(10000)
    assert observer.stage_count == 6
    for values in observer.cumulative_faces.values():
        np.testing.assert_allclose(values, .2*(1/6+2/6+2*3/3+4/6+5/6+2*6/3))


def test_legacy_absence_and_real_zero_differ(complete, store):
    root, record, _ = complete
    result = ScientificResultService(store).result(record.run_id)
    assert result.allocation.availability == "UNAVAILABLE" and result.allocation.arrays is None
    assert result.allocation.scalar_totals is None and result.allocation.reason
    assert all(m.availability == "AVAILABLE" and m.value == 0. for m in result.metrics)
    assert result.identity.frozen is False
    assert result.identity.data_origin == "V2_LIVE_COMPUTATION"
    assert result.result_hash == content_hash(result.model_dump(mode="json"))


def test_native_faces_geometry_and_zero_allocation(complete, store):
    root, record, inventory = complete
    with np.load(root / "snapshots/step_000001.npz") as snapshot:
        np.savez(root / "derived/cumulative_faces.npz", **{k: snapshot[k] for k in snapshot.files if 'faces' in k})
    inventory()
    result = ScientificResultService(store).result(record.run_id)
    assert result.allocation.availability == "AVAILABLE"
    assert result.allocation.max_scalar_abs_error == 0.
    x, y = result.allocation.arrays[0], result.allocation.arrays[3]
    assert x.shape == [16, 65] and y.shape == [16, 64]
    assert x.x[0] == 0 and x.x[-1] == 1 and y.y[0] == 0 and y.y[-1] == 15/16
    assert x.face_measure == 1/16 and y.face_measure == 1/64


def test_allocation_integral_mismatch_is_rejected(complete, store):
    root, record, inventory = complete
    np.savez(root / "derived/cumulative_faces.npz", **{f"{axis}_pi_{c}": np.ones((16, 65 if axis == 'x_faces' else 64)) for axis in ('x_faces', 'y_faces') for c in ('bg', 'aa', 'at')})
    inventory()
    with pytest.raises(Exception) as error:
        ScientificResultService(store).result(record.run_id)
    assert error.value.code == "RUN_OUTPUT_INVALID"


def test_history_rk_mismatch_is_rejected(complete, store):
    root, record, _ = complete
    row = json.loads((root / "diagnostics/history.jsonl").read_text())
    row["E_at"] = 100.
    (root / "diagnostics/history.jsonl").write_text(json.dumps(row)+'\n')
    with pytest.raises(Exception) as error:
        ScientificResultService(store).result(record.run_id)
    assert error.value.code == "RUN_OUTPUT_INVALID"


def test_missing_front_hf_stays_null(complete, store):
    root, record, _ = complete
    np.savez(root / "derived/physical_fields.npz", front=np.full(16, np.nan))
    result = ScientificResultService(store).result(record.run_id)
    assert all(m.value is None and m.reason and m.availability == "UNAVAILABLE" for m in result.metrics)


def test_api_field_context_and_evidence(complete, store, client):
    root, record, _ = complete
    url = f"/api/v2/runs/{record.run_id}"
    response = client.get(url + '/result')
    assert response.status_code == 200, response.json
    result = response.json['data']
    evidence = client.get(url + '/evidence').json['data']
    assert result['result_hash'] == evidence['result_hash']
    assert evidence['identity']['frozen'] is False
    assert all(not a['path'].startswith(('D:', 'C:')) for a in evidence['outputs'])
    field = client.get(url + '/snapshot/step_000001/field?field=mach').json['data']
    assert field['shape'] == [16, 64] and len(field['values']) == 1024
    context = client.get(url + '/snapshot/step_000001/view-context?field=mach&x_min=0&x_max=.5&y_min=0&y_max=.5').json['data']
    assert context['selected_count'] == 256 and context['mean'] == pytest.approx(5/np.sqrt(2.8))
    assert context['result_hash'] == result['result_hash'] and context['snapshot_sha256'] == field['source_sha256']
    empty = client.get(url + '/snapshot/step_000001/view-context?x_min=0&x_max=.001&y_min=0&y_max=.001').json['data']
    assert empty['selected_count'] == 0 and empty['mean'] is None and empty['reason']


@pytest.mark.parametrize('query', ['field=bad', 'x_min=0', 'x_min=nan&x_max=1&y_min=0&y_max=1', 'x_min=.5&x_max=.1&y_min=0&y_max=1', 'x_min=-1&x_max=.5&y_min=0&y_max=1', 'path=elsewhere'])
def test_context_rejects_invalid_region(complete, client, query):
    _, record, _ = complete
    response = client.get(f'/api/v2/runs/{record.run_id}/snapshot/step_000001/view-context?{query}')
    assert response.status_code == 400


def test_failed_or_pending_results_never_publish(store, client):
    record = store.create(body())
    for suffix in ('result', 'evidence', 'snapshot/step_000001/field', 'snapshot/step_000001/faces', 'snapshot/step_000001/view-context'):
        assert client.get(f'/api/v2/runs/{record.run_id}/{suffix}').status_code == 409


def test_output_drift_is_explicit_server_error(complete, store, client):
    _, record, _ = complete
    def drift(run): raise RuntimeError('RUN_OUTPUT_DRIFT')
    store.adapter.postprocess = drift
    response = client.get(f'/api/v2/runs/{record.run_id}/result')
    assert response.status_code == 500 and response.json['error']['code'] == 'RUN_OUTPUT_INVALID'


def test_unknown_snapshot_has_no_fallback(complete, client):
    _, record, _ = complete
    assert client.get(f'/api/v2/runs/{record.run_id}/snapshot/step_000002/field').status_code == 404
