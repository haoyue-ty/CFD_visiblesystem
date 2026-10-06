"""Explicit live-provider acceptance. Reads only the backend environment key.

Not part of pytest and never launches CFD. Each request is user-authorized P1
configuration parsing. Store safe DTOs and assertions, never headers/credentials.
"""
import argparse
import json
from pathlib import Path

from backend import create_app
from backend.registry.v2.cases import CAPABILITY_REVISION, templates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/v2/p1_live_ai_results.json'))
    args = parser.parse_args()
    app = create_app()
    if not app.extensions['ai_client'].available:
        raise SystemExit('Backend DEEPSEEK_API_KEY is required; no live request made.')
    client = app.test_client()
    paper = next(t for t in templates() if t.template_id == 'case8.paper.D_u')
    baseline = client.post('/api/v2/experiments/validate', json={
        'config': paper.config.model_dump(mode='json'), 'submission': {
            'input_mode':'template', 'template_id':paper.template_id, 'capability_revision':CAPABILITY_REVISION,
        },
    }).json['data']
    scenarios = [
        ('equivalent-paper', '使用 Case 8 的 D_u 论文标准模板，保持模板的全部参数不变。', True),
        ('modified-paper', '使用 Case 8 的 D_u 论文标准模板，把 q_at 改为 0，其他保持模板不变。', True),
        ('fast-candidate', '使用 Case 8 的 fast 快速实验模板，保持已登记 fast 候选的参数不变。', True),
        ('unsupported-epsilon', '使用 Case 8 的 D_u 论文模板，epsilon=0.0001。', False),
        ('ambiguous-paper', '创建 Case 8 论文标准实验，选择更稳定的配置。', False),
        ('unsupported-mach', '使用 Case 8 的 D_u 论文模板，把 Mach 改为 5。', False),
    ]
    rows = []
    for name, text, ready in scenarios:
        response = client.post('/api/v2/experiments/parse-natural-language', json={
            'text':text, 'capability_revision':CAPABILITY_REVISION,
        })
        payload = response.json
        checks = {'http_200':response.status_code == 200, 'readiness':False,
                  'no_execution':not any('/runs' in rule.rule for rule in app.url_map.iter_rules()
                                        if rule.rule.startswith('/api/v2/'))}
        if response.status_code == 200:
            draft = payload['data']
            checks['readiness'] = draft['ready_for_confirmation'] == ready
            if ready:
                checks['validated'] = draft['validated'] is not None and not draft['validated']['execution_available']
            else:
                checks['unresolved_or_unsupported'] = bool(draft['unresolved_fields'] or draft['unsupported_fields'])
                checks['not_validated'] = draft['validated'] is None
            if name == 'equivalent-paper':
                checks['same_normalized_config'] = draft['validated'] is not None and draft['validated']['normalized_config'] == baseline['normalized_config']
                checks['same_config_hash'] = draft['validated'] is not None and draft['validated']['config_hash'] == baseline['config_hash']
            if name == 'modified-paper':
                checks['lineage_preserved'] = (draft['template_id'] == paper.template_id and draft['validated'] is not None
                                              and draft['validated']['classification'] == 'PAPER_SCALE_CUSTOM')
                checks['explicit_parameter'] = draft['config'] is not None and draft['config']['method']['q_at'] == 0
            if name == 'fast-candidate':
                checks['benchmarked_fast'] = (draft['template_id'] == 'case8.fast.D_u' and draft['validated'] is not None
                                             and draft['validated']['classification'] == 'LIVE_FAST_RUN')
        passed = all(checks.values())
        rows.append({'scenario':name, 'status':'PASS' if passed else 'FAIL', 'http_status':response.status_code,
                     'checks':checks, 'response':payload})
        print(json.dumps({'scenario':name, 'status':rows[-1]['status'], 'http_status':response.status_code}), flush=True)
        # Preserve all completed scenarios even when a subsequent call fails.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'status':'PASS' if all(r['status'] == 'PASS' for r in rows) else 'FAIL',
            'model':app.extensions['ai_client'].model, 'scenarios':rows, 'cfd_runs_started':0},
            ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not all(row['status'] == 'PASS' for row in rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
