"""Independent P7 receipt/identity, real science, contract and source checks."""
import json
import subprocess

from backend.core.settings import Settings, WORKSPACE_ROOT
from backend.models.v2.comparison import CompareRunsRequest
from backend.services.v2.comparison import ComparisonService
from backend.services.v2.results import ScientificResultService
from backend.services.v2.sweeps import SweepService
from backend.solver_runtime.artifacts import sha256, utc_now, write_json
from backend.solver_runtime.run_store import RunStore
from scripts.verification.v2_p4_finalize import suite


def main():
    out = WORKSPACE_ROOT/'docs/v2'
    live = json.loads((out/'p7_live_acceptance.json').read_text(encoding='utf-8'))
    assert live['status'] == 'PASS' and len(live['checks']) == 6
    backend, targeted = [suite(out/f'p7_{name}_results.xml') for name in ('backend','targeted')]
    for report in (backend,targeted): assert report['failures'] == report['errors'] == 0
    first_browser = json.loads((WORKSPACE_ROOT/'.cache/phase11/playwright.json').read_text(encoding='utf-8'))
    browsers = {name: json.loads(path.read_text(encoding='utf-8'))['stats'] for name,path in
        (('v1_recheck',out/'p7_v1_recheck.json'),('p7',out/'p7_browser_acceptance.json'))}
    for report in browsers.values(): assert report['unexpected'] == report['flaky'] == 0
    def specs(suites):
        return [spec for s in suites for spec in s.get('specs',[])] + [spec for s in suites for spec in specs(s.get('suites',[]))]
    incident = None
    if first_browser['stats']['unexpected']:
        assert first_browser['stats']['expected'] == 224 and first_browser['stats']['unexpected'] == 1
        failed = [s for s in specs(first_browser['suites']) if not s['ok']]
        assert len(failed) == 1 and failed[0]['title'] == 'template and form share hash, paper changes preserve lineage, confirmation invalidates'
        failure_text = json.dumps(failed[0],ensure_ascii=False)
        assert 'execution-ready' in failure_text and '后台运行服务在线' in failure_text
        recheck = json.loads((out/'p7_v1_recheck.json').read_text(encoding='utf-8'))
        assert any(s['title'] == failed[0]['title'] and s['ok'] for s in specs(recheck['suites']))
        incident = 'First existing suite shared the live verifier manager; its owner exited before the online-capability test. 224 passed, one service-availability failure; the unchanged failing test and affected entropy/chart flows pass in an isolated server recheck.'
    else:
        assert first_browser['stats']['expected'] == 225 and first_browser['stats']['flaky'] == 0
    browsers['existing_first_attempt'] = first_browser['stats']
    source = json.loads((out/'p7_source_preservation.json').read_text(encoding='utf-8'))
    assert source['status'] == 'PASS'
    original = json.loads(subprocess.check_output(['git','show','HEAD:config/openapi.json'],cwd=WORKSPACE_ROOT))
    current = json.loads((WORKSPACE_ROOT/'config/openapi.json').read_text(encoding='utf-8'))
    assert all(current['paths'][key] == value for key,value in original['paths'].items())
    assert all(current['components']['schemas'][key] == value for key,value in original['components']['schemas'].items())
    store = RunStore(Settings())
    sweeps, science, comparisons = SweepService(store), ScientificResultService(store), ComparisonService(store)
    scan = live['checks']['real_four_combination_serial_scan']
    sweep = sweeps.get(scan['sweep_id'])
    assert sweep.status == 'COMPLETED' and sweep.successful_tasks == 4
    results=[]
    for item, receipt in zip(sweep.items,scan['results']):
        result, evidence = science.result(item.run.run_id), science.evidence(item.run.run_id)
        assert result.result_hash == receipt['result_hash']
        assert result.config.config_hash == item.config_hash == receipt['config_hash']
        config = result.config.normalized_config
        assert (config.method.q_aa, config.method.q_at) == (item.q_aa,item.q_at)
        assert evidence.effective_config['normalized_config'] == config.model_dump(mode='json')
        assert result.entropy.totals == receipt['entropy']
        assert [m.model_dump(mode='json') for m in result.metrics] == receipt['metrics']
        assert result.allocation.availability == 'AVAILABLE'
        if item.q_at == 0.:
            assert result.entropy.totals['E_at'] == 0.
            assert all(v == 0. for face in result.allocation.arrays if face.channel == 'at' for v in face.values)
        results.append(dict(run_id=item.run.run_id,result_hash=result.result_hash,config_hash=item.config_hash,
            q_aa=item.q_aa,q_at=item.q_at,accepted_steps=result.runtime.accepted_steps,
            solver_seconds=result.runtime.solver_seconds,output_hashes_verified=len(evidence.outputs)))
    for a,b in zip(sweep.items,sweep.items[1:]): assert a.run.finished_at <= b.run.started_at
    query=CompareRunsRequest(run_a=sweep.items[0].run.run_id,run_b=sweep.items[1].run.run_id)
    comparison=comparisons.compare(query)
    assert comparison.same_conditions and len(comparison.common_snapshot_times) == 6
    assert comparison.field_a.time == comparison.field_b.time == .04
    assert comparison.color_min == min(comparison.field_a.minimum,comparison.field_b.minimum)
    assert comparison.color_max == max(comparison.field_a.maximum,comparison.field_b.maximum)
    query.run_b=live['checks']['non_matching_grid_no_ranking']['run_b']
    mismatch=comparisons.compare(query)
    assert not mismatch.same_conditions and all(m.b_minus_a is None for m in mismatch.metrics)
    cancelled=sweeps.get(live['checks']['cancel_real_active_worker']['record']['sweep_id'])
    assert cancelled.status == 'CANCELLED' and cancelled.items[0].run.status == 'CANCELLED'
    assert all(i.status == 'SKIPPED' and i.run is None for i in cancelled.items[1:])
    timed=sweeps.get(live['checks']['real_time_budget']['record']['sweep_id'])
    assert timed.status == 'FAILED' and timed.failure == 'SWEEP_TIME_BUDGET_EXCEEDED'
    paths=['backend/models/v2/comparison.py','backend/models/v2/sweep.py','backend/services/v2/comparison.py',
        'backend/services/v2/sweeps.py','backend/api/v2/comparison.py','backend/api/v2/errors.py',
        'backend/solver_runtime/run_manager.py','frontend/src/pages/RunComparisonPage.vue','frontend/src/pages/ParameterSweepPage.vue',
        'frontend/src/views/runs/ComparisonField.vue','frontend/src/views/runs/p7.css','frontend/src/scientific/EntropyChart.vue',
        'frontend/src/data/v2/comparison.ts','frontend/live-tests/v2-p7.spec.ts','scripts/verification/v2_p7_browser.mjs',
        'scripts/verification/v2_p7_finalize.py','tests/v2_p7/test_comparison.py','tests/v2_p7/test_sweeps.py']
    report=dict(status='PASS',checked_at=utc_now(),backend=backend,targeted=targeted,browsers=browsers,
        real_scan=dict(sweep_id=sweep.sweep_id,results=results,serial_execution=True),
        comparison_same_conditions=True,comparison_grid_mismatch=True,active_cancel=True,time_budget=True,
        browser_environment_incident=incident,
        source_preservation=source,v1_contract_subset=dict(paths=len(original['paths']),
            schemas=len(original['components']['schemas']),identical=True),
        current_contract=dict(paths=len(current['paths']),schemas=len(current['components']['schemas']),
            openapi_sha256=sha256(WORKSPACE_ROOT/'config/openapi.json'),types_sha256=sha256(WORKSPACE_ROOT/'frontend/src/types/generated/api.d.ts')),
        delivered_files=[dict(path=p,sha256=sha256(WORKSPACE_ROOT/p)) for p in paths],
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORKSPACE_ROOT,text=True).strip(),
        git_committed=False,git_pushed=False)
    write_json(out,'p7_final_checks.json',report)
    print(json.dumps(dict(status='PASS',backend=backend,targeted=targeted,browsers=browsers,real_scan=report['real_scan']),ensure_ascii=False))


if __name__ == '__main__': main()
