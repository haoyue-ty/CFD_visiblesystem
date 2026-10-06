"""Independent final P6 receipt, science, offline artifact and V1/source audit."""
import json
import re
import subprocess

from backend.ai.analysis import validate_prose
from backend.ai.context_builder import build_context
from backend.core.settings import WORKSPACE_ROOT, Settings
from backend.models.v2.ai import AIAnalysis, AIViewSelection
from backend.services.v2.reports import ReportService
from backend.services.v2.results import ScientificResultService
from backend.solver_runtime.artifacts import write_json, sha256, utc_now
from backend.solver_runtime.binding import ScientificBinding
from backend.solver_runtime.case8_adapter import MANIFEST
from backend.solver_runtime.run_store import RunStore
from scripts.verification.v2_p4_finalize import suite


def main():
    out=WORKSPACE_ROOT/'docs/v2'
    original=json.loads(subprocess.check_output(['git','show','HEAD:config/openapi.json'],cwd=WORKSPACE_ROOT))
    current=json.loads((WORKSPACE_ROOT/'config/openapi.json').read_text(encoding='utf-8'))
    assert all(current['paths'][k]==v for k,v in original['paths'].items())
    assert all(current['components']['schemas'][k]==v for k,v in original['components']['schemas'].items())
    backend=suite(out/'p6_backend_results.xml')
    targeted=suite(out/'p6_targeted_results.xml')
    for check in (backend,targeted):
        assert check['failures']==check['errors']==0
    browser=json.loads((WORKSPACE_ROOT/'.cache/phase11/playwright.json').read_text(encoding='utf-8'))['stats']
    assert browser['unexpected']==browser['flaky']==0
    source=json.loads((out/'p6_source_preservation.json').read_text(encoding='utf-8'))
    assert source['status']=='PASS'
    live=json.loads((out/'p6_live_acceptance.json').read_text(encoding='utf-8'))
    assert live['status']=='PASS' and len(live['scenarios'])==3
    assert len({s['run_id'] for s in live['scenarios']})==3
    assert len({s['config_hash'] for s in live['scenarios']})==1
    binding=ScientificBinding(MANIFEST)
    store=RunStore(Settings())
    reports=[]
    for scenario in live['scenarios']:
        run_id=scenario['run_id']
        class Offline:
            available=False
            model=scenario['receipt']['ai_model']
            def complete_json(self,*args):
                raise AssertionError('Final report audit never contacts provider')
        service=ReportService(store,Offline())
        metadata=service.status(run_id)
        assert metadata.model_dump(mode='json')==scenario['receipt']
        exported=WORKSPACE_ROOT/scenario['saved_html']
        assert sha256(exported)==metadata.html_sha256
        assert exported.read_text(encoding='utf-8')==service.html(run_id)
        html=exported.read_text(encoding='utf-8')
        data=json.loads(re.search(r'<script type="application/json" id="report-data">(.*?)</script>',html,re.S).group(1))
        scientific=ScientificResultService(store).result(run_id)
        assert data['result_hash']==scientific.result_hash==scenario['result_hash']
        assert data['config']==scientific.config.model_dump(mode='json')
        assert data['runtime']==scientific.runtime.model_dump(mode='json')
        assert data['metrics']==[m.model_dump(mode='json') for m in scientific.metrics]
        assert data['entropy']==scientific.entropy.model_dump(mode='json')
        context=build_context(store,run_id)
        assert data['ai_context']==context.model_dump(mode='json')
        validate_prose(AIAnalysis.model_validate_json(json.dumps(data['ai'])).interpretation,context)
        answer=AIAnalysis.model_validate_json(json.dumps(scenario['assistant']))
        view=answer.current_view
        selection=AIViewSelection(snapshot_id=view.snapshot_id,field=view.field,**(view.region or {}))
        chat_context=build_context(store,run_id,selection)
        assert view==chat_context.current_view
        validate_prose(answer.assistant,chat_context)
        assert not re.search(r'(?:src|href)="(?:https?://|/api/|runtime/)',html)
        assert len(re.findall(r'<section id=',html))==12 and len(re.findall(r'<svg ',html))==4
        reports.append(dict(run_id=run_id,input_mode=scenario['mode'],result_hash=scientific.result_hash,
            report_id=metadata.report_id,html_sha256=metadata.html_sha256,size_bytes=metadata.size_bytes,
            offline_validated_with_provider_disabled=True))
    files=['backend/models/v2/report.py','backend/services/v2/reports.py','backend/services/v2/report_renderer.py',
        'backend/api/v2/reports.py','backend/ai/analysis.py','frontend/src/pages/RunReportPage.vue',
        'frontend/src/data/v2/reports.ts','frontend/src/router.ts','frontend/src/pages/RunWorkspacePage.vue',
        'scripts/verification/v2_p6_browser.mjs','scripts/verification/v2_p6_finalize.py']
    report=dict(status='PASS',checked_at=utc_now(),backend=backend,targeted=targeted,browser=browser,
        live_three_entry_closed_loop='PASS',reports=reports,report_provider_calls=0,
        v1_contract_subset=dict(paths=len(original['paths']),schemas=len(original['components']['schemas']),identical=True),
        current_contract=dict(paths=len(current['paths']),schemas=len(current['components']['schemas']),
            openapi_sha256=sha256(WORKSPACE_ROOT/'config/openapi.json'),types_sha256=sha256(WORKSPACE_ROOT/'frontend/src/types/generated/api.d.ts')),
        dependency_files=len(binding.manifest['files']),source_preservation=source,
        delivered_files=[dict(path=p,sha256=sha256(WORKSPACE_ROOT/p)) for p in files],
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORKSPACE_ROOT,text=True).strip(),
        git_committed=False,git_pushed=False)
    write_json(out,'p6_final_checks.json',report)
    print(json.dumps(dict(status='PASS',backend=backend,targeted=targeted,browser=browser,reports=reports),ensure_ascii=False))


if __name__=='__main__':main()
