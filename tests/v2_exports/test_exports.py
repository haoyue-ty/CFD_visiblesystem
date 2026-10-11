"""Export contracts, numeric ordering, identity, resources and failure isolation."""
import base64
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
import os
import struct
import threading
from xml.etree import ElementTree as ET
import zipfile

import numpy as np
import pytest

from backend import create_app
from backend.models.v2.result import ScientificRunResult
from backend.postprocess.case8 import primitive_fields
from backend.services.v2.case8_exports import Case8Exporter
from backend.services.v2.exports import ExportService
from backend.services.v2.pdf_export import PDFUnavailable
from backend.services.v2.results import ScientificResultService
from backend.solver_runtime.artifacts import output_inventory, sha256, write_json
from backend.solver_runtime.run_manager import directory_bytes
from backend.solver_runtime.run_store import file_lock
from tests.v2_p3.test_runs import store, body
from tests.v2_p4.test_results import complete


@pytest.fixture
def source(complete, store):
    root, record, inventory = complete
    nx, ny = record.experiment.normalized_config.grid.nx, record.experiment.normalized_config.grid.ny
    j, i = np.indices((ny, nx))
    rho, u, v, pressure = 2 + i/100 + j/10, 1 + i/200, .5 + j/200, 4 + i/50 + j/25
    state = np.stack([rho, rho*u, rho*v, pressure/.4 + rho*(u*u+v*v)/2], axis=-1)
    np.savez(root/'initial_state.npz', state=state, x=(np.arange(nx)+.5)/nx, y=(np.arange(ny)+.5)/ny)
    np.savez(root/'final_state.npz', state=state, accepted_steps=1, time=.04)
    with np.load(root/'snapshots/step_000001.npz', allow_pickle=False) as old:
        faces = {k: old[k] for k in old.files if 'faces' in k}
    for step, time in ((0, 0.), (1, .04)):
        np.savez(root/f'snapshots/step_{step:06d}.npz', state=state, step=step, time=time, **faces)
    write_json(root, 'snapshots/index.json', [dict(step=step, time=time, cell_shape=[ny,nx,4]) for step,time in ((0,0.),(1,.04))])
    inventory()
    return root, record, inventory


@pytest.fixture
def service(store):
    return ExportService(store)


@pytest.fixture
def api(store):
    app = create_app(run_store=store, case8_adapter=None, allocation_adapter=None, spectral_adapter=None,
                     cylinder_adapter=None, closure_adapter=None)
    return app.test_client()


def original_hashes(root):
    return {p.relative_to(root).as_posix(): sha256(p) for p in root.rglob('*') if p.is_file()
            and p.relative_to(root).parts[0] not in ('exports','report','ai')}


def vtk_values(path, name):
    tree = ET.parse(path)
    array = tree.find(f'.//CellData/DataArray[@Name="{name}"]')
    assert array.attrib['type'] == 'Float64' and array.attrib['format'] == 'binary'
    binary = base64.b64decode(array.text)
    assert struct.unpack('<Q', binary[:8])[0] == len(binary)-8
    return np.frombuffer(binary[8:], dtype='<f8')


def test_raw_csv_manifest_zip_and_repeated_cache_are_exact(source, store, service, api):
    root, record, _ = source
    before, inventory, solver_bytes = original_hashes(root), output_inventory(root), directory_bytes(root)
    result = ScientificResultService(store).result(record.run_id)
    url = f'/api/v2/runs/{record.run_id}/exports'
    assert api.get(url).json['data']['exports']['raw']['status'] == 'NOT_GENERATED'
    assert api.get(url+'/raw/download').status_code == 409
    response = api.post(url+'/raw')
    assert response.status_code == 200, response.json
    meta = response.json['data']
    assert meta['status'] == 'READY' and meta['formats'] == ['NPZ','JSON','CSV']
    manifest_path = root/'exports/manifest.json'
    manifest_bytes, modified = manifest_path.read_bytes(), manifest_path.stat().st_mtime_ns
    assert api.post(url+'/raw').json['data'] == meta
    assert manifest_path.read_bytes() == manifest_bytes and manifest_path.stat().st_mtime_ns == modified
    manifest = json.loads(manifest_bytes)
    assert manifest['source_result_hash'] == result.result_hash
    for row in manifest['files']:
        file = root/'exports'/row['path']
        assert sha256(file) == row['sha256'] and file.stat().st_size == row['size'] and row['sources']
    for file in (root/'exports/raw').rglob('*.npz'):
        original = root/file.relative_to(root/'exports/raw')
        assert sha256(file) == sha256(original)
    with (root/'exports/diagnostics/history.csv').open(encoding='utf-8-sig',newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    history = [json.loads(line) for line in (root/'diagnostics/history.jsonl').read_text().splitlines()]
    assert len(csv_rows) == len(history)
    assert set(csv_rows[0]) == set(history[0])
    for key,value in history[0].items():
        assert float(csv_rows[0][key]) == value
    download = api.get(url+'/raw/download')
    assert download.status_code == 200 and download.mimetype == 'application/zip'
    assert download.content_length == meta['size_bytes'] and download.headers['X-Export-SHA256'] == meta['sha256']
    assert f'ShockPath_{record.run_id}_raw_data.zip' in download.headers['Content-Disposition']
    with zipfile.ZipFile(io.BytesIO(download.data)) as archive:
        assert archive.testzip() is None
        assert {'README.md','raw/initial_state.npz','raw/final_state.npz','diagnostics/history.csv'} <= set(archive.namelist())
        assert not any('..' in p or p.startswith('/') or '.env' in p for p in archive.namelist())
    download.close()
    assert original_hashes(root) == before and output_inventory(root) == inventory
    assert directory_bytes(root) == solver_bytes
    assert ScientificResultService(store).result(record.run_id).result_hash == result.result_hash


def test_vti_fields_native_geometry_and_pvd_times(source, store, service):
    root, record, _ = source
    service.generate(record.run_id, 'visualization')
    datasets = ET.parse(root/'exports/visualization/timeseries.pvd').findall('.//DataSet')
    assert [float(row.attrib['timestep']) for row in datasets] == [0.,.04]
    result = ScientificResultService(store).result(record.run_id)
    assert len(datasets) == len(result.snapshots)
    for row, snapshot in zip(datasets,result.snapshots):
        vti = root/'exports/visualization'/row.attrib['file']
        image = ET.parse(vti).find('ImageData')
        assert image.attrib['WholeExtent'] == '0 64 0 16 0 1'
        assert list(map(float,image.attrib['Origin'].split())) == [0.,0.,-1/128]
        assert list(map(float,image.attrib['Spacing'].split())) == [1/64,1/16,1/64]
        assert not image.findall('.//PointData/DataArray')
        with np.load(root/f'snapshots/{snapshot.snapshot_id}.npz',allow_pickle=False) as data:
            expected = primitive_fields(data['state'],1.4)
            for name,array in expected.items():
                # Explicit tolerance: Float64 binary stores these values exactly.
                np.testing.assert_allclose(vtk_values(vti,name).reshape(16,64),array,rtol=0,atol=0)
            assert vtk_values(vti,'density')[1] > vtk_values(vti,'density')[0]
            assert vtk_values(vti,'density')[64] > vtk_values(vti,'density')[0]


def test_csv_union_precision_and_missing_are_preserved(source, store, service):
    root, record, inventory = source
    path = root/'diagnostics/history.jsonl'
    first = json.loads(path.read_text())
    first.update(time_end=.02,dt=.02)
    second = {**first, 'step':1, 'time_start':.02, 'time_end':.04, 'new_diagnostic':1.2345678901234567}
    first['legacy_extra'] = 3.125
    path.write_text(json.dumps(first)+'\n'+json.dumps(second)+'\n',encoding='utf-8')
    summary = json.loads((root/'result.json').read_text())
    summary.update(accepted_steps=2,final_time=.04,dt=.02)
    write_json(root,'result.json',summary)
    with np.load(root/'final_state.npz',allow_pickle=False) as data:
        state = data['state']
    np.savez(root/'final_state.npz',state=state,accepted_steps=2,time=.04)
    np.savez(root/'snapshots/step_000001.npz',state=state,step=1,time=.02)
    np.savez(root/'snapshots/step_000002.npz',state=state,step=2,time=.04)
    index=json.loads((root/'snapshots/index.json').read_text())
    index[1]['time']=.02
    index.append(dict(step=2,time=.04,cell_shape=list(state.shape)))
    write_json(root,'snapshots/index.json',index); inventory()
    service.generate(record.run_id,'raw')
    with (root/'exports/diagnostics/history.csv').open(encoding='utf-8-sig',newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]['new_diagnostic'] == 'NA' and rows[1]['legacy_extra'] == 'NA'
    assert float(rows[1]['new_diagnostic']) == second['new_diagnostic']
    assert rows[0]['E_at'] == '0.0' and rows[1]['time_end'] == repr(.04)


@pytest.mark.parametrize('present',[False,True])
def test_existing_runs_and_stored_scientific_identity_unchanged(source, store, service, present):
    root, record, inventory = source
    expected = ScientificResultService(store).result(record.run_id)
    if present:
        write_json(root,'scientific_result.json',expected.model_dump(mode='json')); inventory()
    before = original_hashes(root)
    service.generate(record.run_id,'raw'); service.generate(record.run_id,'visualization')
    exported = ScientificRunResult.model_validate_json((root/'exports/raw/scientific_result.json').read_text(encoding='utf-8'))
    assert exported.result_hash == expected.result_hash
    assert original_hashes(root) == before
    assert (root/'scientific_result.json').exists() is present


def test_html_report_reuses_existing_renderer_and_pdf_degrades(source, store, service, api, monkeypatch):
    root, record, _ = source
    monkeypatch.setattr('backend.services.v2.exports.pdf_capability',lambda settings:(None,'No Chromium test dependency'))
    metadata = service.generate(record.run_id,'report')
    assert metadata.formats == ['HTML'] and metadata.unavailable_formats['PDF']
    manifest = json.loads((root/'exports/manifest.json').read_text())
    assert manifest['formats']['report'] == ['HTML']
    assert not (root/'exports/reports/report.pdf').exists()
    html = (root/'exports/reports/report.html').read_text(encoding='utf-8')
    original = service.reports.html(record.run_id)
    assert html == original and record.run_id in html and '<svg ' in html
    download = api.get(f'/api/v2/runs/{record.run_id}/exports/report/download?format=html')
    assert download.status_code == 200 and download.data.decode('utf-8') == html
    assert f'ShockPath_{record.run_id}_report.html' in download.headers['Content-Disposition']
    download.close()
    with zipfile.ZipFile(root/'exports/bundles/experiment_report.zip') as archive:
        assert set(archive.namelist()) == {'report.html','README.md','export_manifest.json'}
    assert service.status(record.run_id).capabilities['report'].unavailable_formats['PDF']


def test_pdf_failure_preserves_html_and_raw_and_can_retry(source, store, service, monkeypatch):
    root, record, _ = source
    monkeypatch.setattr('backend.services.v2.exports.pdf_capability',lambda settings:('test-browser',None))
    def fail(*args,**kwargs): raise PDFUnavailable('Renderer test failure')
    monkeypatch.setattr('backend.services.v2.exports.render_pdf',fail)
    with pytest.raises(Exception) as error:
        service.generate(record.run_id,'report','pdf')
    assert error.value.code == 'PDF_UNAVAILABLE'
    assert service.status(record.run_id).exports['report'].status == 'READY'
    assert service.reports.html(record.run_id)
    assert not (root/'exports/reports/report.pdf').exists()
    assert service.generate(record.run_id,'raw').status == 'READY'
    def succeeds(html,path,browser,**kwargs): path.write_bytes(b'%PDF-1.7\n' + b'test-only-not-a-delivery\n'*100)
    monkeypatch.setattr('backend.services.v2.exports.render_pdf',succeeds)
    assert 'PDF' in service.generate(record.run_id,'report','pdf').formats


@pytest.mark.parametrize('status',['QUEUED','RUNNING','POSTPROCESSING','FAILED','CANCELLED'])
def test_incomplete_runs_are_not_packaged(store, api, status):
    record = store.create(body())
    with store.transaction():
        record.status=status; store._commit(record)
    url=f'/api/v2/runs/{record.run_id}/exports'
    assert api.get(url).json['data']['available'] is False
    for kind in ('raw','visualization','report'):
        assert api.post(url+'/'+kind).status_code == 409
        assert api.get(url+'/'+kind+'/download').status_code == 409
    assert not (store.directory(record.run_id)/'exports').exists()


def test_tampered_source_is_rejected_even_when_cache_exists(source, service, api):
    root, record, _ = source
    service.generate(record.run_id,'raw')
    with (root/'final_state.npz').open('ab') as stream: stream.write(b'drift')
    response = api.get(f'/api/v2/runs/{record.run_id}/exports/raw/download')
    assert response.status_code == 500 and response.json['error']['code'] == 'RUN_OUTPUT_INVALID'


@pytest.mark.parametrize('which',['snapshot_time','final_time','final_shape','snapshot_order','incomplete_interval'])
def test_inconsistent_scientific_source_cannot_be_packaged(source, service, api, which):
    root, record, inventory = source
    with np.load(root/'final_state.npz',allow_pickle=False) as data: state=data['state']
    if which == 'snapshot_time':
        np.savez(root/'snapshots/step_000001.npz',state=state,step=1,time=.02)
    elif which == 'final_time':
        np.savez(root/'final_state.npz',state=state,accepted_steps=1,time=.02)
    elif which == 'final_shape':
        np.savez(root/'final_state.npz',state=state.T,accepted_steps=1,time=.04)
    elif which == 'snapshot_order':
        rows=json.loads((root/'snapshots/index.json').read_text())
        write_json(root,'snapshots/index.json',list(reversed(rows)))
    else:
        summary=json.loads((root/'result.json').read_text())
        summary['full_requested_interval_completed']=False
        write_json(root,'result.json',summary)
    inventory()  # Hash correctness alone cannot legitimize contradictory metadata.
    response=api.post(f'/api/v2/runs/{record.run_id}/exports/raw')
    assert response.status_code == 500 and response.json['error']['code']=='RUN_OUTPUT_INVALID'


def test_tampered_cache_is_never_downloaded_and_regenerated(source, service, api):
    root, record, _ = source
    old = service.generate(record.run_id,'raw')
    (root/'exports/raw/final_state.npz').write_bytes(b'corrupt')
    assert api.get(f'/api/v2/runs/{record.run_id}/exports/raw/download').status_code == 409
    assert service.status(record.run_id).exports['raw'].status == 'FAILED'
    new = service.generate(record.run_id,'raw')
    assert new.status == 'READY' and sha256(root/'exports/raw/final_state.npz') == sha256(root/'final_state.npz')


def test_arbitrary_selectors_and_manifest_paths_are_refused(source, service, api):
    root, record, _ = source
    url=f'/api/v2/runs/{record.run_id}/exports'
    assert api.post(url+'/secret').status_code == 400
    for suffix in ('/raw?format=pdf','/raw?path=.env','/raw?format=zip&format=pdf'):
        assert api.post(url+suffix).status_code == 400
    assert api.post('/api/v2/runs/not-a-uuid/exports/raw').status_code == 404
    unknown='00000000-0000-4000-8000-000000000000'
    assert api.post(f'/api/v2/runs/{unknown}/exports/raw').status_code == 404
    service.generate(record.run_id,'raw')
    manifest=json.loads((root/'exports/manifest.json').read_text())
    manifest['files'][0]['path']='../../.env'
    write_json(root,'exports/manifest.json',manifest)
    response=api.get(url+'/raw/download')
    assert response.status_code == 500 and response.json['error']['code'] == 'EXPORT_OUTPUT_INVALID'


def test_same_run_concurrency_shows_generating_and_publishes_once(source, store, service, api, monkeypatch):
    root, record, _ = source
    entered, release = threading.Event(), threading.Event()
    original=Case8Exporter.raw
    calls=[]
    def paused(self):
        calls.append(1); entered.set(); assert release.wait(15); return original(self)
    monkeypatch.setattr(Case8Exporter,'raw',paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        task=pool.submit(service.generate,record.run_id,'raw')
        try:
            assert entered.wait(10)
            assert service.status(record.run_id).exports['raw'].status == 'GENERATING'
            response=api.post(f'/api/v2/runs/{record.run_id}/exports/raw')
            assert response.status_code == 429 and response.json['error']['code'] == 'EXPORT_BUSY'
            assert not (root/'exports/bundles/raw_data.zip').exists()
        finally: release.set()
        assert task.result().status == 'READY'
    assert len(calls)==1
    assert service.generate(record.run_id,'raw').status == 'READY' and len(calls)==1
    assert not list((root/'exports/.staging').glob('*/'))


def test_export_quotas_and_global_slots_are_independent(source, store, service, api):
    root, record, _ = source
    store.settings.max_export_cache_bytes=100
    response=api.post(f'/api/v2/runs/{record.run_id}/exports/raw')
    assert response.status_code == 413 and response.json['error']['code'] == 'EXPORT_CACHE_LIMIT'
    assert store.get(record.run_id).status == 'COMPLETED'
    store.settings.max_export_cache_bytes=268435456
    store.settings.max_total_export_cache_bytes=100
    assert api.post(f'/api/v2/runs/{record.run_id}/exports/raw').status_code == 413
    store.settings.max_total_export_cache_bytes=2147483648
    store.settings.max_concurrent_exports=1
    with file_lock(store.control/'export-slot-0.lock'):
        response=api.post(f'/api/v2/runs/{record.run_id}/exports/raw')
    assert response.status_code == 429 and response.json['error']['code'] == 'EXPORT_SERVICE_BUSY'


def test_failure_never_changes_original_and_leaves_no_partial_zip(source, service, monkeypatch):
    root, record, _ = source
    before=original_hashes(root)
    def fail(self):
        self.copy('initial_state.npz','raw/initial_state.npz')
        raise OSError('test disk error')
    monkeypatch.setattr(Case8Exporter,'raw',fail)
    with pytest.raises(Exception) as error: service.generate(record.run_id,'raw')
    assert error.value.code == 'EXPORT_GENERATION_FAILED'
    assert service.status(record.run_id).exports['raw'].status == 'FAILED'
    assert not (root/'exports/bundles/raw_data.zip').exists()
    assert original_hashes(root) == before
