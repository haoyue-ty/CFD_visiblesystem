"""P5 evidence aggregation; no provider request and no CFD execution."""
import json
import subprocess
from backend.core.settings import WORKSPACE_ROOT, Settings
from backend.solver_runtime.artifacts import write_json, sha256, utc_now
from backend.solver_runtime.binding import ScientificBinding
from backend.solver_runtime.case8_adapter import MANIFEST
from backend.solver_runtime.run_store import RunStore
from backend.ai.analysis import ScientificAIService, validate_prose
from backend.ai.context_builder import build_context
from backend.ai.prompts import PROMPT_VERSION
from scripts.verification.v2_p4_finalize import suite


def main():
    out=WORKSPACE_ROOT/'docs/v2'
    original=json.loads(subprocess.check_output(['git','show','HEAD:config/openapi.json'],cwd=WORKSPACE_ROOT))
    current=json.loads((WORKSPACE_ROOT/'config/openapi.json').read_text(encoding='utf-8'))
    assert all(current['paths'][k]==v for k,v in original['paths'].items())
    assert all(current['components']['schemas'][k]==v for k,v in original['components']['schemas'].items())
    backend=suite(out/'p5_backend_results.xml'); targeted=suite(out/'p5_targeted_results.xml')
    v2=suite(out/'p5_v2_results.xml')
    for check in (backend,targeted,v2):assert check['failures']==check['errors']==0
    browser=json.loads((WORKSPACE_ROOT/'.cache/phase11/playwright.json').read_text(encoding='utf-8'))['stats']
    ui=json.loads((out/'p5_browser_acceptance.json').read_text(encoding='utf-8'))['stats']
    for check in (browser,ui):assert check['unexpected']==check['flaky']==0
    live=json.loads((out/'p5_live_ai_acceptance.json').read_text(encoding='utf-8'))
    assert live['status']=='PASS' and len(live['scenarios'])==6 and all(s['status']=='PASS' for s in live['scenarios'])
    assert live['cfd_runs_started']==live['refresh_provider_calls']==0
    source=json.loads((out/'p5_source_preservation.json').read_text())
    assert source['status']=='PASS'
    binding=ScientificBinding(MANIFEST)
    store=RunStore(Settings())
    class Offline:
        available=False
        model=live['model']
        def complete_json(self,*args):raise AssertionError('Finalize must not contact provider')
    service=ScientificAIService(store,Offline())
    for run_id in live['result_hashes']:
        cached=service.interpret(run_id)
        assert cached.cached and cached.result_hash==live['result_hashes'][run_id]
        assert cached.prompt_version==PROMPT_VERSION
        validate_prose(cached.interpretation,build_context(store,run_id))
    for scenario in live['scenarios']:
        data=scenario.get('analysis',{})
        if data.get('assistant'):
            from backend.models.v2.ai import AIAnalysis,AIViewSelection
            analysis=AIAnalysis.model_validate_json(json.dumps(data))
            c=analysis.current_view
            selection=AIViewSelection(snapshot_id=c.snapshot_id,field=c.field,**(c.region or {}))
            context=build_context(store,analysis.run_id,selection)
            assert c==context.current_view
            validate_prose(analysis.assistant,context)
    files=['backend/ai/client.py','backend/ai/context_builder.py','backend/ai/prompts.py','backend/ai/analysis.py',
        'backend/models/v2/ai.py','backend/api/v2/ai.py','frontend/src/views/runs/RunAIView.vue',
        'frontend/src/views/runs/AIClaimView.vue','frontend/src/views/runs/ScientificRunView.vue','frontend/src/data/v2/ai.ts']
    result=dict(status='PASS',checked_at=utc_now(),prompt_version=PROMPT_VERSION,backend=backend,
        targeted=targeted,v2_regression=v2,browser=browser,p5_browser=ui,
        v1_contract_subset=dict(paths=len(original['paths']),schemas=len(original['components']['schemas']),identical=True),
        current_contract=dict(paths=len(current['paths']),schemas=len(current['components']['schemas']),
            openapi_sha256=sha256(WORKSPACE_ROOT/'config/openapi.json'),types_sha256=sha256(WORKSPACE_ROOT/'frontend/src/types/generated/api.d.ts')),
        real_ai=dict(status='PASS',scenarios=len(live['scenarios']),model=live['model'],run_ids=list(live['result_hashes']),
            cfd_runs_started=0,refresh_provider_calls=0,cached_with_offline_provider=True),
        dependency_files=len(binding.manifest['files']),source_preservation=source,
        delivered_files=[dict(path=p,sha256=sha256(WORKSPACE_ROOT/p)) for p in files],
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORKSPACE_ROOT,text=True).strip(),
        git_committed=False,git_pushed=False)
    write_json(out,'p5_final_checks.json',result)
    print(json.dumps(dict(status='PASS',backend=backend,targeted=targeted,browser=browser,p5_browser=ui,real_ai=result['real_ai']),ensure_ascii=False))


if __name__=='__main__':main()
