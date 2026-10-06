import pytest

from backend.models.v2.comparison import CompareRunsRequest
from backend.services.v2.comparison import ComparisonService
from backend.services.v2.results import ScientificResultService
from tests.v2_p3.test_runs import store, client, body
from tests.v2_p4.test_results import complete


def pair(store, complete):
    _, record, _ = complete
    result = ScientificResultService(store).result(record.run_id)
    a, b = result.model_copy(deep=True), result.model_copy(deep=True)
    b.config.normalized_config.method.q_at = 0.
    b.identity.run_id = 'b'
    service = ComparisonService(store)
    service.scientific.result = lambda run_id: a if run_id == record.run_id else b
    original = service.scientific.field
    service.scientific.field = lambda query: original(query.model_copy(update={'run_id': record.run_id}))
    return service, a, b, CompareRunsRequest(run_a=record.run_id, run_b='b')


def test_allowed_coefficients_same_conditions_unified_field_and_true_zero(store, complete):
    service, a, b, request = pair(store,complete)
    result = service.compare(request)
    assert result.same_conditions
    assert [d.field for d in result.differences] == ['method.q_at']
    assert result.snapshot_time == .04 and result.field_a.time == result.field_b.time
    assert result.color_min == result.color_max == 2.
    assert all(m.comparable and m.b_minus_a == 0. for m in result.metrics)


@pytest.mark.parametrize('field,value', [('nx',128), ('final_time',.08), ('reconstruction','future'),
    ('mach',7.),('corrugation_amplitude',.02), ('cfl',.1), ('method_sha256','different'),('detector','future')])
def test_protocol_mismatches_never_produce_metric_differences(store, complete, field, value):
    service,a,b,request=pair(store,complete)
    target = {'nx':b.config.normalized_config.grid,'final_time':b.config.normalized_config.time,
        'cfl':b.config.normalized_config.time,'reconstruction':b.config.normalized_config.discretization,
        'mach':b.config.normalized_config.physics,'corrugation_amplitude':b.config.normalized_config.physics.initial_condition,
        'method_sha256':b.provenance,'detector':b.metrics[0]}[field]
    setattr(target,field,value)
    result=service.compare(request)
    assert not result.same_conditions and any(d.affects_conditions for d in result.differences)
    assert all(m.b_minus_a is None and not m.comparable and m.reason for m in result.metrics)


def test_missing_metric_and_unmatched_snapshot_time(store,complete):
    service,a,b,request=pair(store,complete)
    b.metrics[0].value=None; b.metrics[0].availability='UNAVAILABLE'; b.metrics[0].reason='no detector rows'
    result=service.compare(request)
    assert result.same_conditions
    assert next(m for m in result.metrics if m.metric_id == b.metrics[0].metric_id).b_minus_a is None
    request.snapshot_time=.02
    with pytest.raises(Exception) as error: service.compare(request)
    assert error.value.code == 'COMPARISON_TIME_UNAVAILABLE'
    request.snapshot_time=None; b.snapshots=[]
    result=service.compare(request)
    assert result.field_a is None and result.color_min is None and result.field_reason


def test_api_verifies_identity_readiness_variables_and_time(complete,store,client):
    _,r,_=complete
    payload={'run_a':r.run_id,'run_b':r.run_id,'field':'pressure','snapshot_time':.04}
    response=client.post('/api/v2/comparisons',json=payload)
    assert response.status_code == 200, response.json
    assert response.json['data']['field_a']['field_id'] == 'pressure'
    assert response.json['data']['a']['result_hash'] == response.json['data']['b']['result_hash']
    assert client.post('/api/v2/comparisons',json={**payload,'snapshot_time':.01}).status_code == 409
    assert client.post('/api/v2/comparisons',json={**payload,'field':'invalid'}).status_code == 400
    assert client.post('/api/v2/comparisons',json={**payload,'path':'bad'}).status_code == 400
    assert client.post('/api/v2/comparisons',json={**payload,'run_b':'unknown'}).status_code == 404
    pending=store.create(body())
    assert client.post('/api/v2/comparisons',json={**payload,'run_b':pending.run_id}).status_code == 409


def test_tampered_output_never_compares(complete,store,client):
    _,r,_=complete
    def drift(run): raise RuntimeError('RUN_OUTPUT_DRIFT')
    store.adapter.postprocess=drift
    assert client.post('/api/v2/comparisons',json={'run_a':r.run_id,'run_b':r.run_id}).status_code == 500
