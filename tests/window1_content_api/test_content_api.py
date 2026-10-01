"""Window 1 HTTP, scientific boundary and generated-contract acceptance."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

from backend import create_app
from backend.core.errors import system_error
from backend.models import ApiEnvelope, FailedEnvelope
from backend.models.content import MechanismContent, SceneList, ScenePreset
from backend.registry import content_registry as R
from backend.registry.content_bindings import resolve_evidence, resolve_target
from backend.schemas.openapi import export_openapi

ROOT = Path(__file__).resolve().parents[2]
PATHS = {'CONTENT01': '/api/v1/explore/scenes',
         'CONTENT02': '/api/v1/explore/scenes/{scene_id}',
         'CONTENT03': '/api/v1/mechanism'}
SCENES = PATHS['CONTENT01']


def success(response, model):
    assert response.status_code == 200, response.text
    envelope = ApiEnvelope[model].model_validate_json(response.data).root
    assert envelope.availability == 'AVAILABLE'
    assert envelope.request_id == response.headers['X-Request-ID']
    assert response.headers['Cache-Control'] == 'no-store'
    assert envelope.issues == []
    return envelope.data


def test_content01_exact_seven_scenes(app):
    scenes = success(app.test_client().get(SCENES), SceneList)
    assert [scene.scene_id for scene in scenes.items] == list(range(1, 8))
    assert scenes == R.load_scenes()


@pytest.mark.parametrize('scene_id', range(1, 8))
def test_content02_complete_scene(app, scene_id):
    scene = success(app.test_client().get(f'{SCENES}/{scene_id}'), ScenePreset)
    assert scene == R.get_scene(scene_id)
    assert set(scene.model_dump()) == {'scene_id', 'title', 'conclusion', 'view_kind',
                                       'targets', 'allowed_controls', 'evidence_refs', 'limitations'}
    assert scene.title and scene.conclusion and scene.evidence_refs and scene.limitations


@pytest.mark.parametrize('scene_id', ['0', '8', '-1', '1.0', 'abc', '01', '+1', '1e0'])
def test_invalid_scene_identity_is_typed(app, scene_id):
    response = app.test_client().get(f'{SCENES}/{scene_id}')
    assert response.status_code == 400
    envelope = FailedEnvelope.model_validate_json(response.data)
    assert envelope.availability == 'ERROR'
    assert envelope.error.code == 'INVALID_REQUEST'
    assert envelope.error.domain == 'SYSTEM'
    assert not envelope.error.retryable
    assert 'data' not in response.json


@pytest.mark.parametrize('path', [SCENES, f'{SCENES}/3', '/api/v1/mechanism'])
@pytest.mark.parametrize('query', ['epsilon=1e-5', 'state=STRICT_1D', 'state_vector=1,2,3,4',
                                   'scene_id=1', 'registry_revision=a&registry_revision=b'])
def test_unsupported_inputs_rejected(app, path, query):
    response = app.test_client().get(f'{path}?{query}')
    assert response.status_code == 400
    assert FailedEnvelope.model_validate_json(response.data).error.code == 'INVALID_REQUEST'


@pytest.mark.parametrize('path', [SCENES, f'{SCENES}/1', '/api/v1/mechanism'])
def test_content_revision_and_method_contract(app, path):
    client = app.test_client()
    first = client.get(path)
    revision = first.json['registry_revision']['value']
    assert revision == app.extensions['content_service'].registry_revision
    assert client.get(f'{path}?registry_revision={revision}').status_code == 200
    unavailable = client.get(f'{path}?registry_revision=missing')
    assert unavailable.status_code == 409
    assert FailedEnvelope.model_validate_json(unavailable.data).error.code == 'REVISION_UNAVAILABLE'
    invalid = client.post(path, json={'state_vector': [1, 2, 3, 4]})
    assert invalid.status_code == 405
    assert invalid.json['error']['code'] == 'METHOD_NOT_ALLOWED'
    assert 'GET' in invalid.headers['Allow']


def test_content03_schematic_complete_graph(app):
    mechanism = success(app.test_client().get('/api/v1/mechanism'), MechanismContent)
    assert mechanism.data_origin == 'SCHEMATIC'
    assert mechanism.supported_states == ['STRICT_1D', 'WEAKLY_2D']
    assert mechanism == R.load_mechanism()
    ids = [node.id for node in mechanism.nodes]
    assert len(ids) == len(set(ids))
    assert {'interface-state', 'background-psd', 'acoustic-information', 'acoustic-gate',
            'normal-output', 'tangential-output', 'combiner', 'entropy-variable-mapping'} <= set(ids)
    pairs = {(edge.from_node, edge.to_node) for edge in mechanism.edges}
    assert all(a in ids and b in ids for a, b in pairs)
    assert {a for a, b in pairs if b == 'acoustic-gate'} == {'acoustic-information'}
    assert {a for a, b in pairs if b == 'combiner'} == {'background-psd', 'normal-output', 'tangential-output'}
    assert ('combiner', 'entropy-variable-mapping') in pairs
    assert all(node.explanation for node in mechanism.nodes)
    assert all(edge.label for edge in mechanism.edges)
    assert 'NO_AUTHORITATIVE_NEAR1D_RAW_SCAN' in {lim.code for lim in mechanism.limitations}


@pytest.mark.parametrize('child_error,status', [(None, 503), ('SOURCE_DATA_DRIFT', 409), ('SOURCE_READ_ERROR', 500)])
def test_scene_metadata_survives_unavailable_children_without_scientific_io(monkeypatch, child_error, status):
    app = create_app(case8_adapter=None, allocation_adapter=None, spectral_adapter=None, cylinder_adapter=None)
    client = app.test_client()
    if child_error:
        def fail_child(*args, **kwargs):
            raise system_error(child_error, 'Controlled child resource failure', status=status)
        monkeypatch.setattr(app.extensions['case8_service'], 'load_scalar_series', fail_child)
    assert client.get('/api/v1/experiments/case8/configs/B_u/scalar-series/E_bg_cumulative').status_code == status
    original_open = io.open

    def guard(file, mode='r', *args, **kwargs):
        if isinstance(file, (str, Path)):
            assert not Path(file).resolve().is_relative_to(Path('D:/Paper').resolve()), file
        return original_open(file, mode, *args, **kwargs)

    def no_process(*args, **kwargs):
        pytest.fail('Content delivery must not start a solver or any child process')

    monkeypatch.setattr(io, 'open', guard)
    monkeypatch.setattr(subprocess, 'Popen', no_process)
    assert len(success(client.get(SCENES), SceneList).items) == 7
    for scene_id in range(1, 8):
        assert success(client.get(f'{SCENES}/{scene_id}'), ScenePreset) == R.get_scene(scene_id)
    assert success(client.get('/api/v1/mechanism'), MechanismContent).data_origin == 'SCHEMATIC'


def test_scene_payloads_have_no_scientific_arrays(app):
    def walk(value, key=''):
        if isinstance(value, dict):
            assert not {'values', 'points', 'arrays', 'eigenvalues', 'state_vector', 'flux'} & value.keys()
            for name, child in value.items():
                walk(child, name)
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, (float, int)):
            assert key == 'scene_id'

    client = app.test_client()
    walk(client.get(SCENES).json['data'])
    for scene_id in range(1, 8):
        walk(client.get(f'{SCENES}/{scene_id}').json['data'])
    walk(client.get('/api/v1/mechanism').json['data'])


def test_scene_targets_and_evidence_resolve_existing_registry_and_api(app):
    client = app.test_client()
    scenes = success(client.get(SCENES), SceneList)
    evidence = set()
    for scene in scenes.items:
        evidence.update(scene.evidence_refs)
        for target in scene.targets:
            assert target.config_id.root.state == 'KNOWN'
            for binding in resolve_target(target):
                response = client.get(binding.url)
                assert response.status_code == 200, (binding.url, response.json)
            for result_id in target.result_ids:
                response = client.get(f'/api/v1/results/{result_id}/provenance')
                assert response.status_code == 200, (result_id, response.json)
                assert response.json['data']['provenance']['evidence_refs']
    mechanism = success(client.get('/api/v1/mechanism'), MechanismContent)
    evidence.update(mechanism.evidence_refs)
    for ref in sorted(evidence):
        response = client.get(resolve_evidence(ref).url)
        assert response.status_code == 200, (ref, response.json)
    for ref in mechanism.evidence_refs:
        record = client.get(resolve_evidence(ref).url).json['data']
        assert record['method_name'] == {'state': 'KNOWN', 'value': 'cross_mode_ec_unified_v1'}
        assert any(asset['role'] == 'METHOD' for asset in record['source_assets'])
        assert record['method_hash']['state'] == 'KNOWN'
    # Evidence is existing implementation context, never an invented Near-1D result.
    assert not any('near1d' in ref.lower() for ref in evidence)


def test_only_three_content_operations_and_no_near1d_numerical_endpoint(app):
    operations = app.extensions['operation_catalog'].operations
    assert {op.operation_id: op.path for op in operations if op.operation_id.startswith('CONTENT')} == PATHS
    assert not any('near1d' in op.path.lower() or 'near-1d' in op.path.lower() for op in operations)
    for path in ('/api/v1/mechanism/flux', '/api/v1/mechanism/states', '/api/v1/near1d'):
        response = app.test_client().get(path)
        assert response.status_code == 404
        assert response.json['error']['code'] == 'API_ROUTE_NOT_FOUND'


def test_openapi_consistency_and_actual_payloads(app):
    document = export_openapi(app.extensions['operation_catalog'])
    assert json.loads((ROOT/'config/openapi.json').read_text(encoding='utf-8')) == document
    assert app.test_client().get('/api/v1/openapi.json').json == document
    validate(document)
    app.extensions['operation_catalog'].assert_routes(app)
    client = app.test_client()
    for identity, path in PATHS.items():
        operation = document['paths'][path]['get']
        assert operation['operationId'] == identity
        assert operation['x-service'] == 'ContentService'
        assert operation['x-delivery-phase'] == 'Full'
        assert {p['name'] for p in operation['parameters']} == ({'registry_revision', 'scene_id'} if identity == 'CONTENT02' else {'registry_revision'})
        urls = [path.replace('{scene_id}', str(i)) for i in range(1, 8)] if identity == 'CONTENT02' else [path]
        ref = operation['responses']['200']['content']['application/json']['schema']
        validator = Draft202012Validator({**ref, 'components': document['components']})
        for url in urls:
            validator.validate(client.get(url).json)
        error_ref = operation['responses']['400']['content']['application/json']['schema']
        Draft202012Validator({**error_ref, 'components': document['components']}).validate(client.get(urls[0] + '?epsilon=1').json)


def test_openapi_and_generated_types_repeatable(tmp_path):
    exports = [tmp_path/f'openapi-{i}.json' for i in (1, 2)]
    for output in exports:
        subprocess.run([sys.executable, '-m', 'scripts.export_openapi', '--output', str(output)], cwd=ROOT, check=True, capture_output=True)
    assert exports[0].read_bytes() == exports[1].read_bytes() == (ROOT/'config/openapi.json').read_bytes()
    cli = ROOT/'frontend/node_modules/openapi-typescript/bin/cli.js'
    assert cli.exists(), 'Install the locked frontend dependencies before contract acceptance'
    generated = [tmp_path/f'api-{i}.d.ts' for i in (1, 2)]
    for source, output in zip(exports, generated, strict=True):
        subprocess.run([shutil.which('node'), str(cli), str(source), '-o', str(output)], cwd=ROOT, check=True, capture_output=True)
    assert generated[0].read_bytes() == generated[1].read_bytes() == (ROOT/'frontend/src/types/generated/api.d.ts').read_bytes()
    types = generated[0].read_text(encoding='utf-8')
    assert all(identity in types for identity in PATHS)
    assert all(name in types for name in ('SceneList', 'ScenePreset', 'ScientificTarget', 'MechanismContent'))
