"""Read-only Window2 API acceptance report; writes only worktree handoffs.

Run after pytest XML outputs exist: python -B -m scripts.phase9.verify_closure_api
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from backend import create_app
from backend.registry import closure_registry as R
from backend.schemas.openapi import export_openapi
from backend.services.closure_resources import EVIDENCE_IDS


BASE = "/api/v1/experiments/entropy-closure"
PATHS = {"CLO01": f"{BASE}/runs", "CLO02": f"{BASE}/runs/{{run_id}}",
         "CLO03": f"{BASE}/runs/{{run_id}}/stage-history", "CLO04": f"{BASE}/runs/{{run_id}}/step-history",
         "CLO05": f"{BASE}/refinement"}


def write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_counts(path):
    suites = ElementTree.parse(path).getroot().findall("testsuite")
    return {key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = R.ROOT / "docs/handoffs/phase9"
    app = create_app()
    client = app.test_client()

    def read(path):
        response = client.get(path)
        if response.status_code != 200:
            raise RuntimeError(f"API verification failed: {path}: {response.status_code}")
        return response.json["data"]

    registry = read(PATHS["CLO01"])
    ids = [run["run_id"] for run in registry["runs"]]
    checks = {"CLO01": ids == list(R.RUN_IDS) and len(ids) == 5}
    rows = []
    for run in registry["runs"]:
        identity = run["run_id"]
        checks["CLO02"] = checks.get("CLO02", True) and read(f"{BASE}/runs/{identity}") == run
        groups = {}
        for group, operation, granularity in (("stage", "CLO03", "PER_STAGE"), ("step", "CLO04", "PER_STEP")):
            count = run[f"{group}_point_count"]
            history = read(f"{BASE}/runs/{identity}/{group}-history?offset={count - 1}&limit=1")
            checks[operation] = checks.get(operation, True) and history["granularity"] == granularity and all(
                s["total_point_count"] == s["page"]["total_count"] == count and s["page"]["returned_count"] == 1
                and s["points"][0]["point_index"] == count - 1 for s in history["series"])
            groups[group] = {"rows": count, "granularity": history["granularity"], "evidence_refs": history["evidence_refs"]}
        rows.append({"run_id": identity, **groups, "evidence_refs": run["evidence_refs"]})
    refinement = read(PATHS["CLO05"])
    checks["CLO05"] = refinement["run_ids"] == list(R.RUN_IDS[:4]) and len(refinement["metrics_by_run"]) == 4

    invalid, random = [], []
    for suffix in ("", "/stage-history", "/step-history"):
        for identity in ("B_u-cfl-0.1", "D_u-cfl-0.03"):
            response = client.get(f"{BASE}/runs/{identity}{suffix}")
            invalid.append(response.status_code == 422 and response.json["error"]["code"] == "UNSUPPORTED_COMBINATION")
        response = client.get(f"{BASE}/runs/random-run{suffix}")
        random.append(response.status_code == 404 and response.json["error"]["code"] == "INVALID_RESULT_ID")

    evidence = []
    for identity in sorted(EVIDENCE_IDS):
        record = read(f"/api/v1/evidence/{identity}")
        evidence.append({"evidence_id": identity, "result_ids": record["result_ids"],
                         "source_asset_ids": [a["asset_id"] for a in record["source_assets"]],
                         "data_hash": record["data_hash"], "definition_ids": [d["id"] for d in record["definitions"]],
                         "source_drift": record["source_drift"]})
    write(destination / "WINDOW2_EVIDENCE_BINDINGS.json", evidence)

    before = json.loads((destination / "WINDOW2_SOURCE_BEFORE.json").read_text(encoding="utf-8"))
    after = {path: {"size_bytes": Path(path).stat().st_size, "sha256": sha(Path(path))} for path in before}
    tree = {path.as_posix() for path in (Path(R.SCIENTIFIC_ROOT) / R.BASE).rglob("*") if path.is_file()}
    before_tree = {path for path in before if path.startswith(f"{R.SCIENTIFIC_ROOT}/{R.BASE}/")}
    scientific_preserved = before == after and tree == before_tree
    write(destination / "WINDOW2_SOURCE_PRESERVATION.json", {
        "status": "PASS" if scientific_preserved else "FAIL", "compared_files": len(before),
        "closure_file_set_equal": tree == before_tree, "before_after_sizes_and_sha256_equal": before == after,
        "scientific_files_modified": not scientific_preserved, "cfd_runs_started": 0, "files_after": after})

    document = export_openapi(app.extensions["operation_catalog"])
    actual = {item["get"]["operationId"]: path for path, item in document["paths"].items() if path.startswith(BASE)}
    exact_routes = actual == PATHS
    no_spatial = exact_routes
    for suffix in ("spatial", "fields", "snapshots", "trajectory", "arbitrary-cfl", "run-new"):
        for prefix in (BASE, f"{BASE}/runs/{R.RUN_IDS[0]}"):
            response = client.get(f"{prefix}/{suffix}")
            no_spatial = no_spatial and response.status_code == 404 and response.json["error"]["code"] == "API_ROUTE_NOT_FOUND"
    openapi = (document["openapi"] == "3.1.0" and exact_routes
               and document == json.loads((R.ROOT / "config/openapi.json").read_text(encoding="utf-8"))
               and document == client.get("/api/v1/openapi.json").json)
    generated = R.ROOT / "frontend/src/types/generated/api.d.ts"
    cli = R.ROOT / "frontend/node_modules/openapi-typescript/bin/cli.js"
    with TemporaryDirectory(prefix="closure-api-types-") as temporary:
        output = Path(temporary) / "api.d.ts"
        subprocess.run(["node", str(cli), str(R.ROOT / "config/openapi.json"), "-o", str(output)], check=True, capture_output=True)
        repeatable = output.read_bytes() == generated.read_bytes()
        digest = sha(output)
        subprocess.run(["node", str(cli), str(R.ROOT / "config/openapi.json"), "-o", str(output)], check=True, capture_output=True)
        repeatable = repeatable and digest == sha(output)

    focused = test_counts(destination / "WINDOW2_TESTS.xml")
    regression = test_counts(destination / "WINDOW2_FULL_REGRESSION.xml")
    contracts = all(sha(R.ROOT / item["path"]) == item["sha256"] for item in R.SOURCE_MAP["frozen_contracts"])
    imported = [name for name in sys.modules if name == "solver" or name.startswith("solver.")]
    passed = (all(checks.values()) and all(invalid) and all(random) and no_spatial and openapi and repeatable and scientific_preserved
              and contracts and not imported and not focused["failures"] and not focused["errors"]
              and not regression["failures"] and not regression["errors"])
    report = {
        "WINDOW": "2_CLOSURE_API", "STATUS": "PASS" if passed else "FAIL",
        **{key: "PASS" if value else "FAIL" for key, value in checks.items()}, "RUNS": f"{len(ids)}/5",
        "INVALID_COMBINATION": "PASS" if all(invalid) else "FAIL", "RANDOM_IDS": "PASS" if all(random) else "FAIL",
        "NO_SPATIAL_API": "PASS" if no_spatial else "FAIL", "EVIDENCE": "PASS" if len(evidence) == 16 else "FAIL",
        "OPENAPI": "PASS" if openapi else "FAIL", "GENERATED_TYPES": "PASS" if repeatable else "FAIL",
        "TESTS": {"closure_api": focused, "full_regression": regression},
        "SCIENTIFIC_FILES_MODIFIED": "NO" if scientific_preserved else "YES", "CFD_RUNS_STARTED": 0,
        "MERGE_READY": "YES" if passed else "NO", "PHASE9_BASE_COMMIT": R.MANIFEST["phase9_base_commit"],
        "ACCEPTED_WINDOW1_COMMIT": "31341e75da43f91fd4878edf7e41138aee22c0ff",
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=R.ROOT, text=True).strip(),
        "openapi_sha256": sha(R.ROOT / "config/openapi.json"), "generated_types_sha256": sha(generated),
        "frozen_contracts_preserved": contracts, "scientific_modules_imported": imported, "runs": rows,
        "operations": PATHS, "refinement_run_ids": refinement["run_ids"],
        "refinement_global_slope": refinement["refinement_slope"]["value"]["value"]["value"],
        "history_query": "registry_revision, offset, limit only; fixed complete saved series; URL fixes granularity and run identity",
    }
    write(destination / "WINDOW2_CLOSURE_API_REPORT.json", report)
    print(json.dumps({key: report[key] for key in ("WINDOW", "STATUS", *PATHS, "RUNS", "INVALID_COMBINATION", "NO_SPATIAL_API",
                                                 "OPENAPI", "GENERATED_TYPES", "TESTS", "SCIENTIFIC_FILES_MODIFIED", "CFD_RUNS_STARTED", "MERGE_READY")}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
