import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError
import pytest
from backend.ai.client import DeepSeekClient
from backend.core.settings import Settings
from backend.services.v2.experiments import ExperimentError
from tests.v2_p1.test_ai_client import FakeResponse


def make(monkeypatch, tmp_path, **settings):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'sensitive-secret')
    return DeepSeekClient(Settings(**settings), audit_root=tmp_path/'audit')


def response():
    return FakeResponse(json.dumps(dict(choices=[dict(finish_reason='stop',message=dict(content='{"ok":true}'))],
        usage=dict(prompt_tokens=10,completion_tokens=5,total_tokens=15,secret='private'))).encode())


def test_retry_only_transient_errors_with_safe_usage(monkeypatch,tmp_path):
    client = make(monkeypatch,tmp_path)
    calls=[]
    def open(req, timeout):
        calls.append(timeout)
        if len(calls)==1: raise HTTPError('private',429,'secret',{},None)
        return response()
    client._opener=SimpleNamespace(open=open)
    assert client.complete_json('json','test') == '{"ok":true}'
    records=[json.loads(p.read_text()) for p in (tmp_path/'audit/calls').glob('*.json')]
    assert len(records)==2 and {r['status'] for r in records}=={'SUCCESS','AI_UNAVAILABLE'}
    assert [r for r in records if r['status']=='SUCCESS'][0]['usage']==dict(prompt_tokens=10,completion_tokens=5,total_tokens=15)
    assert len(calls)==2 and calls[1]<calls[0]
    assert not any('sensitive-secret' in json.dumps(r) or 'private' in json.dumps(r) for r in records)


@pytest.mark.parametrize('code',[401,403,302,400])
def test_permanent_errors_never_retry(monkeypatch,tmp_path,code):
    client=make(monkeypatch,tmp_path); calls=[]
    def open(*args,**kwargs):
        calls.append(1); raise HTTPError('private',code,'secret',{},None)
    client._opener=SimpleNamespace(open=open)
    with pytest.raises(ExperimentError):client.complete_json('json','test')
    assert len(calls)==1


def test_daily_reservation_and_input_limit_prevent_network(monkeypatch,tmp_path):
    client=make(monkeypatch,tmp_path, ai_daily_token_budget=4096, ai_max_input_chars=24000)
    calls=[]
    def no_usage(*a,**kw):
        calls.append(1)
        return FakeResponse(json.dumps(dict(choices=[dict(finish_reason='stop',message=dict(content='{"ok":true}'))])).encode())
    client._opener=SimpleNamespace(open=no_usage)
    client.complete_json('json','test')
    with pytest.raises(ExperimentError) as error:client.complete_json('json','test')
    assert error.value.code=='AI_BUDGET_LIMIT' and len(calls)==1
    with pytest.raises(ExperimentError) as error:client.complete_json('x'*24001,'test')
    assert error.value.code=='AI_INPUT_LIMIT' and len(calls)==1


def test_completed_usage_reconciles_reservation_once(monkeypatch,tmp_path):
    client=make(monkeypatch,tmp_path, ai_daily_token_budget=4096)
    client._opener=SimpleNamespace(open=lambda *a,**kw:response())
    for _ in range(3):client.complete_json('json','test')
    budget=json.loads((tmp_path/'audit/budget.json').read_text())
    assert len(budget['refunded_calls'])==2
    assert budget['reserved_tokens']==30+len(b'jsontest')+2048+128


def test_retry_limit_and_timeout_classification(monkeypatch,tmp_path):
    client=make(monkeypatch,tmp_path,deepseek_max_retries=2);calls=[]
    def open(*args,**kwargs):calls.append(1);raise TimeoutError
    client._opener=SimpleNamespace(open=open)
    with pytest.raises(ExperimentError):client.complete_json('json','test')
    assert len(calls)==3
    records=[json.loads(p.read_text()) for p in (tmp_path/'audit/calls').glob('*.json')]
    assert all(r['error_class']=='TIMEOUT' for r in records)
