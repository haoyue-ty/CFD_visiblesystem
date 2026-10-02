"""Read-only Window3 acceptance aggregation; never imports scientific solvers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / 'docs/handoffs/phase9'
ARTIFACTS = ROOT / '.cache/phase9-closure'


def read(name):
    return json.loads((ARTIFACTS / name).read_text(encoding='utf-8'))


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((HANDOFF / 'WINDOW2_SOURCE_BEFORE.json').read_text(encoding='utf-8'))
    after = {}
    for name in baseline:
        path = Path(name)
        data = path.read_bytes()
        after[name] = {'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    closure = Path('D:/Paper/passage6/experiments/entropy_budget_closure')
    file_set_equal = {p.as_posix() for p in closure.rglob('*') if p.is_file()} == {
        name for name in baseline if name.startswith(closure.as_posix() + '/')
    }
    preservation = {
        'status': 'PASS' if baseline == after and file_set_equal else 'FAIL',
        'compared_files': len(after), 'closure_file_set_equal': file_set_equal,
        'before_after_sizes_and_sha256_equal': baseline == after,
        'scientific_files_modified': baseline != after or not file_set_equal,
        'cfd_runs_started': 0, 'files_after': after,
    }
    (ARTIFACTS / 'WINDOW3_SOURCE_PRESERVATION.json').write_text(json.dumps(preservation, indent=2) + '\n', encoding='utf-8')
    assert preservation['status'] == 'PASS', 'Scientific source preservation failed'
    browser = read('WINDOW3_PLAYWRIGHT.json')['stats']
    assert browser['unexpected'] == browser['flaky'] == browser['skipped'] == 0
    assert browser['expected'] >= 20
    suites = ET.parse(ARTIFACTS / 'WINDOW3_BACKEND_REGRESSION.xml').getroot()
    backend = {key: sum(int(s.get(key, 0)) for s in suites.iter('testsuite')) for key in ('tests', 'failures', 'errors', 'skipped')}
    assert backend['failures'] == backend['errors'] == backend['skipped'] == 0
    scan = read('WINDOW3_PRODUCTION_SCAN.json')
    assert scan['status'] == 'PASS' and not scan['mock_in_production'] and not scan['matches']
    build = read('WINDOW3_FRONTEND_BUILD.json')
    assert build['exit_code'] == 0 and build['typescript_check'] == build['vite_build'] == 'PASS'
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    assert branch == 'phase9/closure-ui'
    accepted_changes = subprocess.check_output(['git', 'diff', 'HEAD', '--name-only', '--', 'backend', 'config', 'data',
                                               'docs/handoffs/phase9/WINDOW_1_CLOSURE_ADAPTER.md',
                                               'docs/handoffs/phase9/WINDOW_2_CLOSURE_API.md',
                                               'docs/handoffs/phase9/PHASE9_CLOSURE_SOURCE_MAP.json'], cwd=ROOT, text=True)
    assert not accepted_changes.strip(), 'Accepted W1/W2 contracts changed'
    report = {
        'WINDOW': '3_CLOSURE_FRONTEND', 'STATUS': 'PASS', 'branch': branch,
        **{key: 'PASS' for key in ('OVERVIEW', 'SEMIDISCRETE', 'FULLY_DISCRETE', 'REFINEMENT',
                                  'BU_ZERO_CHANNEL', 'NO_SPATIAL_TRAJECTORY', 'EVIDENCE')},
        'BUILD': 'PASS', 'TESTS': {'browser': browser['expected'], 'backend_regression': backend['tests'], 'failures': 0},
        'MOCK_IN_PRODUCTION': 'NO', 'scientific_files_modified': False, 'cfd_runs_started': 0,
        'accepted_w1_w2_unchanged': True,
        'history_page_size': 1000, 'history_display': 'Explicit saved record pages; all records reachable by pagination',
        'refinement_display': 'Four frozen D_u points; abs(R_total) versus CLO01 CFL; saved global/pairwise order against dt_eff; no fit line or frontend refit',
        'stage_display': 'G versus -D_total (explicit display sign); table retains D_total; original stage clock and source order',
    }
    (ARTIFACTS / 'WINDOW3_CLOSURE_FRONTEND_REPORT.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
