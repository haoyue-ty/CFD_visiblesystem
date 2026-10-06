"""Real managed fast/custom CFD and HTTP science-to-file acceptance."""
import json
import os
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import numpy as np

from backend.core.settings import Settings, WORKSPACE_ROOT
from backend.services.v2.experiments import validate_experiment
from backend.solver_runtime.artifacts import write_json, utc_now, sha256
from backend.solver_runtime.case8_adapter import worker_environment, Case8SolverAdapter
from backend.solver_runtime.processes import terminate_worker, process_identity
from backend.solver_runtime.run_store import RunStore
from scripts.run_case8 import template_request

OUT = WORKSPACE_ROOT / "docs/v2"
BASE = "http://127.0.0.1:5125"


def http(path, body=None, expected=200):
    request = Request(BASE + path, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            status, payload = response.status, json.load(response)
    except HTTPError as error:
        status, payload = error.code, json.load(error)
    assert status == expected, (path, status, payload)
    return payload.get("data", payload)


def main():
    store = RunStore(Settings())
    if store.manager_available():
        raise RuntimeError("P4 acceptance needs an idle runtime without an active manager")
    report = dict(status="RUNNING", started_at=utc_now(), checks={})
    server = None
    def save(name, value):
        report["checks"][name] = {"status": "PASS", **value}
        write_json(OUT, "p4_live_acceptance.json", report)
        print(json.dumps(dict(check=name, status="PASS")), flush=True)
    try:
        with (OUT / "p4_live_server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen([sys.executable, "-B", "-m", "scripts.serve_backend"], cwd=WORKSPACE_ROOT,
                env=os.environ | {"API_PORT": "5125", "DEEPSEEK_API_KEY": ""}, stdout=log, stderr=subprocess.STDOUT)
            for _ in range(150):
                try:
                    http("/api/v2/cases"); break
                except OSError: time.sleep(.1)
            for custom in (False, True):
                request = template_request("case8.fast.D_u")
                if custom:
                    request.config.grid.nx, request.config.grid.ny = 128, 32
                    request.config.method.q_at = 0.
                validated = validate_experiment(request)
                record = http("/api/v2/runs", {**request.model_dump(mode="json"), "idempotency_key": str(uuid4()),
                    "confirmed_config_hash": validated.config_hash}, 202)
                run_id = record["run_id"]
                http(f"/api/v2/runs/{run_id}/result", expected=409)
                deadline = time.monotonic() + 240
                while record["status"] != "COMPLETED":
                    assert record["status"] not in ("FAILED", "CANCELLED"), record
                    assert time.monotonic() < deadline, record
                    time.sleep(.5)
                    record = http(f"/api/v2/runs/{run_id}")
                root = store.directory(run_id)
                result = http(f"/api/v2/runs/{run_id}/result")
                evidence = http(f"/api/v2/runs/{run_id}/evidence")
                assert result["identity"]["frozen"] is False
                assert result["result_hash"] == evidence["result_hash"]
                assert result["identity"]["config_hash"] == validated.config_hash
                assert result["identity"]["classification"] == ("CUSTOM_RUN" if custom else "LIVE_FAST_RUN")
                assert http(f"/api/v2/runs/{run_id}/result")["result_hash"] == result["result_hash"]
                history = [json.loads(line) for line in (root / "diagnostics/history.jsonl").read_text().splitlines()]
                assert history == result["entropy"]["rows"]
                assert len(result["snapshots"]) == 6
                max_field_error = 0.
                for snapshot in result["snapshots"]:
                    sid = snapshot["snapshot_id"]
                    with np.load(root / f"snapshots/{sid}.npz", allow_pickle=False) as data:
                        state = data["state"]
                        rho, mx, my, energy = np.moveaxis(state, -1, 0)
                        pressure = .4*(energy - (mx*mx + my*my)/(2*rho))
                        direct = dict(density=rho, pressure=pressure, velocity_x=mx/rho, velocity_y=my/rho)
                        direct["speed"] = np.sqrt((mx/rho)**2+(my/rho)**2)
                        direct["mach"] = direct["speed"]/np.sqrt(1.4*pressure/rho)
                        for key, values in direct.items():
                            field = http(f"/api/v2/runs/{run_id}/snapshot/{sid}/field?field={key}")
                            observed = np.array(field["values"]).reshape(field["shape"])
                            np.testing.assert_allclose(observed, values, rtol=3e-14, atol=3e-14)
                            max_field_error = max(max_field_error, float(np.max(abs(observed-values))))
                            assert field["axes"] == ["y", "x"] and field["time"] == snapshot["time"]
                            assert field["source_sha256"] == sha256(root / f"snapshots/{sid}.npz")
                        faces = http(f"/api/v2/runs/{run_id}/snapshot/{sid}/faces")
                        for face in faces:
                            axis = 'x_faces' if face['location_type'] == 'CARTESIAN_X_FACE' else 'y_faces'
                            np.testing.assert_array_equal(np.array(face['values']).reshape(face['shape']), data[f"{axis}_pi_{face['channel']}"])
                            assert face["quantity"] == "INSTANTANEOUS_PI"
                for asset in evidence['outputs']:
                    assert sha256(root / asset['path']) == asset['sha256']
                allocation = result["allocation"]
                assert allocation["availability"] == "AVAILABLE"
                for channel in ("bg", "aa", "at"):
                    total = sum(a["face_measure"]*sum(a["values"]) for a in allocation["arrays"] if a["channel"] == channel)
                    np.testing.assert_allclose(total, result["entropy"]["totals"][f"E_{channel}"], rtol=1e-10, atol=1e-12)
                    if custom and channel == "at":
                        assert total == 0. and all(v == 0. for a in allocation["arrays"] if a["channel"] == channel for v in a["values"])
                snapshot = result['snapshots'][2]['snapshot_id']
                ctx = http(f"/api/v2/runs/{run_id}/snapshot/{snapshot}/view-context?field=mach&x_min=.25&x_max=.75&y_min=.25&y_max=.75")
                field = http(f"/api/v2/runs/{run_id}/snapshot/{snapshot}/field?field=mach")
                x, y = np.array(field['x']), np.array(field['y'])
                selected = np.array(field['values']).reshape(field['shape'])[np.ix_((y>=.25)&(y<=.75), (x>=.25)&(x<=.75))]
                assert ctx['selected_count'] == selected.size and ctx['mean'] == selected.mean()
                assert ctx['result_hash'] == result['result_hash']
                direct = subprocess.run([sys.executable, '-B', '-m', 'scripts.verification.v2_p4_direct', '--run-id', run_id],
                    cwd=root, env=worker_environment(root), capture_output=True, text=True, timeout=30, check=True)
                save('custom_128x32_qat_zero' if custom else 'fast_64x16', dict(run_id=run_id, result_hash=result['result_hash'],
                    accepted_steps=record['completed_steps'], snapshots=6, fields_compared=36, field_max_abs_error=max_field_error,
                    allocation_scalar_max_abs_error=allocation['max_scalar_abs_error'], selected_region_count=ctx['selected_count'],
                    source_direct_comparison=json.loads(direct.stdout), output_hashes_verified=len(evidence['outputs'])))
            # A newly computed micro Run also retains exact source SSP-RK3 evolution.
            adapter = Case8SolverAdapter()
            smoke = adapter.prepare_run(template_request('case8.fast.D_u'), smoke_steps=3)
            adapter.execute(smoke)
            direct = subprocess.run([sys.executable, '-B', '-m', 'scripts.verification.v2_p2_equivalence', '--run-id', smoke.run_id],
                cwd=smoke.directory, env=worker_environment(smoke.directory), capture_output=True, text=True, check=True, timeout=30)
            save('allocation_observer_source_evolution', json.loads(direct.stdout))
            # Old completed P3 Run: read-only projection, cumulative allocation absent.
            legacy = 'ea852646-72ce-40fc-b5f3-99329ff0895b'
            old = http(f'/api/v2/runs/{legacy}/result')
            assert old['allocation']['availability'] == 'UNAVAILABLE' and old['allocation']['arrays'] is None
            save('legacy_absence', dict(run_id=legacy, result_hash=old['result_hash'], availability='UNAVAILABLE'))
            report.update(status="PASS", finished_at=utc_now())
    except Exception as error:
        report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        write_json(OUT, "p4_live_acceptance.json", report)
        if server and server.poll() is None:
            terminate_worker(server.pid, process_identity(server.pid)); server.wait(timeout=15)


if __name__ == '__main__':
    main()
