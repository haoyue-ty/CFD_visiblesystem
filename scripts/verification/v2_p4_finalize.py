"""Read-only P4 final manifest, V1 compatibility and current contract assertions."""
import json
import subprocess
import xml.etree.ElementTree as ET

from backend.core.settings import WORKSPACE_ROOT
from backend.solver_runtime.artifacts import write_json, sha256
from backend.solver_runtime.binding import ScientificBinding
from backend.solver_runtime.case8_adapter import MANIFEST


def suite(path):
    node = ET.parse(path).getroot()
    suites = node.findall('testsuite') if node.tag == 'testsuites' else [node]
    return {key: sum(float(s.attrib.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped', 'time')}


def main():
    out = WORKSPACE_ROOT / 'docs/v2'
    original = json.loads(subprocess.check_output(['git', 'show', 'HEAD:config/openapi.json'], cwd=WORKSPACE_ROOT))
    current = json.loads((WORKSPACE_ROOT / 'config/openapi.json').read_text(encoding='utf-8'))
    for key, value in original['paths'].items():
        assert current['paths'][key] == value, key
    for key, value in original['components']['schemas'].items():
        assert current['components']['schemas'][key] == value, key
    backend = suite(out / 'p4_backend_results.xml')
    assert backend['errors'] == backend['failures'] == 0
    browser = json.loads((WORKSPACE_ROOT / '.cache/phase11/playwright.json').read_text(encoding='utf-8'))['stats']
    assert browser['unexpected'] == browser['flaky'] == 0
    binding = ScientificBinding(MANIFEST)
    source = json.loads((out / 'p4_source_preservation.json').read_text())
    assert source['status'] == 'PASS'
    live = json.loads((out / 'p4_live_acceptance.json').read_text(encoding='utf-8'))
    ui = json.loads((out / 'p4_browser_acceptance.json').read_text(encoding='utf-8'))
    assert live['status'] == ui['status'] == 'PASS'
    for check in live['checks'].values():
        assert check['status'] == 'PASS'
    report = dict(status='PASS', backend=backend, browser=browser,
        v1_contract_subset=dict(paths=len(original['paths']), schemas=len(original['components']['schemas']), identical=True),
        dependency_manifest_files=len(binding.manifest['files']), source_preservation=source,
        public_contract=dict(paths=len(current['paths']), schemas=len(current['components']['schemas']),
            openapi_sha256=sha256(WORKSPACE_ROOT / 'config/openapi.json'), types_sha256=sha256(WORKSPACE_ROOT / 'frontend/src/types/generated/api.d.ts')),
        real_runs={name: dict(run_id=check['run_id'], result_hash=check.get('result_hash')) for name, check in live['checks'].items()},
        live_science='PASS', current_browser='PASS', git_head=subprocess.check_output(['git','rev-parse','HEAD'], cwd=WORKSPACE_ROOT, text=True).strip(),
        git_committed=False, git_pushed=False)
    write_json(out, 'p4_final_checks.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
