import copy
import hashlib
import json
from pathlib import Path

import pytest

from backend import create_app
from backend.models.v2.experiment import NaturalLanguageRequest
from backend.registry.v2.cases import CAPABILITY_REVISION, templates
from backend.ai.config_parser import parse_natural_language
from backend.services.v2.experiments import ExperimentError


class FakeAI:
    available = True

    def __init__(self, output=None, error=None):
        self.output, self.error, self.calls = output, error, 0

    def complete_json(self, system, text):
        self.calls += 1
        assert 'json' in system and '密钥' in system
        if self.error:
            raise self.error
        return self.output


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    return create_app().test_client()


def request_body(template='case8.paper.D_u', mode='template'):
    config = next(t for t in templates() if t.template_id == template).config.model_dump(mode='json')
    return {'config': config, 'submission': {'input_mode': mode, 'template_id': template,
            'capability_revision': CAPABILITY_REVISION,
            'natural_language_text': 'Case 8 D_u 论文模板' if mode == 'natural_language' else None,
            'parser_version': 'case8.nl.p1.1' if mode == 'natural_language' else None}}


def set_field(body, path, value):
    node = body['config']
    parts = path.split('.')
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value


def test_standalone_capabilities_do_not_enable_web_execution(client):
    response = client.get('/api/v2/cases')
    assert response.status_code == 200
    case = response.json['data']['cases'][0]
    assert response.json['request_id'] == response.headers['X-Request-ID']
    assert not response.json['data']['natural_language_available']
    assert case['input_validation_status'] == 'IMPLEMENTED'
    assert case['execution_status'] == 'STANDALONE_VERIFIED'
    assert not case['execution_available']
    assert len(case['templates']) == 5
    assert case['templates'][0]['benchmark_status'] == 'PASSED'
    assert all(c['execution_verified'] for c in case['capabilities'] if c['scope'] == 'INPUT' and c['validation_ready'])
    assert all(not c['execution_verified'] for c in case['capabilities'] if c['support'] == 'UNSUPPORTED')
    outputs = [c for c in case['capabilities'] if c['scope'] == 'OUTPUT']
    assert {c['field_path'] for c in outputs} == {'fields', 'entropy', 'metrics', 'allocation'}
    assert all(c['execution_verified'] and not c['validation_ready'] for c in outputs)
    assert client.post('/api/v2/runs', json={}).status_code == 400


@pytest.mark.parametrize('name,aa,at', [('A_u',13.2,0), ('B_u',3.96,0), ('C_u',13.2,.396), ('D_u',3.96,.396)])
def test_complete_paper_protocol_and_classification(client, name, aa, at):
    response = client.post('/api/v2/experiments/validate', json=request_body('case8.paper.' + name))
    assert response.status_code == 200, response.json
    data = response.json['data']
    assert data['classification'] == 'LIVE_PAPER_PROFILE'
    assert not data['execution_available']
    config = data['normalized_config']
    assert config['method']['q_aa'] == aa and config['method']['q_at'] == at
    assert config['grid']['domain'] == {'x': [0.,1.], 'y': [0.,1.]}
    assert config['physics']['initial_condition']['transverse_seed_sound_speed_factor'] == .01
    assert config['output']['checkpoint_fractions'] == [0.,.2,.4,.6,.8,1.]
    encoded = json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    assert data['config_hash'] == hashlib.sha256(encoded).hexdigest()


def test_three_entry_modes_share_normalization_and_hash(client):
    outputs = []
    for mode in ('template', 'form', 'natural_language'):
        body = request_body(mode=mode)
        if mode == 'form':
            body['config'].pop('physics')
            body['config'].pop('output')
            body['config']['method']['q_at'] = 0.396
        response = client.post('/api/v2/experiments/validate', json=body)
        assert response.status_code == 200, response.json
        outputs.append(response.json['data'])
    assert outputs[0] == outputs[1] == outputs[2]


def test_negative_zero_and_integer_float_notation_normalize(client):
    body = request_body('case8.paper.B_u')
    body['config']['method']['q_at'] = -0.0
    a = client.post('/api/v2/experiments/validate', json=body).json['data']
    body['config']['method']['q_at'] = 0
    body['config']['physics']['mach'] = 6
    b = client.post('/api/v2/experiments/validate', json=body).json['data']
    assert a['config_hash'] == b['config_hash']
    assert json.dumps(a['normalized_config']).find('-0.0') == -1


def test_template_lineage_not_relabelled_when_d_becomes_b(client):
    body = request_body()
    body['config']['method']['q_at'] = 0
    response = client.post('/api/v2/experiments/validate', json=body)
    data = response.json['data']
    assert data['classification'] == 'PAPER_SCALE_CUSTOM'
    assert data['protocol_diff'] == [{'field': 'method.q_at', 'expected': .396, 'actual': 0.0}]
    body['submission']['template_id'] = 'case8.paper.B_u'
    data_b = client.post('/api/v2/experiments/validate', json=body).json['data']
    assert data_b['classification'] == 'LIVE_PAPER_PROFILE'
    assert data_b['config_hash'] == data['config_hash']


def test_paper_grid_change_reports_actual_grid(client):
    body = request_body()
    body['config']['grid'].update(nx=64, ny=16)
    data = client.post('/api/v2/experiments/validate', json=body).json['data']
    assert data['classification'] == 'PAPER_SCALE_CUSTOM'
    assert {d['field'] for d in data['protocol_diff']} == {'grid.nx', 'grid.ny'}
    assert data['normalized_config']['grid']['nx'] == 64


def test_no_paper_identity_without_template_and_approved_fast(client):
    body = request_body(mode='form')
    body['submission']['template_id'] = None
    assert client.post('/api/v2/experiments/validate', json=body).json['data']['classification'] == 'CUSTOM_RUN'
    body = request_body('case8.fast.D_u')
    result = client.post('/api/v2/experiments/validate', json=body).json['data']
    assert result['classification'] == 'LIVE_FAST_RUN'
    assert any('benchmark' in w for w in result['warnings'])
    body['config']['method']['q_at'] = 0.0
    modified = client.post('/api/v2/experiments/validate', json=body).json['data']
    assert modified['classification'] == 'CUSTOM_RUN'
    assert modified['protocol_diff'] == [{'field': 'method.q_at', 'expected': .396, 'actual': 0.0}]


@pytest.mark.parametrize('path,value', [
    ('grid.nx', True), ('grid.nx', 64.0), ('grid.nx', '64'), ('grid.ny', 1.5), ('grid.nx', 129), ('grid.ny', 0),
    ('time.cfl', '0.05'), ('time.cfl', True), ('time.cfl', 0), ('time.final_time', -.01),
    ('method.q_aa', -1), ('method.q_at', .397), ('physics.mach', False),
    ('case_id', 'cylinder'), ('profile', 'production'), ('discretization.reconstruction', 'WENO'),
    ('discretization.positivity_clipping', 0), ('time.integrator', 'Euler'), ('method.method_id', 'other'),
    ('physics.epsilon', .0001), ('method.gate', 'Acoustic'), ('output.snapshot_interval', .01), ('command', 'cmd'),
])
def test_invalid_or_unknown_fields_are_rejected(client, path, value):
    body = request_body()
    set_field(body, path, value)
    response = client.post('/api/v2/experiments/validate', json=body)
    assert response.status_code == 400, response.json
    assert response.json['schema_version'] == '2.0.0'
    assert response.json['error']['code'] == 'INVALID_REQUEST'
    assert response.json['error']['details']
    assert 'data' not in response.json


@pytest.mark.parametrize('path,value', [
    ('time.cfl', .04), ('time.final_time', .02), ('method.q_aa', 4.0), ('method.q_at', .1),
    ('physics.mach', 5.), ('physics.gamma', 1.5), ('physics.initial_condition.corrugation_amplitude', .0001),
    ('physics.initial_condition.wavelength_count', 3), ('grid.domain.x', [0.,2.]),
    ('output.checkpoint_fractions', [0.,.1,.4,.6,.8,1.]), ('discretization.artificial_viscosity', True),
])
def test_unsupported_values_fail_with_field_details(client, path, value):
    body = request_body()
    set_field(body, path, value)
    response = client.post('/api/v2/experiments/validate', json=body)
    assert response.status_code == 422, response.json
    assert response.json['error']['code'] == 'UNSUPPORTED_PARAMETER'
    assert path in {item['field'] for item in response.json['error']['details']}


def test_grid_combination_revision_and_lineage_fail(client):
    body = request_body()
    body['config']['grid']['nx'] = 64
    assert client.post('/api/v2/experiments/validate', json=body).json['error']['code'] == 'UNSUPPORTED_COMBINATION'
    body = request_body()
    body['submission']['capability_revision'] = 'old'
    assert client.post('/api/v2/experiments/validate', json=body).status_code == 409
    body = request_body()
    body['submission']['template_id'] = 'unknown'
    assert client.post('/api/v2/experiments/validate', json=body).status_code == 400


@pytest.mark.parametrize('raw', ['{}', '[]', '{', '{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_json_preflight_safe_failures(client, raw):
    response = client.post('/api/v2/experiments/validate', data=raw, content_type='application/json')
    assert response.status_code == 400
    assert response.json['error']['code'] == 'INVALID_REQUEST'


@pytest.mark.parametrize('path', ['method.q_aa', 'physics.mach'])
@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity', '1e999'])
def test_non_finite_numbers_rejected(client, path, value):
    body = request_body()
    set_field(body, path, 'NONFINITE')
    raw = json.dumps(body).replace('"NONFINITE"', value)
    assert client.post('/api/v2/experiments/validate', data=raw, content_type='application/json').status_code == 400


def test_media_type_unknown_query_method_and_size(client):
    assert client.post('/api/v2/experiments/validate', data='{}').status_code == 415
    assert client.get('/api/v2/cases?path=secret').status_code == 400
    response = client.post('/api/v2/cases', json={})
    assert response.status_code == 405 and 'GET' in response.headers['Allow']
    response = client.post('/api/v2/experiments/validate', data=' ' * 65537, content_type='application/json')
    assert response.status_code == 413 and response.json['schema_version'] == '2.0.0'


def test_long_unknown_field_names_remain_client_errors(client):
    body = request_body()
    body['config']['x' * 300] = 'untrusted value'
    response = client.post('/api/v2/experiments/validate', json=body)
    assert response.status_code == 400
    assert response.json['error']['code'] == 'INVALID_REQUEST'
    assert len(response.json['error']['details'][0]['field']) <= 160
    assert 'untrusted value' not in response.get_data(as_text=True)


def extraction(**updates):
    data = {'template_id': 'case8.paper.D_u', 'parameters': {}, 'unresolved_fields': [],
            'unsupported_fields': [], 'warnings': []}
    data.update(updates)
    return json.dumps(data)


def parse(text='Case 8 D_u 论文模板', output=None):
    return parse_natural_language(NaturalLanguageRequest(text=text, capability_revision=CAPABILITY_REVISION),
                                 FakeAI(output or extraction()))


def test_ai_template_equivalent_to_other_modes_and_no_run(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = parse()
    assert result.ready_for_confirmation
    expected = client.post('/api/v2/experiments/validate', json=request_body()).json['data']
    assert result.validated.model_dump(mode='json') == expected
    assert not list(tmp_path.iterdir())


def test_ai_paper_modified_not_silently_relabelled():
    result = parse('D_u 论文模板，q_at=0', extraction(parameters={'q_at': 0}))
    assert result.validated.classification == 'PAPER_SCALE_CUSTOM'
    assert result.config.method.q_at == 0


def test_ai_missing_baseline_and_parameters_require_clarification():
    result = parse('做更稳定的实验', extraction(template_id=None))
    assert not result.ready_for_confirmation and result.validated is None and result.config is None
    assert len(result.unresolved_fields) >= 6


@pytest.mark.parametrize('text', ['使用论文标准', '创建实验', 'D_u 更稳定', 'D_u Case9', 'D_u 圆柱'])
def test_ai_cannot_guess_ambiguous_templates_or_other_cases(text):
    result = parse(text)
    assert not result.ready_for_confirmation
    assert result.unresolved_fields or result.unsupported_fields


def test_ai_custom_complete_and_unknown_template():
    result = parse('自定义', extraction(template_id=None, parameters={
        'nx':64, 'ny':16, 'cfl':.05, 'final_time':.04, 'q_aa':3.96, 'q_at':.396}))
    assert result.ready_for_confirmation and result.validated.classification == 'CUSTOM_RUN'
    result = parse(output=extraction(template_id='unknown'))
    assert not result.ready_for_confirmation and result.config is None


@pytest.mark.parametrize('text', ['D_u epsilon=0.0001', 'D_u Gate Acoustic', 'D_u WENO', 'D_u 快照间隔0.01'])
def test_explicit_unsupported_request_survives_model_omission(text):
    result = parse(text)
    assert result.unsupported_fields and not result.ready_for_confirmation and result.validated is None


@pytest.mark.parametrize('text,params', [('D_u q_aa=13.2', {}), ('D_u Mach=5', {}),
    ('D_u q_at=0，q_at=0.396', {'q_at':0}), ('D_u Nx=64', {'nx':128})])
def test_ai_cannot_drop_or_substitute_named_numeric_values(text, params):
    result = parse(text, extraction(parameters=params))
    assert result.unresolved_fields and not result.ready_for_confirmation


def test_ai_unsupported_numeric_retained_for_review():
    result = parse('D_u Mach=5', extraction(parameters={'mach':5}))
    assert not result.ready_for_confirmation and result.config.physics.mach == 5
    assert result.unsupported_fields[0].field == 'physics.mach'


@pytest.mark.parametrize('text', ['D_u 网格64×16', 'D_u q=0.396'])
def test_ai_cannot_ignore_unlabelled_grid_or_ambiguous_q(text):
    result = parse(text)
    assert result.unresolved_fields and not result.ready_for_confirmation


@pytest.mark.parametrize('raw', ['{}', '[]', 'bad', '', '{"a":1,"a":2}',
    extraction(parameters={'nx':64.0}), extraction(parameters={'command':'run'}),
    extraction(parameters={'q_at':'0'}), extraction(parameters={'q_at':float('nan')})])
def test_invalid_ai_output_is_not_a_success(raw):
    with pytest.raises(ExperimentError) as caught:
        parse_natural_language(NaturalLanguageRequest(text='D_u', capability_revision=CAPABILITY_REVISION), FakeAI(raw))
    assert caught.value.code == 'AI_INVALID_OUTPUT'


def test_ai_failure_is_independent_of_template_validation(client):
    response = client.post('/api/v2/experiments/parse-natural-language', json={'text':'D_u', 'capability_revision':CAPABILITY_REVISION})
    assert response.status_code == 503 and response.json['error']['code'] == 'AI_UNAVAILABLE'
    assert client.post('/api/v2/experiments/validate', json=request_body()).status_code == 200


def test_ai_api_success_and_stale_revision_does_not_call_provider():
    fake = FakeAI(extraction())
    client = create_app(ai_client=fake).test_client()
    body = {'text':'Case8 D_u 论文模板', 'capability_revision':CAPABILITY_REVISION}
    assert client.post('/api/v2/experiments/parse-natural-language', json=body).json['data']['ready_for_confirmation']
    assert fake.calls == 1
    body['capability_revision'] = 'old'
    assert client.post('/api/v2/experiments/parse-natural-language', json=body).status_code == 409
    assert fake.calls == 1


def test_v1_contract_subset_unchanged(app):
    import subprocess
    from backend.schemas.openapi import export_openapi
    original = json.loads(subprocess.check_output(['git','show','HEAD:config/openapi.json']))
    actual = export_openapi(app.extensions['operation_catalog'])
    assert {key: actual['paths'][key] for key in original['paths']} == original['paths']
    assert {key: actual['components']['schemas'][key] for key in original['components']['schemas']} == original['components']['schemas']
    for path in ('/api/v2/experiments/validate', '/api/v2/experiments/parse-natural-language'):
        operation = actual['paths'][path]['post']
        assert operation['requestBody']['required']
        assert operation['responses']['400']['content']['application/json']['schema']['$ref'].endswith('V2FailedEnvelope')


def test_v2_catalog_and_error_contract_are_exact(app):
    from backend.schemas.openapi import export_openapi
    catalog = app.extensions['operation_catalog']
    operations = [op for op in catalog.operations if op.delivery_phase == 'V2-P1']
    assert {op.operation_id for op in operations} == {'V2_CASES','V2_VALIDATE_EXPERIMENT','V2_PARSE_EXPERIMENT'}
    known = {'INVALID_REQUEST','UNSUPPORTED_MEDIA_TYPE','UNSUPPORTED_PARAMETER','UNSUPPORTED_COMBINATION',
             'CAPABILITY_REVISION_CONFLICT','AI_UNAVAILABLE','AI_INVALID_OUTPUT','INTERNAL_ERROR','CANONICAL_SCHEMA_MISMATCH'}
    document = export_openapi(catalog)
    for op in operations:
        assert op.error_response_model.__name__ == 'V2FailedEnvelope'
        for status, codes in op.documented_errors.items():
            assert codes and set(codes) <= known
            schema = document['paths'][op.path][op.method.lower()]['responses'][str(status)]['content']['application/json']['schema']
            assert schema['$ref'].endswith('/V2FailedEnvelope')
    catalog.assert_routes(app)
