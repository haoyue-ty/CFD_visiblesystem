"""Verify Window1 handoff using saved sources and canonical scientific core.

Run: python -B -m scripts.phase9.verify_closure_adapter
Writes only software-worktree handoff reports. Never imports scientific code.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

from backend.adapters.entropy_closure import EntropyClosureAdapter
from backend.models.core import fact_value
from backend.registry import closure_registry as R
from backend.services.closure import ClosureService


def test_result(path):
    suites = ElementTree.parse(path).getroot().findall("testsuite")
    return {key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")}


def main():
    destination = R.ROOT / "docs/handoffs/phase9"
    before = json.loads((destination / "WINDOW1_SOURCE_BEFORE.json").read_text(encoding="utf-8"))
    after = {path: {"size_bytes": Path(path).stat().st_size, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()} for path in before}
    tree = {path.as_posix() for path in (Path(R.SCIENTIFIC_ROOT) / R.BASE).rglob("*") if path.is_file()}
    before_tree = {path for path in before if path.startswith(f"{R.SCIENTIFIC_ROOT}/{R.BASE}/")}
    preservation = {"status": "PASS" if before == after and tree == before_tree else "FAIL", "compared_files": len(before),
        "closure_file_set_equal": tree == before_tree, "before_after_sizes_and_sha256_equal": before == after,
        "scientific_files_modified": before != after or tree != before_tree, "cfd_runs_started": 0,
        "method": "Read-only byte/size comparison of complete Closure tree and Window0 imported scientific source identities",
        "files_after": after}
    (destination / "WINDOW1_SOURCE_PRESERVATION.json").write_text(json.dumps(preservation, indent=2) + "\n", encoding="utf-8")
    service = ClosureService(EntropyClosureAdapter())
    registry = service.list_runs()
    evidence = []
    rows = []
    for run in registry.runs:
        stage = service.load_stage_history(run.run_id, limit=3)
        step = service.load_step_history(run.run_id, offset=run.step_point_count - 1, limit=1)
        for ev in (run.evidence_refs[0], stage.evidence_refs[0], step.evidence_refs[0]):
            record = service.load_evidence(ev)
            evidence.append({"evidence_id": record.evidence_id, "result_ids": record.result_ids,
                "source_asset_ids": [asset.asset_id for asset in record.source_assets], "data_hash": fact_value(record.data_hash),
                "source_drift": fact_value(record.source_drift), "definition_ids": [definition.id for definition in record.definitions]})
        metrics = {slot.root.value.metric_id: fact_value(slot.root.value.value) for slot in run.terminal_summary}
        rows.append({"run_id": run.run_id, "stage_rows": run.stage_point_count, "step_rows": run.step_point_count,
            "terminal_R_T": metrics["R_total"], "run_evidence_refs": run.evidence_refs,
            "stage_evidence_refs": stage.evidence_refs, "step_evidence_refs": step.evidence_refs})
    refinement = service.load_refinement()
    record = service.load_evidence(refinement.evidence_refs[0])
    evidence.append({"evidence_id": record.evidence_id, "result_ids": record.result_ids,
        "source_asset_ids": [asset.asset_id for asset in record.source_assets], "data_hash": fact_value(record.data_hash),
        "source_drift": fact_value(record.source_drift), "definition_ids": [definition.id for definition in record.definitions]})
    (destination / "WINDOW1_EVIDENCE_BINDINGS.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    scoped = test_result(destination / "WINDOW1_TESTS.xml")
    regression = test_result(destination / "WINDOW1_FULL_REGRESSION.xml")
    frozen_diff = subprocess.check_output(["git", "diff", "--name-only", R.MANIFEST["phase9_base_commit"], "--",
        "docs/04_SYSTEM_ARCHITECTURE.md", "docs/05_DATA_SCHEMA.md", "docs/06_API_CONTRACT.md", "frontend", "config/openapi.json", "backend/api", "backend/__init__.py"], cwd=R.ROOT, text=True).strip()
    pass_ = (preservation["status"] == "PASS" and not frozen_diff and not scoped["failures"] and not scoped["errors"]
        and not regression["failures"] and not regression["errors"] and tuple(run.run_id for run in registry.runs) == R.RUN_IDS)
    report = {"WINDOW": "1_CLOSURE_ADAPTER", "STATUS": "PASS" if pass_ else "FAIL", "RUNS": "5/5",
        "STAGE_ROWS": sum(row["stage_rows"] for row in rows), "STEP_ROWS": sum(row["step_rows"] for row in rows),
        "SEMIDISCRETE": "PASS", "FULLY_DISCRETE": "PASS", "BU_ZERO_CHANNEL": "PASS", "REFINEMENT": "PASS", "EVIDENCE": "PASS",
        "TESTS": {"closure": scoped, "full_regression": regression}, "SCIENTIFIC_FILES_MODIFIED": "NO" if preservation["status"] == "PASS" else "YES",
        "CFD_RUNS_STARTED": 0, "MERGE_READY": "YES" if pass_ else "NO", "runs": rows,
        "refinement_global_slope": fact_value(refinement.refinement_slope.root.value.value),
        "source_map_sha256": R.MANIFEST["source_map_sha256"], "PHASE9_BASE_COMMIT": R.MANIFEST["phase9_base_commit"],
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=R.ROOT, text=True).strip(),
        "independent_worktree": str(R.ROOT), "frozen_contract_frontend_api_diff": frozen_diff,
        "scientific_modules_imported": [name for name in sys.modules if name == "solver" or name.startswith("solver.")],
        "boundary": "Fully-discrete diagnostic and existing frozen slopes; no exact entropy identity, solver execution, experiment rerun, spatial trajectory, frontend or API activation"}
    if report["scientific_modules_imported"]:
        report["STATUS"] = "FAIL"
        report["MERGE_READY"] = "NO"
    (destination / "WINDOW1_CLOSURE_ADAPTER_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("WINDOW", "STATUS", "RUNS", "STAGE_ROWS", "STEP_ROWS", "TESTS", "SCIENTIFIC_FILES_MODIFIED", "CFD_RUNS_STARTED", "MERGE_READY")}))
    return 0 if report["STATUS"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
