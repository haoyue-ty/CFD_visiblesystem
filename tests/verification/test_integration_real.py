"""Acceptance over the production factory and real read-only source, without fakes."""
import csv
import json

import numpy as np
import pytest

from backend import create_app
from backend.adapters import Case8Adapter
from backend.registry import case8_source_constants as C, case8_semantics as SEM
from backend.schemas.openapi import export_openapi

BASE = '/api/v1/experiments/case8/configs'


@pytest.fixture(scope='module')
def real_app():
    return create_app()


@pytest.mark.parametrize('config', C.CONFIG_ORDER)
def test_real_arrays_and_histories_equal_recorded_source(real_app, config):
    adapter = real_app.extensions['case8_service'].adapter
    assert isinstance(adapter, Case8Adapter)
    client = real_app.test_client()
    frames = client.get(f'{BASE}/{config}/snapshots').json['data']['items']
    assert len(frames) == 6
    for frame in frames:
        with np.load(adapter._checkpoint_path(config, frame['step_index']), allow_pickle=False) as checkpoint:
            assert frame['physical_time'] == float(checkpoint['time'])
            for field in frame['fields']:
                ref = field['array_ref']
                response = client.get(f"/api/v1/results/{ref['result_id']}/arrays/{field['field_id']}")
                assert response.status_code == 200
                data = response.json['data']
                expected = checkpoint[field['field_id']]
                assert data['descriptor']['shape'] == list(expected.shape)
                assert np.array_equal(data['values'], expected.reshape(-1, order='C'))
                assert data['result']['verification']['status'] == 'VERIFIED_NOT_FROZEN'
    with adapter._history_path(config).open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    history = client.get(f'{BASE}/{config}/entropy-history').json['data']
    assert len(rows) == 1912
    for series in history['series']:
        assert len(series['points']) == series['total_point_count'] == 1912
        for point, row in zip(series['points'], rows):
            assert point['step_index']['value'] == int(row['step']) + 1
            assert point['physical_time']['value'] == float(row['time_end'])
            assert point['value']['value'] == float(row[series['source_column']])
        expected_accumulation = 'STEP_INCREMENT' if series['aggregation'] == 'STEP_INCREMENT' else 'TRAJECTORY_INTEGRATED'
        assert series['result']['time']['accumulation'] == expected_accumulation


def test_metrics_definitions_and_provenance_are_source_bound(real_app):
    client = real_app.test_client()
    metrics = client.get(f'{BASE}/D_u/metrics').json['data']
    evidence = client.get('/api/v1/evidence/ev.case8.D_u.metrics').json['data']
    assert {item['id'] for item in evidence['definitions']} == {slot['value']['definition_id'] for slot in metrics['items']}
    assert evidence['data_hash']['state'] == 'UNKNOWN'
    assert evidence['verification']['status'] == 'PARTIAL'
    assert len(evidence['source_assets']) == 3
    method = next(asset for asset in evidence['source_assets'] if asset['role'] == 'METHOD')
    assert method['relative_origin']['value'] == 'solver/fluxes/cross_mode_ec_unified_v1.py'
    assert method['recorded_data_hash'] == evidence['method_hash']
    assert evidence['recorded_source_hash'] == evidence['method_hash']
    for slot in metrics['items']:
        result = slot['value']['result']
        provenance = client.get(f"/api/v1/results/{result['result_id']}/provenance").json['data']['provenance']
        for key in ('registry_revision', 'data_revision', 'release_id', 'evidence_refs'):
            assert provenance[key] == result['provenance'][key]
        assert provenance['source_asset_ids'] == result['provenance']['source_asset_ids'] + [method['asset_id']]
        assert provenance['source_drift']['state'] == result['provenance']['source_drift']['state'] == 'UNKNOWN'
        assert result['result_id'] in evidence['result_ids']
        assert result['verification']['status'] == 'VERIFIED_NOT_FROZEN'


def test_missing_metric_is_a_missing_slot_without_value(monkeypatch):
    adapter = Case8Adapter()
    monkeypatch.setattr(adapter, '_read_checkpoint_metrics', lambda *args: {})
    metrics = adapter.load_metrics('A_u').model_dump(mode='json')
    assert len(metrics['items']) == 3
    assert all(slot['availability'] == 'MISSING' and 'value' not in slot for slot in metrics['items'])


@pytest.mark.parametrize('selector', ['secret', 'case8.D_u.snapshot.no.density', 'case8.D_u.snapshot.6.pressure'])
def test_bad_array_identity_cannot_read_another_member(real_app, selector):
    response = real_app.test_client().get(f'/api/v1/results/{selector}/arrays/density')
    assert response.status_code == 404
    assert response.json['error']['code'] == 'INVALID_RESULT_ID'


def test_exported_openapi_matches_production_catalog(real_app):
    from backend.core.settings import WORKSPACE_ROOT
    saved = json.loads((WORKSPACE_ROOT / 'config/openapi.json').read_text(encoding='utf-8'))
    assert saved == export_openapi(real_app.extensions['operation_catalog'])
    assert real_app.test_client().get('/api/v1/openapi.json').json == saved


def test_alignment_uses_real_recorded_times(real_app):
    adapter = real_app.extensions['case8_service'].adapter
    point = adapter.load_scalar_series('D_u', 'E_at_cumulative', offset=1199, limit=1).points[0]
    alignment = adapter.load_snapshot_alignment('D_u', scalar_step=1200)
    assert alignment.selected_scalar_time == point.physical_time.root.value
    frames = adapter.list_snapshots('D_u').items
    nearest = min(frames, key=lambda item: (abs(item.physical_time - point.physical_time.root.value), item.physical_time, item.snapshot_index))
    assert alignment.displayed_snapshot_id == nearest.snapshot_id
    pinned = adapter.load_snapshot_alignment('D_u', scalar_step=1200, policy='PINNED', snapshot_index=1)
    assert pinned.displayed_snapshot_time == 0.0
