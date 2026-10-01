"""Production factory, real saved arrays, masks, integrals and evidence closure."""
import hashlib
from pathlib import Path
from shutil import copyfile

import numpy as np
import pytest

from backend import create_app
from backend.adapters.allocation_integration import IntegratedAllocationAdapter
from backend.registry import case8_allocation as R, gate_registry as G


@pytest.fixture(scope='module')
def allocation_client():
    return create_app().test_client()


def data(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.json
    assert response.json['availability'] == 'AVAILABLE'
    return response.json['data']


@pytest.mark.parametrize('identity', [R.RESULT_ID, *(f'gate.{c}.allocation' for c in G.CONFIG_ORDER)])
def test_real_allocation_scientific_and_evidence_closure(allocation_client, identity):
    client = allocation_client
    metadata = data(client, f'/api/v1/allocations/{identity}/metadata')
    summary = data(client, f'/api/v1/allocations/{identity}/summary')
    face = identity == R.RESULT_ID
    assert metadata['representation_type'] == ('FACE_FIELD' if face else 'CELL_FIELD')
    assert metadata['semantic_id'] == ('Case8_face_Pi_at_integrated' if face else 'Gate_cell_Pi_at_integrated')
    assert metadata['definition']['semantic_id'] == metadata['semantic_id']
    assert metadata['mask_refs'] == summary['mask_refs'] == [R.MASK_ID if face else G.MASK_ID]
    assert metadata['mask_counts'] == ([640, 648] if face else [672])
    assert metadata['masks'][0]['id'] == metadata['mask_refs'][0]
    assert metadata['masks'][0]['type'] == ('CASE8_NATIVE_FACE_SHOCK_WINDOW' if face else 'GATE_CELL_SHOCK_WINDOW')
    assert summary['measure']['includes_time_weights'] is True
    assert summary['measure']['includes_spatial_measure'] is (not face)
    description = create_app().extensions['allocation_service'].describe_allocation(metadata['experiment_id'], metadata['config_id'])
    assert description.representation_type == metadata['representation_type']
    assert metadata['result']['time']['accumulation'] == 'TRAJECTORY_INTEGRATED'
    assert metadata['result']['time']['sampling'] == ('TERMINAL' if face else 'STATIC')
    adapter = IntegratedAllocationAdapter()
    fields = []
    for field in metadata['fields']:
        ref = field['array_ref']
        array = data(client, f"/api/v1/allocations/{identity}/arrays/{ref['descriptor']['array_id']}")
        assert array['representation_type'] == metadata['representation_type']
        assert array['array_ref'] == ref
        assert array['result']['semantic_id'] == metadata['semantic_id']
        fields.append(np.asarray(array['values']).reshape(ref['descriptor']['shape']))
    budget = summary['total_budget']['value']['value']['value']
    assert summary['total_budget']['value']['result']['semantic_id'] == 'E_at_cumulative'
    assert summary['total_budget']['value']['result']['semantic_id'] != metadata['semantic_id']
    fraction = summary['inside']['value']['value']['value']
    if face:
        assert [f['domain']['location_type'] for f in metadata['fields']] == ['CARTESIAN_X_FACE', 'CARTESIAN_Y_FACE']
        with np.load(adapter.face._root / R.FREEZE_DIR / 'Pi_at_trajectory_integrated.npz', allow_pickle=False) as source:
            assert np.array_equal(fields[0], source['pi_at_x_faces'])
            assert np.array_equal(fields[1], source['pi_at_y_faces'])
        masks = [np.asarray(adapter.face.load_allocation_array(ref.result_id, ref.descriptor.array_id).values).reshape(field.shape).astype(bool)
                 for ref, field in zip(adapter.face.load_mask(R.MASK_ID).mask_array_refs, fields)]
        integral = fields[0].sum()/32 + fields[1].sum()/128
        inside = fields[0][masks[0]].sum()/32 + fields[1][masks[1]].sum()/128
    else:
        config = metadata['config_id']
        assert metadata['fields'][0]['domain']['location_type'] == 'CARTESIAN_CELL'
        source = np.load(adapter.cell._root / G.pi_at_relative_origin(config), allow_pickle=False)
        assert np.array_equal(fields[0], source)
        integral = fields[0].sum()
        inside = fields[0][adapter._cell_mask()].sum()
        assert budget == G.FROZEN_SUMMARY[config]['E_at']
    assert abs(integral - budget) < 1e-10
    assert abs(inside / integral - fraction) < 1e-10
    assert abs(fraction + summary['outside']['value']['value']['value'] - 1) < 1e-12
    evidence = data(client, f"/api/v1/evidence/{metadata['evidence_refs'][0]}")
    assert evidence['experiment_id']['value'] == metadata['experiment_id']
    assert evidence['config_id']['value'] == metadata['config_id']
    assert identity in evidence['result_ids']
    assert evidence['source_drift'] == {'state': 'KNOWN', 'value': False}
    for asset in evidence['source_assets']:
        assert asset['recorded_data_hash'] == asset['current_data_hash']
        assert asset['data_drift']['value'] is False
    for context in evidence['result_contexts']:
        assert set(context['provenance']['source_asset_ids']) <= {a['asset_id'] for a in evidence['source_assets']}
        assert context['provenance']['evidence_refs'] == metadata['evidence_refs']
        provenance = data(client, f"/api/v1/results/{context['result_id']}/provenance")
        assert provenance['provenance'] == context['provenance']
    assert all(ref.startswith('ev.') for ref in metadata['evidence_refs'] + summary['evidence_refs'])


def test_gate_comparison_is_only_three_cell_fields(allocation_client):
    comparison = data(allocation_client, '/api/v1/allocations/comparison?experiment_id=gate')
    assert comparison['representation_type'] == 'CELL_FIELD'
    assert [entry['config_id'] for entry in comparison['entries']] == list(G.CONFIG_ORDER)
    assert all(entry['representation_type'] == 'CELL_FIELD' for entry in comparison['entries'])
    assert len(comparison['shared_extent']) == 2
    arrays = [np.load(Path(G.SCIENTIFIC_ROOT_WINDOWS) / G.pi_at_relative_origin(c), allow_pickle=False) for c in G.CONFIG_ORDER]
    assert [s['value']['value']['value'] for s in comparison['shared_extent']] == [min(a.min() for a in arrays), max(a.max() for a in arrays)]
    assert all(s['value']['result']['semantic_id'] == G.SEMANTIC_ID for s in comparison['shared_extent'])
    for params in ['experiment_id=gate&representation_type=FACE_FIELD', 'experiment_id=case8']:
        response = allocation_client.get(f'/api/v1/allocations/comparison?{params}')
        assert response.status_code == 422
        assert response.json['error']['code'] == 'UNSUPPORTED_REPRESENTATION'


@pytest.mark.parametrize('identity', ['case8.A_u.allocation', 'case8.B_u.allocation', 'case8.C_u.allocation', 'gate.Fourth.allocation'])
def test_absent_allocation_has_no_fabricated_values(allocation_client, identity):
    response = allocation_client.get(f'/api/v1/allocations/{identity}/metadata')
    assert response.status_code == 404
    assert response.json['error']['code'] == 'MISSING_ASSET'
    assert 'data' not in response.json


@pytest.mark.parametrize('member', ['Pi_at.npy', 'entropy.csv', 'matched_qat.json', 'gate_ablation_analysis.csv', 'README.md'])
def test_gate_drift_blocks_delivery_without_modifying_scientific_sources(tmp_path, member):
    adapter = IntegratedAllocationAdapter(gate_root=tmp_path)
    original_root = Path(G.SCIENTIFIC_ROOT_WINDOWS)
    for asset in adapter._gate_assets('Acoustic'):
        relative = asset['relative_origin']['value']
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(original_root / relative, target)
        if target.name == member:
            target.write_bytes(target.read_bytes() + b'\n')
    response = create_app(allocation_adapter=adapter).test_client().get('/api/v1/allocations/gate.Acoustic.allocation/metadata')
    assert response.status_code == 500
    assert response.json['error']['code'] == 'SOURCE_ERROR'
    assert 'data' not in response.json


def test_selected_scientific_sources_remain_identical():
    import json
    before_path = Path('.cache/phase6/source-before.json')
    if not before_path.exists():
        pytest.skip('Integration-run preservation baseline is not present')
    for name, record in json.loads(before_path.read_text()).items():
        path = Path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
        assert path.stat().st_size == record['size']
        assert path.stat().st_mtime_ns == record['mtime_ns']
