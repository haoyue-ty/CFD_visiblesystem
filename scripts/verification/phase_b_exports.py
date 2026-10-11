"""Export existing real Runs through Flask, recording immutable source checks."""
import argparse
import csv
import json
from pathlib import Path
import re
import zipfile

import numpy as np

from backend import create_app
from backend.core.settings import Settings, WORKSPACE_ROOT
from backend.postprocess.case8 import primitive_fields
from backend.services.v2.results import ScientificResultService
from backend.solver_runtime.artifacts import output_inventory, sha256
from backend.solver_runtime.run_store import RunStore


def validate(run_id, output, *, include_pdf):
    store=RunStore(Settings.from_env())
    science=ScientificResultService(store)
    result=science.result(run_id)
    root=store.directory(run_id)
    inventory=output_inventory(root)
    before={p.relative_to(root).as_posix():sha256(p) for p in root.rglob('*') if p.is_file()
            and p.relative_to(root).parts[0] not in ('exports','report','ai','cache','tmp')}
    report_hashes={'result_hash':result.result_hash,'solver_result_sha256':result.provenance.solver_result_sha256,
        'config_hash':result.identity.config_hash,'method_sha256':result.provenance.method_sha256,
        'provenance_sha256':sha256(root/'provenance.json')}
    client=create_app(run_store=store,case8_adapter=None,allocation_adapter=None,spectral_adapter=None,
                      cylinder_adapter=None,closure_adapter=None).test_client()
    generated={}
    for kind in ('raw','visualization','report'):
        url=f'/api/v2/runs/{run_id}/exports/{kind}'
        response=client.post(url,query_string={'format':'zip' if kind != 'report' or include_pdf else 'html'})
        assert response.status_code == 200, response.json
        generated[kind]=response.json['data']
        if kind == 'report' and include_pdf:
            assert 'PDF' in generated[kind]['formats'], generated[kind]['unavailable_formats']
        with client.get(url+'/download') as download:
            assert download.status_code == 200
            # Consumption is part of acceptance only; production responses use send_file streaming.
            data=download.data
            assert len(data)==generated[kind]['size_bytes']
        bundle=root/'exports/bundles'/({'raw':'raw_data','visualization':'flow_field','report':'experiment_report'}[kind]+'.zip')
        assert sha256(bundle)==generated[kind]['sha256']
        with zipfile.ZipFile(bundle) as archive: assert archive.testzip() is None
    copies=[]
    for path in (root/'exports/raw').rglob('*.npz'):
        original=root/path.relative_to(root/'exports/raw')
        assert sha256(path)==sha256(original)
        copies.append({'path':path.relative_to(root/'exports').as_posix(),'sha256':sha256(path)})
    source_rows=[json.loads(line) for line in (root/'diagnostics/history.jsonl').read_text(encoding='utf-8').splitlines()]
    with (root/'exports/diagnostics/history.csv').open(encoding='utf-8-sig',newline='') as stream:
        csv_rows=list(csv.DictReader(stream))
    assert len(csv_rows)==len(source_rows)==result.runtime.accepted_steps
    columns=set().union(*(row.keys() for row in source_rows))
    assert set(csv_rows[0])==columns
    for expected,actual in zip(source_rows,csv_rows):
        for key in columns:
            value=expected.get(key)
            if value is None: assert actual[key]=='NA'
            else: assert float(actual[key])==value
    for key,value in result.entropy.totals.items(): assert float(csv_rows[-1][key])==value
    with (root/'exports/diagnostics/entropy_budget.csv').open(encoding='utf-8-sig',newline='') as stream:
        entropy_rows=list(csv.DictReader(stream))
    assert len(entropy_rows)==len(source_rows)
    for actual,expected in zip(entropy_rows,source_rows):
        for key,value in actual.items(): assert float(value)==expected[key]
    html=(root/'exports/reports/report.html').read_text(encoding='utf-8')
    report_data=json.loads(re.search(r'<script type="application/json" id="report-data">(.*?)</script>',html,re.S).group(1))
    assert report_data['run_id']==run_id and report_data['result_hash']==result.result_hash
    assert report_data['config']==result.config.model_dump(mode='json')
    assert report_data['entropy']['totals']==result.entropy.totals
    assert report_data['metrics']==[m.model_dump(mode='json') for m in result.metrics]
    assert html.count('<svg ')==4 and all(word in html for word in ('流场结果','熵耗散路径分析','科学边界'))
    manifest=json.loads((root/'exports/manifest.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path=root/'exports'/row['path']
        assert path.stat().st_size==row['size'] and sha256(path)==row['sha256']
    assert output_inventory(root)==inventory
    for name,value in before.items(): assert sha256(root/name)==value
    after=science.result(run_id)
    assert after.result_hash==result.result_hash
    reference=output/run_id/'vtk-reference'
    reference.mkdir(parents=True,exist_ok=True)
    for snapshot in result.snapshots:
        with np.load(root/f'snapshots/{snapshot.snapshot_id}.npz',allow_pickle=False) as data:
            state=data['state']
            fields=primitive_fields(state,result.config.normalized_config.physics.gamma)
            fields.update(momentum_density_x=state[...,1],momentum_density_y=state[...,2],total_energy_density=state[...,3])
            np.savez(reference/(snapshot.snapshot_id+'.npz'),**fields)
    grid=result.config.normalized_config.grid
    (reference/'reference.json').write_text(json.dumps({'nx':grid.nx,'ny':grid.ny,'x0':grid.domain.x[0],'y0':grid.domain.y[0],
        'dx':(grid.domain.x[1]-grid.domain.x[0])/grid.nx,'dy':(grid.domain.y[1]-grid.domain.y[0])/grid.ny,
        'snapshots':[s.model_dump(mode='json') for s in result.snapshots]},indent=2),encoding='utf-8')
    verification={'run_id':run_id,'source_kind':'EXISTING_COMPLETED_REAL_V2_CASE8','grid':[grid.nx,grid.ny],
        'scientific_result_was_stored':(root/'scientific_result.json').exists(),'run_directory':str(root),'reference_directory':str(reference),
        'identity_before_and_after':report_hashes,'original_files_checked':len(before),'provenance_unchanged':True,
        'raw_npz':{'status':'PASS','copies':copies},'csv':{'status':'PASS','rows':len(csv_rows),'columns':len(columns),'round_trip_exact':True,'missing':'NA'},
        'html':{'status':'PASS','inline_svg_count':4},'exports':generated,'manifest_file_count':len(manifest['files'])}
    (output/run_id/'acceptance.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"PHASE B REAL RUN PASS: {run_id}, {grid.nx}x{grid.ny}, {len(result.snapshots)} frames, {len(csv_rows)} CSV rows / {len(columns)} columns, {len(before)} original file hashes unchanged")
    return verification


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',action='append',required=True)
    parser.add_argument('--output',type=Path,default=WORKSPACE_ROOT/'output/phase-b')
    parser.add_argument('--include-pdf',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    for run_id in args.run_id: validate(run_id,args.output,include_pdf=args.include_pdf)


if __name__=='__main__': main()
