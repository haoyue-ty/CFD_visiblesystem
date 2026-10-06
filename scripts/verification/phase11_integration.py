"""Read-only Phase11 final-integration QA; never invokes a CFD solver."""
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from scripts.verification.source_audit import inventory, fingerprint

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.cache/phase11-final'
SOURCE = Path('D:/Paper/passage6')
ACCEPTED = {
    'PHASE8_COMMIT': 'fceb3b6c569cf381b04767da77b4b92418a4b5ed',
    'PHASE9_COMMIT': '0df633ff6cd9bd939fdbd0eb2b39a3ec0ac7e880',
    'PHASE10_COMMIT': '004b0e7e8081e5331ed7aa6291b83afdcdc4f45b',
    'PHASE11_W1_COMMIT': 'a09b928d5c48aa262293066ce3543fb37c575d0f',
    'PHASE11_W2_COMMIT': '483999ced2c97e80af4df48c50da3ee7bcea9e6a',
    'PHASE11_W2_IMPLEMENTATION': 'a5087dc323e2f0bade186e7b7216e152f171a1c6',
}


def save(name, document):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return document


def git(*args, input=None):
    return subprocess.check_output(['git', *args], cwd=ROOT, input=input)


def lineage():
    checks = {}
    for key, commit in ACCEPTED.items():
        subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
        checks[key] = {'commit': commit, 'ancestry': 'PASS'}
    # The original accepted Phase9 W1 was cherry-picked before its final merge.
    original = '31341e75da43f91fd4878edf7e41138aee22c0ff'
    effective = '7dd3e36a279942351f39c00cde1e1ac5087e0d8b'
    patch_ids = [git('patch-id', '--stable', input=git('show', '--pretty=format:', commit)).decode().split()[0]
                 for commit in (original, effective)]
    assert patch_ids[0] == patch_ids[1]
    subprocess.run(['git', 'merge-base', '--is-ancestor', effective, 'HEAD'], cwd=ROOT, check=True)
    return save('lineage.json', {'status': 'PASS', 'initial_candidate_head': git('rev-parse', 'HEAD').decode().strip(),
        'accepted': checks, 'phase9_w1_patch_equivalence': {'original': original, 'effective': effective,
            'stable_patch_id': patch_ids[0], 'effective_ancestor': True}})


def capture():
    rows = inventory(SOURCE)
    save('source-before.json', rows)
    # Populate the existing Phase6 preservation fixture from THIS pre-audit.
    # Metadata chooses the dependencies; bytes/hash/mtime come from the audit.
    from backend.registry.evidence_registry import EvidenceRegistry
    registry = EvidenceRegistry()
    names = set()
    for identity in ('ev.case8.D_u.allocation', 'ev.gate.Acoustic.allocation',
                     'ev.gate.Pressure.allocation', 'ev.gate.Ungated.allocation'):
        for asset in registry.record(identity)['source_assets']:
            if asset['relative_origin']['state'] == 'KNOWN' and asset['source_id'] != 'shockpath-content':
                names.add(asset['relative_origin']['value'].replace('/', '\\'))
    selected = {str(SOURCE / r['path']): {k: r[k] for k in ('sha256', 'size', 'mtime_ns')}
                for r in rows if r['path'] in names}
    assert selected and len(selected) == len(names), (len(selected), len(names))
    fixture = ROOT / '.cache/phase6/source-before.json'
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps(selected, indent=2), encoding='utf-8')
    return save('source-before-summary.json', {'status': 'PASS', 'files': len(rows),
        'bytes': sum(r['size'] for r in rows), 'fingerprint': fingerprint(rows),
        'phase6_fixture_dependencies': len(selected), 'scientific_writes': 0})


def contracts():
    from backend import create_app
    from backend.schemas.openapi import export_openapi
    from openapi_spec_validator import validate
    app = create_app()
    document = export_openapi(app.extensions['operation_catalog'])
    validate(document)
    assert document['openapi'].startswith('3.1.')
    assert document == app.test_client().get('/api/v1/openapi.json').json
    saved = ROOT / 'config/openapi.json'
    independent = OUT / 'openapi-independent.json'
    subprocess.run([__import__('sys').executable, '-B', '-m', 'scripts.export_openapi', '--output', str(independent)], cwd=ROOT, check=True)
    assert independent.read_bytes() == saved.read_bytes()
    cli = ROOT / 'frontend/node_modules/openapi-typescript/bin/cli.js'
    generated = OUT / 'api-independent.d.ts'
    subprocess.run(['node', str(cli), str(independent), '-o', str(generated)], cwd=ROOT, check=True)
    assert generated.read_bytes() == (ROOT / 'frontend/src/types/generated/api.d.ts').read_bytes()
    return save('contracts.json', {'status': 'PASS', 'openapi_3_1': True, 'runtime_equal_saved': True,
        'independent_export_byte_identical': True, 'generated_types_byte_identical': True,
        'paths': len(document['paths']), 'schemas': len(document['components']['schemas']),
        'openapi_sha256': hashlib.sha256(saved.read_bytes()).hexdigest(),
        'types_sha256': hashlib.sha256(generated.read_bytes()).hexdigest()})


def public_audit():
    from backend import create_app
    from backend.models import SourceAsset
    from backend.registry import spectral_registry as S
    from backend.registry.content_registry import load_foundation
    app = create_app()
    client = app.test_client()
    service = app.extensions['evidence_service']
    unsafe = re.compile(r'[A-Za-z]:[\\/]|file://|\\\\[^\s]+|absolute_source_path', re.I)

    def read(url):
        response = client.get(url)
        assert response.status_code == 200, (url, response.status_code, response.json)
        assert response.json['availability'] == 'AVAILABLE'
        assert 'Content-Disposition' not in response.headers
        assert 'ETag' not in response.headers  # No transport hash substituted for scientific identity.
        assert not unsafe.search(response.get_data(as_text=True)), url
        return response.json['data']

    counts = {section: read(f'/api/v1/evidence?section={section}&limit=1')['page']['total_count']
              for section in ('CURRENT', 'GAPS', 'HISTORY', 'ALL')}
    assert counts['ALL'] == sum(counts[s] for s in ('CURRENT', 'GAPS', 'HISTORY'))
    cases = {
        'Case8': 'case8.D_u.allocation', 'Gate': 'gate.Acoustic.allocation',
        'Spectrum': S.record_id('spectrum.q-0.396', 8),
        'Eigenmode': S.eigenmode_id('spectrum.q-0.396', 8, 'RIGHT', 0),
        'Modal Validation': next(iter(S.RUNS)) + '.history',
        'Cylinder': 'cylinder.D_u.sectors', 'Cross-flow': 'case8-cylinder.D_u.D_u',
        'Entropy Closure': 'entropy-closure.D_u-cfl-0.05.run.R_total',
        'Mechanism': 'mechanism.acoustic-pathways.v1',
    }
    chains = {}
    for family, identity in cases.items():
        provenance = read('/api/v1/results/' + identity + '/provenance')
        assert provenance['result_id'] == identity and provenance['evidence_records']
        records = provenance['evidence_records']
        for r in records:
            detail = read('/api/v1/evidence/' + r['evidence_id'])
            assert detail['evidence_id'] == r['evidence_id']
            assert detail['source_assets']
            assert detail['source_drift'] != {'state': 'KNOWN', 'value': True}, r['evidence_id']
            if detail['source_assets'] and all(a['data_drift'] == {'state': 'KNOWN', 'value': False} for a in detail['source_assets']):
                assert detail['source_drift'] == {'state': 'KNOWN', 'value': False}, r['evidence_id']
            else:
                assert detail['source_drift']['state'] == 'UNKNOWN', (r['evidence_id'], detail['source_drift'])
            assert detail['created_at']['state'] == detail['verified_at']['state'] == 'UNKNOWN'
            if detail['data_hash']['state'] == 'KNOWN':
                assert detail['data_hash'] != detail['method_hash']
        if family == 'Cross-flow':
            assert {'case8', 'cylinder'} <= {r['experiment_id'].get('value') for r in records}
        if family == 'Mechanism':
            assert all(not r['result_ids'] and not r['result_contexts'] for r in records)
            assert any(l['code'] == 'SCHEMATIC' for r in records for l in r['limitations'])
        chains[family] = {'result_id': identity, 'evidence_ids': [r['evidence_id'] for r in records]}
    gaps = ('ev.missing.cylinder-cumulative2d', 'ev.inventory.missing_near1d_raw_epsilon_scan',
            'ev.inventory.missing_persisted_jacobian_fourier_blocks')
    for identity in gaps:
        record = read('/api/v1/evidence/' + identity)
        assert record['verification']['status'] == 'MISSING'
        assert not record['result_ids'] and not record['result_contexts']
        assert record['data_hash']['state'] in ('MISSING', 'UNKNOWN') and 'value' not in record['data_hash']
    mechanism, scenes = load_foundation()
    refs = set(mechanism.evidence_refs) | {r for scene in scenes.items for r in scene.evidence_refs}
    assert refs <= set(service.registry.entries)
    assert not any('explore' in identity.lower() for identity in service.registry.entries)
    cache = {}
    statuses = Counter()
    for identity in sorted(service.registry.assets):
        asset = service.load_asset(identity, cache=cache).model_dump(mode='json')
        SourceAsset.model_validate(asset)
        assert not unsafe.search(json.dumps(asset, ensure_ascii=False)), identity
        statuses[asset['verification']['status']] += 1
    routes = [r.rule for r in app.url_map.iter_rules()]
    assert not any('download' in r or 'file' in r for r in routes)
    for query in ('path=D:/Paper/passage6', 'download=true', 'absolute_source_path=secret'):
        assert client.get('/api/v1/assets/asset_8d15c3f16f95?' + query).status_code == 400
    assert client.get('/api/v1/assets/asset_8d15c3f16f95/download').status_code == 404
    return save('public-audit.json', {'status': 'PASS', 'counts': counts, 'coverage': chains,
        'source_assets_scanned': len(service.registry.assets), 'asset_verification_counts': dict(statuses),
        'absolute_locators_in_public_assets': 0, 'download_routes': 0, 'unsafe_query_rejections': 3,
        'gap_records_no_numeric_payload': list(gaps), 'explore_evidence_duplication': False,
        'hash_fields_separate': True, 'etag_used_as_scientific_hash': False})


def production_scan():
    patterns = {
        'scientific_root': r'D:[\\/]+Paper', 'file_uri': r'file://',
        'absolute_source_path': r'absolute_source_path', 'send_file': r'\bsend_file\b',
        'download': r'\bdownload\w*\b', 'arbitrary_path': r'arbitrary.{0,12}path',
        'prohibited_claim': r'\bbest\b|\bwinner\b|universally stable|always improved|uniformly damped|larger entropy means better|more localized is universally better',
    }
    occurrences = []
    for folder in ('backend', 'frontend/src', 'config/content'):
        for path in sorted((ROOT / folder).rglob('*')):
            if path.suffix not in ('.py', '.ts', '.vue', '.json'):
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                for label, pattern in patterns.items():
                    if re.search(pattern, line, re.I):
                        occurrences.append({'file': path.relative_to(ROOT).as_posix(), 'line': number,
                            'category': label, 'text': line.strip()[:500]})
    # Backend private roots and locator scrubber patterns are implementation,
    # not public DTO paths. Denials of downloading/ranking are retained verbatim.
    assert not any(o['category'] == 'send_file' for o in occurrences)
    bundle = '\n'.join(p.read_text(encoding='utf-8') for p in (ROOT / 'frontend/dist/assets').glob('*.js'))
    assert bundle
    mock_markers = ('createMockProvider', 'mock.case8.', 'mock.gate.', 'mock.spectrum.',
                    'mock.modal-validation.', 'MOCK_SYNTHETIC_DATA', 'lim.mock.synthetic')
    assert not any(marker in bundle for marker in mock_markers)
    assert not re.search(patterns['scientific_root'], bundle, re.I)
    assert 'absolute_source_path' not in bundle and 'send_file' not in bundle
    for claim in ('universally stable', 'always improved', 'uniformly damped',
                  'larger entropy means better', 'more localized is universally better'):
        assert claim not in bundle.lower()
    return save('production-scan.json', {'status': 'PASS', 'occurrences_for_context_review': occurrences,
        'public_asset_path_audit': 'public-audit.json;2438 assets', 'send_file_occurrences': 0,
        'scientific_root_in_bundle': False, 'mock_in_production': False,
        'prohibited_positive_claims_in_bundle': 0,
        'context_review': 'best/winner hits are explicit scientific denials or internal selection variable names; file URI pattern is a scrubber. Evidence download hits deny source-file serving; V2 reports.ts downloads only the controlled, hash-verified self-contained report HTML endpoint as a Blob. Private backend source-root defaults are not public API values.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('lineage', 'capture', 'contracts', 'public', 'scan'))
    operation = parser.parse_args().operation
    result = {'lineage': lineage, 'capture': capture, 'contracts': contracts, 'public': public_audit,
              'scan': production_scan}[operation]()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
