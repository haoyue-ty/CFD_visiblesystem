import pytest
import json

from backend.models.v2.experiment import ValidateExperimentRequest
from backend.services.v2.experiments import validate_experiment

from tests.v2_p1.test_experiments import client, request_body, set_field


def test_catalog_advertises_ranges_separately_from_reference_values(client):
    case = client.get('/api/v2/cases').json['data']['cases'][0]
    fields = {field['field_path']: field for field in case['capabilities']}
    for name in ('grid.nx', 'grid.ny', 'method.q_aa', 'method.q_at', 'time.final_time'):
        assert fields[name]['support'] == 'RANGE'
        assert fields[name]['input_range']['minimum'] is not None
        assert fields[name]['verified_values']
        assert not fields[name]['execution_verified']
    assert fields['grid.nx']['input_range']['maximum'] == 256
    assert fields['grid.ny']['input_range']['maximum'] == 128
    assert fields['time.final_time']['input_range']['minimum_inclusive'] is False


@pytest.mark.parametrize('grid,aa,at,time', [
    ((96, 24), 4.8, .12, .015),
    ((160, 40), 6.6, .2, .005),
    ((64, 32), 0., 0., .03),
    ((256, 128), 13.2, .396, .08),
])
def test_custom_values_are_preserved_and_not_promoted_to_benchmarked_templates(client, grid, aa, at, time):
    body = request_body('case8.fast.D_u', 'form')
    body['config']['grid'].update(nx=grid[0], ny=grid[1])
    body['config']['method'].update(q_aa=aa, q_at=at)
    body['config']['time']['final_time'] = time
    response = client.post('/api/v2/experiments/validate', json=body)
    assert response.status_code == 200, response.json
    data = response.json['data']
    assert data['classification'] == 'CUSTOM_RUN'
    assert data['normalized_config']['grid']['nx'] == grid[0]
    assert data['normalized_config']['grid']['ny'] == grid[1]
    assert data['normalized_config']['method'] == body['config']['method']
    assert data['normalized_config']['time']['final_time'] == time
    assert len(data['config_hash']) == 64


@pytest.mark.parametrize('path,value', [
    ('grid.nx', 15), ('grid.nx', 257), ('grid.ny', 7), ('grid.ny', 129),
    ('method.q_aa', -.1), ('method.q_aa', 13.2001), ('method.q_at', -.1),
    ('method.q_at', .3961), ('time.final_time', 0.), ('time.final_time', .0801),
])
def test_custom_ranges_still_reject_out_of_bounds_values(client, path, value):
    body = request_body('case8.fast.D_u', 'form')
    set_field(body, path, value)
    response = client.post('/api/v2/experiments/validate', json=body)
    assert response.status_code == 400, response.json
    assert response.json['error']['code'] == 'INVALID_REQUEST'


def test_legacy_revision_is_only_allowed_when_executing_an_existing_record(client):
    body = request_body('case8.fast.D_u')
    body['submission']['capability_revision'] = 'case8.capability.p2.1'
    assert client.post('/api/v2/experiments/validate', json=body).status_code == 409
    request = ValidateExperimentRequest.model_validate_json(json.dumps(body))
    validated = validate_experiment(request, allow_legacy=True)
    assert validated.classification == 'LIVE_FAST_RUN'
    assert validated.capability_revision == 'case8.capability.p2.1'
