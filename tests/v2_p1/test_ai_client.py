import io
import json
import socket
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from backend.ai.client import DeepSeekClient, NoRedirects
from backend.core.settings import Settings
from backend.services.v2.experiments import ExperimentError


@pytest.fixture(autouse=True)
def isolated_audit(monkeypatch, tmp_path):
    monkeypatch.setattr('backend.ai.client.WORKSPACE_ROOT', tmp_path)


class FakeResponse(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.timeouts = []
        self.fp = SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(settimeout=self.timeouts.append)))


def make_client(monkeypatch, body=None, failure=None):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-private-key')
    client = DeepSeekClient(Settings(deepseek_max_retries=0))
    calls = []
    response = FakeResponse(body or b'{}')

    def open_request(request, timeout):
        calls.append(request)
        assert 0 < timeout <= 30
        if failure:
            raise failure
        return response

    client._opener = SimpleNamespace(open=open_request)
    return client, calls, response


def test_client_uses_backend_secret_and_bounded_json_mode(monkeypatch):
    provider = {'choices':[{'finish_reason':'stop', 'message':{'content':'{"ok":true}'}}]}
    client, calls, response = make_client(monkeypatch, json.dumps(provider).encode())
    assert client.complete_json('json prompt', 'D_u') == '{"ok":true}'
    assert len(calls) == 1 and response.closed
    request = calls[0]
    body = json.loads(request.data)
    assert request.full_url == 'https://api.deepseek.com/chat/completions'
    assert request.get_header('Authorization') == 'Bearer test-private-key'
    assert b'test-private-key' not in request.data
    assert body['model'] == 'deepseek-flash'
    assert body['response_format'] == {'type':'json_object'}
    assert body['max_tokens'] == 2048 and not body['stream']
    assert not {'tools','tool_choice'} & body.keys()
    assert response.timeouts and all(0 < n <= 30 for n in response.timeouts)


def test_missing_key_does_not_access_network(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    client = DeepSeekClient(Settings())
    with pytest.raises(ExperimentError) as caught:
        client.complete_json('json', 'D_u')
    assert caught.value.status == 503 and not client.available


def test_content_length_response_can_close_after_final_chunk(monkeypatch):
    provider = {'choices':[{'finish_reason':'stop', 'message':{'content':'{"ok":true}'}}]}
    client, _, response = make_client(monkeypatch, json.dumps(provider).encode())
    original_read = response.read1

    def final_chunk(size):
        chunk = original_read(size)
        response.fp = None
        return chunk

    response.read1 = final_chunk
    assert client.complete_json('json', 'D_u') == '{"ok":true}'
    assert response.closed


@pytest.mark.parametrize('failure,retryable', [
    (TimeoutError(),True), (socket.timeout(),True), (URLError('sensitive/path'),True),
    (HTTPError('secret',401,'private key',{},None),False),
    (HTTPError('secret',429,'private key',{},None),True),
    (HTTPError('secret',500,'private key',{},None),True),
    (HTTPError('secret',302,'redirect',{},None),False),
])
def test_provider_errors_are_safe_and_do_not_retry(monkeypatch, failure, retryable):
    client, calls, _ = make_client(monkeypatch, failure=failure)
    with pytest.raises(ExperimentError) as caught:
        client.complete_json('json', 'D_u')
    assert caught.value.code == 'AI_UNAVAILABLE' and caught.value.retryable == retryable
    assert len(calls) == 1
    assert not any(s in caught.value.message for s in ('secret','sensitive','private key','test-private-key'))


@pytest.mark.parametrize('body', [b'{}', b'bad json', b' ' * 262145,
    json.dumps({'choices':[{'finish_reason':'length', 'message':{'content':'{}'}}]}).encode(),
    json.dumps({'choices':[{'finish_reason':'stop', 'message':{'content':''}}]}).encode(),
], ids=['empty-object', 'invalid-json', 'oversized', 'truncated', 'empty-content'])
def test_malformed_truncated_empty_and_oversized_provider_output(monkeypatch, body):
    client, calls, response = make_client(monkeypatch, body)
    with pytest.raises(ExperimentError) as caught:
        client.complete_json('json', 'D_u')
    assert caught.value.code == 'AI_INVALID_OUTPUT'
    assert len(calls) == 1 and response.closed


@pytest.mark.parametrize('url', ['http://api.deepseek.com', 'https://example.org', 'https://api.deepseek.com.evil.org',
    'https://user:password@api.deepseek.com', 'https://api.deepseek.com/other', 'https://api.deepseek.com?key=secret'])
def test_non_official_endpoints_rejected(url):
    with pytest.raises(ValueError):
        DeepSeekClient(Settings(deepseek_base_url=url))


def test_no_redirects_protects_authorization():
    assert NoRedirects().redirect_request(None,None,302,'',{},'https://other') is None
