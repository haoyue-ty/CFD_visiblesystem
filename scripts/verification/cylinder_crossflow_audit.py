"""Window 2 read-only preservation and frozen contract audit."""
import hashlib
import json
import subprocess
from pathlib import Path

from backend.registry import cylinder_registry as R

WORKTREE = Path(__file__).resolve().parents[2]
BASE_COMMIT = "69a318b65b9378066b9a55e429dfca162cef32af"


def audit():
    source = Path(R.SCIENTIFIC_ROOT)
    baseline = json.loads((WORKTREE / "docs/handoffs/phase8/WINDOW1_SOURCE_PRESERVATION.json").read_text(encoding="utf-8"))
    expected = baseline["before_inventory"]
    current = []
    for item in expected:
        path = source / item["path"]
        observed = path.stat()
        current.append({"path": item["path"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "size_bytes": observed.st_size, "mtime_ns": observed.st_mtime_ns})
    unchanged = current == expected
    directories = {}
    for relative in (R.BASE, "jcp_extension_v1/J2_entropy_diagnostics/J2C_S0_localization_semantics", "Paper/fig/fig_15/FREEZE"):
        actual = {p.relative_to(source).as_posix() for p in (source / relative).rglob("*") if p.is_file()}
        names = {item["path"] for item in expected if item["path"].startswith(relative + "/")}
        directories[relative] = actual == names
    docs = {}
    for name in ("03_USER_FLOW_AND_IA.md", "04_SYSTEM_ARCHITECTURE.md", "05_DATA_SCHEMA.md", "06_API_CONTRACT.md"):
        path = "docs/" + name
        old = subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{path}"], cwd=WORKTREE)
        docs[path] = (WORKTREE / path).read_bytes() == old
    old = json.loads(subprocess.check_output(["git", "show", f"{BASE_COMMIT}:config/openapi.json"], cwd=WORKTREE))
    new = json.loads((WORKTREE / "config/openapi.json").read_text(encoding="utf-8"))
    unchanged_components = all(new["components"]["schemas"].get(k) == v for k, v in old["components"]["schemas"].items())
    phase5_manifest = json.loads((WORKTREE / "docs/PHASE5_CASE8_FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    freeze = phase5_manifest["freeze_record"]
    checkout = (WORKTREE / freeze["path"]).read_bytes()
    accepted = Path("D:/code_project/CFD_visiblesystem") / freeze["path"]
    accepted_bytes = accepted.read_bytes()
    baseline_failure = {"path": freeze["path"], "expected_sha256": freeze["sha256"],
        "checkout_sha256": hashlib.sha256(checkout).hexdigest(),
        "accepted_original_sha256": hashlib.sha256(accepted_bytes).hexdigest(),
        "normalized_bytes_match": checkout.replace(b"\r\n", b"\n") == accepted_bytes.replace(b"\r\n", b"\n"),
        "preexisting_test": "tests/window0_spectral_foundation/test_protocol_and_freeze.py::test_phase4_contract_hashes_and_phase5_phase6_freeze"}
    assert unchanged and all(directories.values()) and all(docs.values()) and unchanged_components
    return {"status": "PASS", "audited_scientific_files": len(expected),
        "baseline": "Window 1 recorded source inventory, before and after hashes identical",
        "before_inventory": expected, "after_inventory": current, "directory_names_preserved": directories,
        "frozen_phase4_documents_preserved": docs, "existing_openapi_components_preserved": unchanged_components,
        "existing_openapi_component_count": len(old["components"]["schemas"]),
        "scientific_files_modified": False, "cfd_runs_started": 0, "preexisting_baseline_failure": baseline_failure}


if __name__ == "__main__":
    report = audit()
    target = WORKTREE / "docs/handoffs/phase8/WINDOW2_SOURCE_PRESERVATION.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {report['audited_scientific_files']} scientific files unchanged; existing OpenAPI components preserved")
