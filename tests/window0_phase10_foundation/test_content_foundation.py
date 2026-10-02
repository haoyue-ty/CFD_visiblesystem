"""Scientific content boundary and existing real-resource reuse acceptance."""
import hashlib
import json
from dataclasses import asdict
import re

import pytest
from pydantic import ValidationError

from backend.models.content import MechanismContent, SceneList, ScenePreset, ScientificTarget
from backend.models.core import known
from backend.registry import content_registry as R
from backend.registry.content_bindings import resolve_evidence, resolve_target


def test_exact_frozen_dtos_and_origin():
    mechanism, scenes = R.load_foundation()
    assert set(mechanism.model_dump()) == {'content_id', 'data_origin', 'nodes', 'edges', 'supported_states', 'evidence_refs', 'limitations'}
    assert mechanism.data_origin == 'SCHEMATIC'
    assert mechanism.supported_states == ['STRICT_1D', 'WEAKLY_2D']
    for scene in scenes.items:
        assert set(scene.model_dump()) == {'scene_id', 'title', 'conclusion', 'view_kind', 'targets', 'allowed_controls', 'evidence_refs', 'limitations'}


@pytest.mark.parametrize('origin', ['FROZEN_PRODUCTION', 'VERIFIED_PRODUCTION', 'DIAGNOSTIC_RERUN', 'MOCK'])
def test_mechanism_cannot_be_promoted_to_numerical(origin):
    payload = R.load_mechanism().model_dump()
    payload['data_origin'] = origin
    with pytest.raises(ValidationError):
        MechanismContent.model_validate(payload)


def test_graph_separates_trigger_output_and_receiving_content():
    mechanism = R.load_mechanism()
    pairs = {(edge.from_node, edge.to_node) for edge in mechanism.edges}
    assert {a for a, b in pairs if b == 'acoustic-gate'} == {'acoustic-information'}
    assert ('interface-state', 'background-psd') in pairs
    assert ('acoustic-gate', 'q-aa') in pairs
    assert ('acoustic-gate', 'q-at') in pairs
    assert ('q-aa', 'normal-output') in pairs
    assert ('q-at', 'tangential-output') in pairs
    assert ('tangential-content', 'tangential-output') in pairs
    # Traverse all descendants: no indirect tangential trigger route either.
    visited, frontier = set(), ['tangential-content']
    while frontier:
        current = frontier.pop()
        if current not in visited:
            visited.add(current)
            frontier.extend(b for a, b in pairs if a == current)
    assert 'acoustic-gate' not in visited
    gate = next(node for node in mechanism.nodes if node.id == 'acoustic-gate')
    assert 'δ_t' in gate.explanation and 'DOES NOT ENTER THE GATE' in gate.explanation
    assert 'Trigger ≠ Output' in gate.explanation
    text = mechanism.model_dump_json().lower()
    assert 'off-diagonal matrix coupling' not in text
    assert 'tangential perturbation triggers j' not in text


def test_tangential_input_to_gate_is_rejected():
    payload = R.load_mechanism().model_dump()
    payload['edges'].append({'from_node': 'tangential-content', 'to_node': 'acoustic-gate', 'label': 'Incorrect tangential trigger'})
    changed = MechanismContent.model_validate(payload)
    with pytest.raises(ValueError, match='delta_t'):
        R.validate_foundation(changed, R.load_scenes())


@pytest.mark.parametrize('state,qat,content,output', [
    ('STRICT_1D', 'OFF', 'VANISHES', 'VANISHES'),
    ('STRICT_1D', 'ENABLED', 'VANISHES', 'VANISHES'),
    ('WEAKLY_2D', 'OFF', 'MAY_BE_NONZERO', 'VANISHES'),
    ('WEAKLY_2D', 'ENABLED', 'MAY_BE_NONZERO', 'CONDITIONALLY_ACTIVE'),
])
def test_qualitative_state_combinations(state, qat, content, output):
    explanation = R.explain_mechanism_state(state, qat)
    assert explanation.acoustic_trigger == 'MAY_BE_NONZERO'
    assert explanation.tangential_receiving_content == content
    assert explanation.tangential_output == output
    assert all(isinstance(value, str) for value in asdict(explanation).values())


def test_strict_1d_receiving_content_and_weak_2d_conditional_amplitude():
    strict = R.explain_mechanism_state('STRICT_1D', 'ENABLED')
    weak = R.explain_mechanism_state('WEAKLY_2D', 'ENABLED')
    assert strict.acoustic_trigger == weak.acoustic_trigger
    assert 'receiving content vanishes' in strict.reason
    assert 'not because the gate is inactive' in strict.reason
    assert 'amplitude still depends on tangential' in weak.reason


@pytest.mark.parametrize('state,qat', [('NEAR1D', 'ENABLED'), ('STRICT_1D', '0.396'), ('WEAKLY_2D', 'ON')])
def test_unsupported_schematic_states_rejected(state, qat):
    with pytest.raises(ValueError):
        R.explain_mechanism_state(state, qat)


def test_near1d_gap_is_theory_only_without_fig13_substitution():
    mechanism, scenes = R.load_foundation()
    limitations = {lim.code: lim.description for lim in mechanism.limitations}
    assert 'NO_AUTHORITATIVE_NEAR1D_RAW_SCAN' in limitations
    assert 'Fig13 epsilon' in limitations['NO_AUTHORITATIVE_NEAR1D_RAW_SCAN']
    theory = limitations['THEORY_ONLY_NEAR1D_SCALING']
    assert 'O(epsilon)' in theory and 'O(epsilon^2)' in theory and 'theoretical' in theory
    assert all(control.name != 'epsilon' for scene in scenes.items for control in scene.allowed_controls)
    assert all(target.experiment_id not in ('near1d', 'near-1d', 'modal-validation') for scene in scenes.items for target in scene.targets)
    manifest = json.loads((R.CONTENT_ROOT / 'freeze_manifest.json').read_text())
    assert manifest['near1d_numerical_scan'] == 'MISSING'
    assert manifest['gap_code'] == 'NO_AUTHORITATIVE_NEAR1D_RAW_SCAN'


def test_exact_seven_titles_views_and_ids():
    scenes = R.load_scenes()
    assert [scene.scene_id for scene in scenes.items] == list(range(1, 8))
    assert tuple(scene.title for scene in scenes.items) == R.TITLES
    assert tuple(scene.view_kind for scene in scenes.items) == R.VIEWS


@pytest.mark.parametrize('change', ['delete', 'duplicate', 'eighth', 'reverse', 'wrong-view'])
def test_scene_identity_or_view_drift_rejected(change):
    payload = R.load_scenes().model_dump()
    if change == 'delete':
        payload['items'].pop()
    elif change == 'duplicate':
        payload['items'][1]['scene_id'] = 1
    elif change == 'eighth':
        eighth = dict(payload['items'][-1], scene_id=8)
        payload['items'].append(eighth)
    elif change == 'reverse':
        payload['items'].reverse()
    else:
        payload['items'][0]['view_kind'] = 'NUMERIC_SCAN'
    with pytest.raises(ValidationError):
        SceneList.model_validate(payload)


@pytest.mark.parametrize('identity', [0, 8, -1, '1', True])
def test_lookup_never_aliases_invalid_ids(identity):
    with pytest.raises(KeyError):
        R.get_scene(identity)


@pytest.mark.parametrize('field', ['case8_arrays', 'gate_maps', 'spectrum_arrays', 'cylinder_arrays', 'crossflow_metrics', 'epsilon_scan'])
def test_scene_cannot_store_numerical_payload(field):
    payload = R.get_scene(1).model_dump()
    payload[field] = [1.0, 2.0]
    with pytest.raises(ValidationError):
        ScenePreset.model_validate(payload)


def test_numeric_leaves_absent_except_scene_identity():
    def walk(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, (*path, key))
        elif isinstance(value, list):
            for child in value:
                walk(child, path)
        elif isinstance(value, (float, int)):
            assert path[-1] == 'scene_id', path
    for name in ('mechanism.json', 'scenes.json'):
        walk(json.loads((R.CONTENT_ROOT / name).read_text(encoding='utf-8')))


@pytest.mark.parametrize('scene_id,name,value', [(3, 'epsilon', '1e-5'), (4, 'time', '0.04'), (4, 'q_at', '0.2'), (5, 'q_at', '0.2'), (6, 'winner', 'Case8')])
def test_unsupported_controls_rejected(scene_id, name, value):
    payload = R.load_scenes().model_dump()
    payload['items'][scene_id-1]['allowed_controls'].append({'name': name, 'kind': 'ENUM', 'allowed_values': [value], 'combination_registry_ref': known('unregistered')})
    with pytest.raises(ValueError, match='controls'):
        R.validate_foundation(R.load_mechanism(), SceneList.model_validate(payload))


@pytest.mark.parametrize('experiment,config,result', [
    ('near-1d', 'epsilon-1e-5', 'near-1d.scan'), ('entropy-closure', 'D_u', 'closure.D_u'),
    ('case8', 'D_u', 'case8.B_u.E_at_cumulative'), ('case8', 'B_u', 'case8.B_u.allocation'),
    ('gate', 'Acoustic', 'gate.Pressure.allocation'), ('spectrum', 'spectrum.q-0.200', 'spectrum.q-0.200'),
    ('cylinder', 'C_u', 'cylinder.C_u.sectors'), ('cylinder', 'D_u', 'cylinder.D_u.cumulative2d'),
])
def test_unregistered_or_mismatched_targets_fail_closed(experiment, config, result):
    with pytest.raises(ValueError):
        resolve_target(ScientificTarget(experiment_id=experiment, config_id=known(config), result_ids=[result]))


def test_registered_but_wrong_story_configuration_rejected():
    payload = R.load_scenes().model_dump()
    payload['items'][0]['targets'][0] = {'experiment_id': 'case8', 'config_id': known('A_u'), 'result_ids': ['case8.A_u.E_at_cumulative']}
    with pytest.raises(ValueError, match='frozen story'):
        R.validate_foundation(R.load_mechanism(), SceneList.model_validate(payload))


def test_complete_spectrum_selector_and_crossflow_boundaries():
    modes = next(c for c in R.get_scene(5).allowed_controls if c.name == 'mode_index')
    assert modes.allowed_values == [str(mode) for mode in range(17)]
    assert {lim.code for lim in R.get_scene(6).limitations} >= {'DESCRIPTIVE_ONLY', 'NO_UNIFIED_RANKING'}
    assert [binding.operation_id for binding in R.scene_requests(4)] == ['ALLOC04']
    assert [binding.operation_id for binding in R.scene_requests(6)] == ['CMP01']


def test_independent_loads_preserve_frozen_registry():
    first = R.load_scenes()
    first.items[0].title = 'consumer change'
    first.items[4].allowed_controls[-1].allowed_values.clear()
    assert R.get_scene(1).title == 'How much dissipation?'
    assert len(R.get_scene(5).allowed_controls[-1].allowed_values) == 17


def test_frozen_bytes_and_tampering_rejected(tmp_path, monkeypatch):
    for path in R.CONTENT_ROOT.iterdir():
        (tmp_path / path.name).write_bytes(path.read_bytes())
    manifest = json.loads((tmp_path / 'freeze_manifest.json').read_text())
    assert manifest['base_commit'] == R.BASE_COMMIT
    for name, expected in manifest['sha256'].items():
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest() == expected
    monkeypatch.setattr(R, 'CONTENT_ROOT', tmp_path)
    with (tmp_path / 'scenes.json').open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(ValueError, match='Frozen content bytes changed'):
        R.load_scenes()


def test_all_references_match_actual_phase8_catalog(app):
    catalog = {operation.operation_id: operation for operation in app.extensions['operation_catalog'].operations}
    mechanism, scenes = R.load_foundation()
    bindings = [resolve_evidence(ref) for ref in mechanism.evidence_refs]
    for scene in scenes.items:
        bindings.extend(R.scene_requests(scene.scene_id))
        bindings.extend(resolve_evidence(ref) for ref in scene.evidence_refs)
        for target in scene.targets:
            bindings.extend(resolve_target(target))
    for binding in bindings:
        operation = catalog[binding.operation_id]
        pattern = re.sub(r'\{[^}]+\}', '[^/]+', operation.path)
        assert re.fullmatch(pattern, binding.path), binding
        assert operation.method == 'GET'
    assert {key for key in catalog if key.startswith('CONTENT')} == {'CONTENT01', 'CONTENT02', 'CONTENT03'}


def test_every_real_target_and_evidence_loads_from_existing_api(app):
    client = app.test_client()
    mechanism, scenes = R.load_foundation()
    bindings = {resolve_evidence(ref) for ref in mechanism.evidence_refs}
    for scene in scenes.items:
        bindings.update(R.scene_requests(scene.scene_id))
        bindings.update(resolve_evidence(ref) for ref in scene.evidence_refs)
        for target in scene.targets:
            bindings.update(resolve_target(target))
    for binding in sorted(bindings, key=lambda item: item.url):
        response = client.get(binding.url)
        assert response.status_code == 200, (binding.url, response.json)
        assert response.json['availability'] in ('AVAILABLE', 'PARTIAL')


@pytest.mark.parametrize('dataset', ['spectrum.q-0.000', 'spectrum.q-0.396'])
def test_real_spectrum_includes_all_modes(app, dataset):
    response = app.test_client().get(f'/api/v1/spectra/{dataset}/points')
    assert response.status_code == 200
    assert [point['mode_index'] for point in response.json['data']['points']] == list(range(17))


def test_real_cmp01_retains_descriptive_rules_and_missing_slot(app):
    response = app.test_client().get(R.scene_requests(6)[0].url)
    assert response.status_code == 200
    data = response.json['data']
    assert data['ranking_policy'] == 'NO_UNIFIED_RANKING'
    assert response.json['availability'] == 'PARTIAL'
    assert all(rule['status'] == 'DESCRIPTIVE_ONLY' for rule in data['comparability'])
    assert any(issue['code'] == 'MISSING_SCIENTIFIC_ASSET' for issue in response.json['issues'])


def test_s7_real_evidence_has_required_metadata(app):
    expected = {'method_name', 'config', 'source_assets', 'data_hash', 'verification', 'limitations'}
    for binding in R.scene_requests(7):
        response = app.test_client().get(binding.url)
        assert response.status_code == 200
        assert expected <= response.json['data'].keys()


def test_unknown_evidence_fails_closed():
    with pytest.raises(ValueError):
        resolve_evidence('ev.near1d.five-point-scan')
