"""Static Case8 dependency audit: never imports or executes scientific code."""
import argparse
import ast
import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = Path("D:/Paper/passage6")
J2 = "jcp_extension_v1/J2_entropy_diagnostics"
MODULE_ROOTS = {"solver": "", "diagnostics": J2,
                "case8_entropy_observer": f"{J2}/J2B0_case8_integration/code",
                "case8_j2_driver": f"{J2}/J2B0_case8_integration/code"}
SEEDS = ["solver.fluxes.cross_mode_ec_unified_v1", "solver.cases.flagship_cross_modal_case8",
         "solver.core.finite_volume", "solver.core.explicit_ssprk", "case8_j2_driver",
         "case8_entropy_observer", "solver.experiments.baseline_case8_production"]
PROTOCOL = f"{J2}/J2B_case8_formal/J2B_PROTOCOL_LOCK.json"
FORMAL = f"{J2}/J2B_case8_formal/analysis/case8_j2b_formal.py"


def build_manifest(root: Path, *, runtime=False):
    root = root.resolve(strict=True)
    seeds = SEEDS + (["solver.fluxes.registry"] if runtime else [])
    pending, visited, external = list(seeds), {}, set()

    def locate(module):
        base = MODULE_ROOTS.get(module.split(".")[0])
        if base is None:
            return None
        path = root / base / module.replace(".", "/")
        candidates = [path.with_suffix(".py"), path / "__init__.py"]
        found = next((p for p in candidates if p.is_file()), None)
        if found is None:
            raise FileNotFoundError(f"Unresolved selected dependency: {module}")
        if not found.resolve().is_relative_to(root):
            raise ValueError("Dependency escapes selected scientific root")
        return found

    def record(path, module=None, role="dependency"):
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError("Source changed during audit")
        return {"path": path.relative_to(root).as_posix(), "module": module, "role": role,
                "size": before.st_size, "mtime_ns": before.st_mtime_ns,
                "sha256": hashlib.sha256(data).hexdigest()}

    while pending:
        module = pending.pop()
        if module in visited:
            continue
        path = locate(module)
        if path is None:
            external.add(module.split(".")[0])
            continue
        imports = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.Import):
                imports.update(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
                    parts = package.split(".")
                    base = ".".join(parts[:len(parts) - node.level + 1])
                    if node.module:
                        imports.add(base + "." + node.module)
                    else:
                        imports.update(base + "." + item.name for item in node.names)
                elif node.module:
                    imports.add(node.module)
        visited[module] = record(path, module)
        visited[module]["imports"] = sorted(imports)
        pending.extend(imports - visited.keys())
        # Python executes package initializers too, even for named submodules.
        parts = module.split(".")
        pending.extend(".".join(parts[:i]) for i in range(1, len(parts)))

    files = sorted(visited.values(), key=lambda row: row["path"])
    files.extend([record(root / PROTOCOL, role="protocol"), record(root / FORMAL, role="reference_only_do_not_execute")])
    method = next(row for row in files if row["module"] == SEEDS[0])
    expected = "98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0"
    if method["sha256"] != expected:
        raise ValueError("Selected method differs from V1 recorded method hash")
    packages = {}
    for name in ("numpy", "scipy", "matplotlib", "PyYAML"):
        try:
            packages[name] = {"version": version(name), "available": True}
        except PackageNotFoundError:
            packages[name] = {"version": None, "available": False}
    return {"manifest_version": "v2-p2.1" if runtime else "v2-p0.1", "source_root": str(root),
            "selection": MODULE_ROOTS, "seeds": seeds, "files": files,
            "external_imports": sorted(external), "python": sys.version,
            "external_packages": packages,
            "method_hash_matches_v1": True,
            "scope": "Static import closure plus protocol and reference driver; no scientific imports or CFD execution",
            "dynamic_import_policy": "P2 must verify loaded module.__file__ against this allowlist in an isolated worker"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=PROJECT / "docs/v2/source_manifest.json")
    parser.add_argument("--verify", action="store_true", help="Compare against the saved lock; do not rewrite it")
    parser.add_argument("--runtime", action="store_true", help="P2 closure including baseline's from-import flux registry")
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(PROJECT):
        raise ValueError("Audit output must stay inside the software workspace")
    if args.output.resolve().is_relative_to(args.root.resolve()):
        raise ValueError("Audit output must not enter the scientific root")
    document = build_manifest(args.root, runtime=args.runtime)
    if args.verify:
        saved = json.loads(args.output.read_text(encoding="utf-8"))
        # P0 package inventory is historical. Installing runtime extras does not
        # change scientific identity; report environment differences separately.
        source_keys = ("manifest_version", "source_root", "selection", "seeds", "files", "method_hash_matches_v1")
        if any(document[key] != saved[key] for key in source_keys):
            raise ValueError("Scientific source manifest changed")
        print(json.dumps({"status": "PASS", "files": len(document["files"]), "scientific_writes": 0,
                          "environment_changed": document["external_packages"] != saved["external_packages"],
                          "external_packages": document["external_packages"]}))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(document["files"]), "method_hash_matches_v1": True}))


if __name__ == "__main__":
    main()
