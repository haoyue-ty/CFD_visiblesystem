"""Independent saved-source acceptance; no solver imports or scientific writes.

Expected run selections/counts are explicit. Numeric expectations come directly
from CSV/JSON, not adapter helpers or their private validation routines.
"""
from __future__ import annotations

import builtins
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('D:/Paper/passage6').resolve()
CLOSURE = SOURCE / 'experiments/entropy_budget_closure'
EXPECTED = (
    ('D_u-cfl-0.2', 'Du_cfl_02', 'D_u', .2, 3451),
    ('D_u-cfl-0.1', 'Du_cfl_01', 'D_u', .1, 6901),
    ('D_u-cfl-0.05', 'Du_cfl_005', 'D_u', .05, 13802),
    ('D_u-cfl-0.025', 'Du_cfl_0025', 'D_u', .025, 27603),
    ('B_u-cfl-0.05', 'Bu_cfl_005', 'B_u', .05, 13802),
)
BASE = '/api/v1/experiments/entropy-closure'
ARITHMETIC_ERRORS = {}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def numeric_csv(path):
    with path.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        rows = list(reader)
    data = {key: np.array([float(row[key]) for row in rows]) for key in columns}
    assert all(np.isfinite(values).all() for values in data.values()), path
    return data


def equals(actual, expected, label):
    assert np.array_equal(actual, expected), label


def arithmetic(actual, expected, scale, label):
    # Independent vectorized arithmetic may associate sums differently from the
    # frozen Python observer. Bound cancellation by the original term magnitudes,
    # never by a relative tolerance on the tiny entropy residual itself.
    error = np.abs(actual - expected)
    bound = 8 * np.finfo(float).eps * np.abs(scale)
    assert (error <= bound).all(), label
    previous = ARITHMETIC_ERRORS.get(label, {'maximum_absolute_difference': 0.0, 'maximum_allowed_bound': 0.0})
    ARITHMETIC_ERRORS[label] = {
        'maximum_absolute_difference': max(previous['maximum_absolute_difference'], float(np.max(error))),
        'maximum_allowed_bound': max(previous['maximum_allowed_bound'], float(np.max(bound))),
    }


def main():
    # Guard all ordinary Path/open writes to the scientific tree during QA.
    def guarded(original):
        def opened(file, mode='r', *args, **kwargs):
            if isinstance(file, (str, Path)) and Path(file).resolve().is_relative_to(SOURCE):
                assert not any(flag in mode for flag in ('w', 'a', 'x', '+')), 'Scientific write attempted'
            return original(file, mode, *args, **kwargs)
        return opened
    builtins.open = guarded(builtins.open)
    io.open = guarded(io.open)

    from backend import create_app
    from backend.adapters.entropy_closure import EntropyClosureAdapter
    from backend.models.closure import ClosureHistory, ClosureRunRegistry, EntropyClosureRun, RefinementSummary
    from backend.models.evidence import EvidenceRecord
    from backend.schemas.openapi import export_openapi
    from openapi_spec_validator import validate

    assert Path(sys.modules['backend'].__file__).resolve().is_relative_to(ROOT)
    bootstrap_paths = ('docs/handoffs/phase9/PHASE9_CLOSURE_SOURCE_MAP.json',
                       'docs/handoffs/phase9/WINDOW_0_PHASE9_BOOTSTRAP.md')
    for relative in bootstrap_paths:
        original = subprocess.check_output(['git', 'show', f'5ad96fb:{relative}'], cwd=ROOT)
        assert (ROOT / relative).read_bytes() == original, relative
    source_map = read_json(ROOT / bootstrap_paths[0])
    frozen = read_json(CLOSURE / 'FREEZE/frozen_config.json')
    assert frozen['protocol']['time_integrator'] == 'SSP-RK3'
    assert frozen['protocol']['grid'] == [128, 128]
    assert frozen['stage_weights'] == [1 / 6, 1 / 6, 2 / 3]
    eps0 = frozen['eps0']
    client = create_app().test_client()

    def read(path, model=None):
        response = client.get(path)
        assert response.status_code == 200, (path, response.json)
        if model:
            model.model_validate(response.json['data'])
        return response.json['data']

    registry = read(f'{BASE}/runs', ClosureRunRegistry)
    assert [run['run_id'] for run in registry['runs']] == [entry[0] for entry in EXPECTED]
    rows, evidence_refs, terminal = [], set(), {}
    public_payloads = [registry]
    adapter = EntropyClosureAdapter()
    for run_id, directory, config, cfl, count in EXPECTED:
        saved = CLOSURE / 'outputs' / directory
        stage = numeric_csv(saved / 'stage_closure.csv')
        step = numeric_csv(saved / 'step_closure.csv')
        summary = read_json(saved / 'run_summary.json')
        assert len(stage['step']) == 3 * count and len(step['step']) == count
        assert summary['config'] == config and summary['CFL'] == cfl
        assert summary['N_steps'] == count and summary['N_stages'] == 3 * count
        assert summary['T'] == 10 and summary['rejected_steps'] == 0
        assert count == int(np.ceil(10 * 69.00525085828785 / cfl))
        equals(step['step'], np.arange(1, count + 1), 'accepted step indices')
        equals(stage['step'], np.repeat(step['step'], 3), 'stage step indices')
        equals(stage['stage'], np.tile([1, 2, 3], count), 'source stage indices')
        equals(stage['dt'], np.repeat(step['dt'], 3), 'stage intervals')
        equals(stage['t_stage_or_step_time'], np.repeat(step['time_n'], 3), 'recorded stage clock')
        equals(step['time_n'][1:], step['time_np1'][:-1], 'contiguous intervals')
        assert step['time_n'][0] == 0 and step['time_np1'][-1] == 10
        assert (step['time_np1'] > step['time_n']).all()
        assert (step['dt'] == 10 / count).all()
        equals(stage['R_SD'], stage['G'] + stage['D_total'], 'R_SD definition')
        equals(stage['eps_SD'], np.abs(stage['R_SD']) /
               (np.abs(stage['G']) + np.abs(stage['D_total']) + eps0), 'eps_SD normalization')
        arithmetic(stage['R_decomp'], stage['D_total'] - (stage['D_bg'] + stage['D_aa'] + stage['D_at']),
                   np.abs(stage['D_total']) + stage['D_bg'] + stage['D_aa'] + stage['D_at'], 'independent D_total')
        equals(step['DeltaS'], step['S_np1'] - step['S_n'], 'entropy increment')
        cumulative = {}
        for channel in ('bg', 'aa', 'at', 'total'):
            rates = stage[f'D_{channel}'].reshape(count, 3)
            for index in range(3):
                equals(step[f'D_{channel}_stage{index + 1}'], rates[:, index], 'embedded original stage rates')
            field = f'E_{channel}_step' if channel != 'total' else 'E_total_independent_step'
            arithmetic(step[field], step['dt'] * (rates[:, 0] / 6 + rates[:, 1] / 6 + 2 * rates[:, 2] / 3),
                       step[field], 'weighted increment')
            if channel != 'total':
                cumulative[channel] = np.cumsum(step[field])
                assert cumulative[channel][-1] == summary[f'E_{channel}_total']
                assert (rates >= 0).all()
        arithmetic(step['E_obs_step'], step['E_bg_step'] + step['E_aa_step'] + step['E_at_step'],
                   step['E_obs_step'], 'observer increment')
        equals(step['R_time_step'], step['DeltaS'] + step['E_obs_step'], 'temporal increment')
        arithmetic(step['R_time_cumulative'], step['S_np1'] - summary['S0'] +
                   (cumulative['bg'] + cumulative['aa'] + cumulative['at']),
                   np.abs(step['S_np1']) + abs(summary['S0']) + cumulative['bg'] + cumulative['aa'] + cumulative['at'],
                   'recorded cumulative residual')
        assert step['R_time_cumulative'][-1] == summary['R_total']
        terminal[run_id] = summary
        actual = read(f'{BASE}/runs/{run_id}', EntropyClosureRun)
        assert actual == adapter.load_run(run_id).model_dump(mode='json')
        assert actual['stage_point_count'] == 3 * count and actual['step_point_count'] == count
        assert {p['name']: p['value']['value'] for p in actual['config']['parameters']} == {
            'CFL': cfl, 'q_aa': 3.96, 'q_at': 0 if config == 'B_u' else .396}
        for slot in actual['terminal_summary']:
            metric = slot['value']
            assert metric['value']['value'] == summary[metric['metric_id']]
        if config == 'B_u':
            assert (stage['D_at'] == 0).all() and (step['E_at_step'] == 0).all() and summary['E_at_total'] == 0
        evidence_refs.update(actual['evidence_refs'])
        public_payloads.append(actual)
        for group, data, granularity in (('stage', stage, 'PER_STAGE'), ('step', step, 'PER_STEP')):
            total = len(data['step'])
            for offset in (0, total // 2, total - 1):
                history = read(f'{BASE}/runs/{run_id}/{group}-history?offset={offset}&limit=3', ClosureHistory)
                assert history['granularity'] == granularity
                for series in history['series']:
                    assert series['total_point_count'] == series['page']['total_count'] == total
                    assert series['result']['time']['sampling'] == granularity
                    for index, point in enumerate(series['points'], offset):
                        assert point['point_index'] == index
                        assert point['value']['value'] == data[series['source_column']][index]
                        assert point['step_index']['value'] == data['step'][index]
                        if group == 'stage':
                            assert point['source_stage_index']['value'] == data['stage'][index]
                            assert point['stage_index']['value'] == data['stage'][index] - 1
                            assert point['physical_time']['value'] == data['t_stage_or_step_time'][index]
                        else:
                            assert point['physical_time']['value'] == data['time_np1'][index]
                    if series['series_id'] == 'R_time_cumulative':
                        assert series['aggregation'] == 'CUMULATIVE'
                    if series['series_id'] == 'R_time_step':
                        assert series['aggregation'] == 'STEP_INCREMENT'
                evidence_refs.update(history['evidence_refs'])
                public_payloads.append(history)
        rows.append({'run_id': run_id, 'CFL': cfl, 'steps': count, 'stage_rows': 3 * count,
                     'step_rows': count, 'R_total': summary['R_total'], 'all_raw_rows_audited': True})

    refinement = read(f'{BASE}/refinement', RefinementSummary)
    assert refinement['run_ids'] == [entry[0] for entry in EXPECTED[:4]]
    assert len(refinement['metrics_by_run']) == 4
    for entry in refinement['metrics_by_run']:
        metrics = {slot['value']['metric_id']: slot['value']['value']['value'] for slot in entry['metrics']}
        assert metrics['R_total'] == terminal[entry['run_id']]['R_total']
        assert metrics['dt_eff'] == terminal[entry['run_id']]['dt_eff']
    slopes = read_json(CLOSURE / 'FREEZE/frozen_audit_summary.json')
    assert refinement['refinement_slope']['value']['value']['value'] == slopes['global_slope']
    assert slopes['global_slope'] == source_map['refinement']['global_slope']
    evidence_refs.update(refinement['evidence_refs'])
    public_payloads.append(refinement)
    evidence = []
    assert len(evidence_refs) == 16
    for identity in sorted(evidence_refs):
        record = read(f'/api/v1/evidence/{identity}', EvidenceRecord)
        assert record['source_drift'] == {'state': 'KNOWN', 'value': False}
        assert record['result_ids'] and record['definitions'] and record['source_assets']
        for asset in record['source_assets']:
            assert asset['recorded_data_hash'] == asset['current_data_hash']
            relative = asset['relative_origin']['value']
            actual_hash = hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest()
            assert asset['current_data_hash']['value'] == actual_hash
        limits = {entry['code']: entry['description'] for entry in record['limitations']}
        assert 'not an exact entropy identity or a new entropy theorem' in limits['FULLY_DISCRETE_DIAGNOSTIC']
        assert 'SSP-RK3 only' in limits['FULLY_DISCRETE_DIAGNOSTIC']
        assert 'SPATIAL_TRAJECTORY_MISSING' in limits
        evidence.append({'evidence_id': identity, 'result_ids': record['result_ids'],
                         'source_asset_ids': [asset['asset_id'] for asset in record['source_assets']]})
        public_payloads.append(record)
    capabilities = read(f'{BASE}/capabilities')['items']
    flow = next(cap for cap in capabilities if cap['task'] == 'flow')
    assert flow['status'] == 'MISSING' and not flow['tab_policy']['visible_for_family'] and not flow['result_refs']
    for suffix in ('spatial', 'fields', 'snapshots', 'trajectory', 'run-new'):
        assert client.get(f'{BASE}/{suffix}').status_code == 404
    for bad_run in ('B_u-cfl-0.1', 'D_u-cfl-0.03'):
        assert client.get(f'{BASE}/runs/{bad_run}').status_code == 422
    ui = (ROOT / 'frontend/src/pages/ClosurePage.vue').read_text(encoding='utf-8')
    assert 'not an exact fully-discrete entropy identity' in ui
    text = json.dumps(public_payloads).lower() + ui.lower()
    assert not re.search(r'(?:guarantees|proves|establishes)\s+(?:an?\s+)?(?:exact fully.discrete identity|new ssp.rk3 entropy theorem|universal time.integrator)', text)
    assert not [name for name in sys.modules if name == 'solver' or name.startswith('solver.') or name.startswith('diagnostics.')]
    document = export_openapi(create_app().extensions['operation_catalog'])
    validate(document)
    assert document == read_json(ROOT / 'config/openapi.json')
    assert document == client.get('/api/v1/openapi.json').json
    operations = {entry['get']['operationId'] for path, entry in document['paths'].items() if path.startswith(BASE)}
    assert operations == {'CLO01', 'CLO02', 'CLO03', 'CLO04', 'CLO05'}
    result = {'status': 'PASS', 'worktree': str(ROOT), 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'runs': rows, 'stage_rows': sum(row['stage_rows'] for row in rows), 'step_rows': sum(row['step_rows'] for row in rows),
              'bootstrap': 'PASS', 'canonical_models': 'PASS', 'CLO01_05': 'PASS', 'semidiscrete': 'PASS', 'fully_discrete': 'PASS',
              'refinement': 'PASS', 'bu_zero_channel': 'PASS', 'spatial_trajectory': 'MISSING', 'scientific_wording': 'PASS',
              'evidence': evidence, 'scientific_files_modified': False, 'cfd_runs_started': 0,
              'arithmetic_error_bounds': ARITHMETIC_ERRORS,
              'scope': 'All raw rows; API first/middle/last page samples equal saved values exactly; all 16 Evidence groups; frozen slopes read without refit'}
    output = ROOT / '.cache/phase9-final/independent-closure-qa.json'
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'evidence'}))


if __name__ == '__main__':
    main()
