import json
import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path

import numpy as np
import pytest

from backend import create_app
from backend.ai.analysis import ScientificAIService
from backend.ai.context_builder import build_context
from backend.services.v2.reports import ReportService
from backend.services.v2.results import ScientificResultService
from backend.solver_runtime.artifacts import output_inventory, write_json, sha256
from backend.solver_runtime.run_store import file_lock
from tests.v2_p3.test_runs import store, body
from tests.v2_p4.test_results import complete
from tests.v2_p5.test_analysis import Provider, provider


@pytest.fixture
def api(store, provider):
    return create_app(run_store=store, ai_client=provider, case8_adapter=None, allocation_adapter=None,
        spectral_adapter=None, cylinder_adapter=None, closure_adapter=None).test_client()


def embedded(html):
    return json.loads(re.search(r'<script type="application/json" id="report-data">(.*?)</script>', html, re.S).group(1))


def test_deterministic_report_without_provider_is_complete_and_offline(complete, store, provider, api):
    root, record, _ = complete
    inventory = output_inventory(root)
    url = f'/api/v2/reports/{record.run_id}'
    assert api.get(url).json['data']['status'] == 'NOT_GENERATED'
    assert api.get(url+'/html').status_code == 409
    metadata = api.post(url).json['data']
    assert metadata['status'] == 'READY' and metadata['ai_status'] == 'UNAVAILABLE'
    response = api.get(url+'/html')
    assert response.status_code == 200 and response.mimetype == 'text/html'
    assert 'sandbox' in response.headers['Content-Security-Policy']
    html = response.get_data(as_text=True)
    assert len(re.findall(r'<section id=',html)) == 12
    assert html.count('<svg ') == 4
    assert not re.search(r'(?:src|href)="(?:https?://|/api/|runtime/)',html)
    data = embedded(html)
    result = ScientificResultService(store).result(record.run_id)
    context = build_context(store, record.run_id)
    assert data['config'] == result.config.model_dump(mode='json')
    assert data['runtime'] == result.runtime.model_dump(mode='json')
    assert data['metrics'] == context.metrics
    assert data['entropy']['totals'] == context.entropy['totals']
    assert all(m['value'] == 0. and m['availability'] == 'AVAILABLE' for m in data['metrics'])
    assert data['ai_context'] == context.model_dump(mode='json')
    assert data['charts'][0]['snapshot_id'] == 'step_000001'
    assert metadata['html_sha256'] == sha256(root/f"report/{metadata['report_id']}.html")
    assert api.post(url).json['data'] == metadata
    assert api.get(url+'/html').data == response.data
    assert not provider.calls
    assert output_inventory(root) == inventory


def test_ai_cache_changes_report_version_and_works_with_offline_provider(complete, store, provider, api):
    root, record, _ = complete
    url = f'/api/v2/reports/{record.run_id}'
    old = api.post(url).json['data']
    analysis = ScientificAIService(store,provider).interpret(record.run_id)
    provider.complete_json = lambda *args: (_ for _ in ()).throw(AssertionError('No provider call'))
    assert api.get(url).json['data']['status'] == 'STALE'
    assert api.get(url+'/html').status_code == 409
    new = api.post(url).json['data']
    assert new['ai_status'] == 'AVAILABLE' and new['report_id'] != old['report_id']
    html = api.get(url+'/html').get_data(as_text=True)
    assert analysis.interpretation.summary.text in html
    assert embedded(html)['ai']['evidence'] == [f.model_dump(mode='json') for f in analysis.evidence]
    assert new['ai_prompt_version'] == analysis.prompt_version
    assert (root/f"report/{old['report_id']}.html").exists()
    assert len(provider.calls) == 1


def test_user_text_is_escaped_even_in_embedded_json(complete, store, provider, api):
    root, record, _ = complete
    request = json.loads((root/'request.json').read_text())
    payload = '</script><script>alert("injected")</script><img src="https://bad/" onerror="alert(1)">&'
    request['submission']['input_mode'] = 'natural_language'
    request['submission']['natural_language_text'] = payload
    request['submission']['parser_version'] = 'test-parser'
    write_json(root,'request.json',request)
    response = api.post(f'/api/v2/reports/{record.run_id}')
    assert response.status_code == 200, response.json
    html = api.get(f'/api/v2/reports/{record.run_id}/html').get_data(as_text=True)
    assert payload not in html and '&lt;script&gt;' in html
    assert html.count('<script') == 1
    assert embedded(html)['submission']['natural_language_text'] == payload


def test_corrupt_ai_cache_degrades_without_unsafe_html(complete, store, provider, api):
    root, record, _ = complete
    ScientificAIService(store,provider).interpret(record.run_id)
    path = next((root/'ai').glob('interpret-*.json'))
    data = json.loads(path.read_text(encoding='utf-8'))
    data['interpretation']['summary']['text'] = '<script>alert("bad")</script>'
    path.write_text(json.dumps(data),encoding='utf-8')
    response = api.post(f'/api/v2/reports/{record.run_id}')
    assert response.status_code == 200, response.json
    assert response.json['data']['ai_status'] == 'UNAVAILABLE'
    assert '未通过' in response.json['data']['ai_reason']
    html = api.get(f'/api/v2/reports/{record.run_id}/html').get_data(as_text=True)
    assert 'alert' not in html and embedded(html)['ai'] is None


def test_missing_metrics_and_allocation_never_become_zero(complete, store, provider, api):
    root, record, _ = complete
    np.savez(root/'derived/physical_fields.npz',front=np.full(16,np.nan))
    url = f'/api/v2/reports/{record.run_id}'
    assert api.post(url).status_code == 200
    html = api.get(url+'/html').get_data(as_text=True)
    assert all(m['value'] is None and m['reason'] for m in embedded(html)['metrics'])
    assert '不可用' in html and 'UNAVAILABLE' in html


def test_unknown_or_incomplete_runs_reject_report_and_arbitrary_queries(store, provider, api):
    record = store.create(body())
    for method in ('get','post'):
        assert getattr(api,method)(f'/api/v2/reports/{record.run_id}').status_code == 409
        assert getattr(api,method)('/api/v2/reports/not-a-run').status_code == 404
    assert api.get(f'/api/v2/reports/{record.run_id}/html?path=secret').status_code == 400


@pytest.mark.parametrize('which',['html','identity','submission'])
def test_tampered_artifacts_are_rejected(complete, store, provider, api, which):
    root, record, _ = complete
    url=f'/api/v2/reports/{record.run_id}'
    metadata = api.post(url).json['data']
    if which == 'html':
        (root/f"report/{metadata['report_id']}.html").write_text('bad',encoding='utf-8')
    elif which == 'identity':
        metadata['run_id'] = 'other'
        write_json(root,'report/current.json',metadata)
    else:
        data=json.loads((root/'request.json').read_text())
        data['config']['method']['q_at'] = 0.
        write_json(root,'request.json',data)
    response=api.get(url+'/html')
    assert response.status_code == 500 and response.json['error']['code'] in ('REPORT_OUTPUT_INVALID','RUN_OUTPUT_INVALID')


def test_renderer_version_change_requires_new_report(complete, store, provider, api, monkeypatch):
    root, record, _=complete
    url=f'/api/v2/reports/{record.run_id}'
    old=api.post(url).json['data']
    monkeypatch.setattr('backend.services.v2.reports.REPORT_VERSION','case8.html.future')
    assert api.get(url).json['data']['status'] == 'STALE'
    new=api.post(url).json['data']
    assert new['report_id'] != old['report_id']


def test_same_run_generation_lock_returns_retryable_busy(complete, store, provider, api):
    root, record, _ = complete
    (root/'report').mkdir(exist_ok=True)
    with file_lock(root/'report/generate.lock'):
        response=api.post(f'/api/v2/reports/{record.run_id}')
    assert response.status_code == 429
    assert response.json['error']['code'] == 'REPORT_BUSY'
    assert response.json['error']['retryable']
    assert not (root/'report/current.json').exists()


def test_unknown_generation_does_not_create_report_directory(store, provider, api):
    unknown='00000000-0000-4000-8000-000000000000'
    assert api.post(f'/api/v2/reports/{unknown}').status_code == 404
    assert not (store.directory(unknown)/'report').exists()
