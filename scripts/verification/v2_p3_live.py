"""Real HTTP/Waitress, new CFD, cancellation, crash and restart acceptance."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import numpy as np

from backend.core.settings import WORKSPACE_ROOT
from backend.solver_runtime.artifacts import sha256, utc_now, write_json
from backend.solver_runtime.processes import process_identity, terminate_worker
from scripts.run_case8 import template_request
from backend.services.v2.experiments import validate_experiment
from scripts.verification.source_audit import inventory, fingerprint

OUT = WORKSPACE_ROOT / "docs/v2"
BASE = "http://127.0.0.1:5123"


def http(path, body=None, *, expected=200):
    req = Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as response:
            code, payload = response.status, json.load(response)
    except HTTPError as error:
        code, payload = error.code, json.load(error)
    assert code == expected, (path, code, payload)
    return payload


def create(template="case8.fast.D_u", qat=None, *, expected=202, key=None):
    request = template_request(template)
    if qat is not None:
        request.config.method.q_at = qat
    body = {**request.model_dump(mode="json"), "confirmed_config_hash": validate_experiment(request).config_hash,
            "idempotency_key": key or str(uuid4())}
    return body, http("/api/v2/runs", body, expected=expected)


def get(run_id):
    return http("/api/v2/runs/" + run_id)["data"]


def wait(run_id, states, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = get(run_id)
        if record["status"] in states:
            return record
        if record["status"] in ("FAILED", "CANCELLED") and record["status"] not in states:
            raise AssertionError(record)
        time.sleep(.25)
    raise AssertionError("Run wait timed out: " + run_id)


def main():
    from backend.core.settings import Settings
    from backend.solver_runtime.run_store import RunStore
    store = RunStore(Settings())
    if store.manager_available():
        raise RuntimeError("Live acceptance requires an idle runtime without another active manager")
    report = {"status": "RUNNING", "started_at": utc_now(), "checks": {}}
    write_json(OUT, "p3_live_acceptance.json", report)
    log = (OUT / "p3_live_server.log").open("w", encoding="utf-8")
    server = None
    streams = []

    def save(name, value):
        report["checks"][name] = {"status": "PASS", **value}
        write_json(OUT, "p3_live_acceptance.json", report)
        print(json.dumps({"check": name, "status": "PASS"}), flush=True)

    def stop():
        nonlocal server
        for stream in streams:
            stream.close()
        streams.clear()
        if server and server.poll() is None:
            terminate_worker(server.pid, process_identity(server.pid))
            server.wait(timeout=15)
        server = None

    def start(**limits):
        nonlocal server
        env = os.environ | {"API_PORT": "5123", "DEEPSEEK_API_KEY": "", "MAX_RUN_SECONDS": "1800",
                            "MAX_RUN_OUTPUT_BYTES": "67108864", "MAX_QUEUED_RUNS": "3", **limits}
        server = subprocess.Popen([sys.executable, "-B", "-m", "scripts.serve_backend"], cwd=WORKSPACE_ROOT,
                                  env=env, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(150):
            if server.poll() is not None:
                raise RuntimeError("Acceptance HTTP server failed; inspect p3_live_server.log")
            try:
                if http("/api/v2/cases")["data"]["cases"][0]["execution_available"]:
                    return
            except (URLError, OSError):
                pass
            time.sleep(.1)
        raise RuntimeError("HTTP server readiness timeout")

    try:
        start()
        body, first = create()
        a = first["data"]["run_id"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            retries = list(pool.map(lambda _: http("/api/v2/runs", body, expected=202)["data"]["run_id"], range(8)))
        assert set(retries) == {a}
        wait(a, ("RUNNING",))
        _, second = create(qat=0.)
        b = second["data"]["run_id"]
        assert second["data"]["status"] == "QUEUED" and get(b)["worker_pid"] is None
        # Four long SSE streams leave ordinary HTTP and cancellation threads free.
        latency = []
        for _ in range(4):
            stream = urlopen(BASE + "/api/v2/runs/" + a + "/events", timeout=10)
            assert stream.readline().startswith(b"retry:")
            assert stream.readline() == b"\n"
            streams.append(stream)
        try:
            urlopen(BASE + "/api/v2/runs/" + a + "/events", timeout=5)
            raise AssertionError("Fifth event stream was admitted")
        except HTTPError as error:
            assert error.code == 429
        for _ in range(10):
            began = time.monotonic()
            assert http("/api/v2/cases")["data"]["cases"]
            latency.append(time.monotonic() - began)
        assert max(latency) < 2
        save("sse_thread_capacity", {"streams": 4, "fifth_status": 429, "max_normal_api_seconds": max(latency)})
        ar = wait(a, ("COMPLETED",))
        br = wait(b, ("COMPLETED",))
        assert datetime.fromisoformat(br["started_at"]) >= datetime.fromisoformat(ar["finished_at"])
        assert ar["completed_steps"] == br["completed_steps"] == 478
        save("serial_execution_and_idempotency", {"run_a": a, "run_b": b, "retry_count": 8,
                                                  "first_finished": ar["finished_at"], "second_started": br["started_at"]})
        with urlopen(Request(BASE + "/api/v2/runs/" + a + "/events", headers={"Last-Event-ID": str(ar["last_event_id"] - 1)}), timeout=10) as stream:
            assert stream.readline().startswith(b"retry:")
            stream.readline()
            assert stream.readline().strip() == ("id: " + str(ar["last_event_id"])).encode()
            assert stream.readline().strip() == b"event: run"
            final = json.loads(stream.readline().decode().removeprefix("data: "))
            assert final["status"] == "COMPLETED"
        for stream in streams:
            stream.close()
        streams.clear()
        for run_id in (a, b):
            snapshots = http("/api/v2/runs/" + run_id + "/snapshots")["data"]["snapshots"]
            assert len(snapshots) == 6
            sid = snapshots[-1]["snapshot_id"]
            density = http("/api/v2/runs/" + run_id + "/snapshot/" + sid)["data"]
            root = WORKSPACE_ROOT / "runtime/runs" / run_id
            with np.load(root / "final_state.npz") as data:
                assert np.array_equal(np.array(density["values"]).reshape(density["shape"]), data["state"][..., 0])
            assert len(density["x"]) == 64 and len(density["y"]) == 16 and density["time"] == .04
            assert density["source_sha256"] == sha256(root / "snapshots" / (sid + ".npz"))
            assert http("/api/v2/runs/" + run_id + "/history?offset=470&limit=8")["data"]["total"] == 478
        save("density_history_sse_replay", {"run_ids": [a, b], "density": "array exact", "history_rows": 478,
                                           "last_event_id": ar["last_event_id"], "snapshots": 6})
        _, active = create("case8.paper.D_u")
        c = active["data"]["run_id"]
        cr = wait(c, ("RUNNING",))
        queued = [create()[1]["data"]["run_id"] for _ in range(3)]
        create(expected=429)
        for run_id in queued:
            assert http("/api/v2/runs/" + run_id + "/cancel", {})["data"]["status"] == "CANCELLED"
        http("/api/v2/runs/" + c + "/cancel", {})
        assert wait(c, ("CANCELLED",))["cancel_requested"]
        assert process_identity(cr["worker_pid"]) is None
        assert http("/api/v2/runs/" + c + "/snapshot/step_001912", expected=409)["error"]["code"] == "RUN_RESULT_NOT_READY"
        save("queue_capacity_and_cancellation", {"active_run": c, "queued_runs": queued, "worker_stopped": True, "queue_full_status": 429})
        _, crashed = create("case8.paper.D_u")
        d = crashed["data"]["run_id"]
        dr = wait(d, ("RUNNING",))
        terminate_worker(dr["worker_pid"], dr["worker_identity"])
        assert wait(d, ("FAILED",))["failure"] == "WORKER_EXIT"
        save("worker_crash", {"run_id": d, "failure": "WORKER_EXIT"})
        _, interrupted = create("case8.paper.D_u")
        e = interrupted["data"]["run_id"]
        er = wait(e, ("RUNNING",))
        _, preserved = create()
        f = preserved["data"]["run_id"]
        stop()
        start()
        assert get(e)["status"] == "FAILED" and get(e)["failure"] == "WORKER_INTERRUPTED"
        assert process_identity(er["worker_pid"]) is None
        assert wait(f, ("COMPLETED",))["completed_steps"] == 478
        assert http("/api/v2/runs", body, expected=202)["data"]["run_id"] == a
        duplicate = subprocess.run([sys.executable, "-B", "-m", "backend.solver_runtime.run_manager"],
                                   cwd=WORKSPACE_ROOT, capture_output=True, timeout=15)
        assert duplicate.returncode != 0 and b"already owned" in duplicate.stderr
        save("restart_and_duplicate_leader", {"interrupted_run": e, "preserved_queued_run": f,
                                             "failure": "WORKER_INTERRUPTED", "duplicate_leader_rejected": True})
        stop()
        start(MAX_RUN_SECONDS=".2")
        _, timed = create()
        g = timed["data"]["run_id"]
        gr = wait(g, ("FAILED",))
        assert gr["failure"] == "WORKER_TIMEOUT" and process_identity(gr["worker_pid"]) is None
        save("timeout", {"run_id": g, "failure": gr["failure"], "worker_stopped": True})
        stop()
        start(MAX_RUN_OUTPUT_BYTES="1048576")
        _, sized = create()
        h = sized["data"]["run_id"]
        hr = wait(h, ("FAILED",))
        assert hr["failure"] == "RUN_OUTPUT_LIMIT"
        save("output_capacity", {"run_id": h, "failure": hr["failure"], "limit_bytes": 1048576})
        stop()
        source = Path("D:/Paper/passage6")
        rows = inventory(source)
        expected = json.loads((OUT / "p2_source_preservation.json").read_text(encoding="utf-8"))["before_manifest_sha256"]
        assert fingerprint(rows) == expected
        save("scientific_source_preservation", {"files": len(rows), "bytes": sum(r["size"] for r in rows), "fingerprint": expected})
        report.update(status="PASS", finished_at=utc_now())
        write_json(OUT, "p3_live_acceptance.json", report)
    except Exception as error:
        report.update(status="FAIL", error_type=type(error).__name__, message=str(error))
        write_json(OUT, "p3_live_acceptance.json", report)
        raise
    finally:
        stop()
        log.close()


if __name__ == "__main__":
    main()
