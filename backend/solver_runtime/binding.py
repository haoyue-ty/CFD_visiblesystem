"""Only import the hash-locked scientific implementation in an isolated worker."""
import importlib.abc
import importlib.machinery
import importlib.util
import hashlib
import json
from pathlib import Path
import sys

from backend.solver_runtime.artifacts import sha256


class LockedSourceLoader(importlib.machinery.SourceFileLoader):
    """Compile verified source bytes; -B alone still permits reading old .pyc."""
    def __init__(self, name, path, expected_hash):
        super().__init__(name, path)
        self.expected_hash = expected_hash

    def get_code(self, fullname):
        payload = Path(self.path).read_bytes()
        if hashlib.sha256(payload).hexdigest() != self.expected_hash:
            raise ImportError(f"SCIENTIFIC_SOURCE_DRIFT: {fullname}")
        return compile(payload, self.path, "exec", dont_inherit=True)


class ScientificBinding(importlib.abc.MetaPathFinder):
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.root = Path(self.manifest["source_root"]).resolve(strict=True)
        self.modules = {row["module"]: row for row in self.manifest["files"] if row["module"]}
        self.prefixes = set(self.manifest["selection"])
        self.verify_files()

    def verify_files(self):
        for row in self.manifest["files"]:
            path = (self.root / row["path"]).resolve(strict=True)
            if not path.is_relative_to(self.root) or sha256(path) != row["sha256"]:
                raise RuntimeError(f"SCIENTIFIC_SOURCE_DRIFT: {row['path']}")

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] not in self.prefixes:
            return None
        row = self.modules.get(fullname)
        if row is None:
            raise ImportError(f"UNREGISTERED_SCIENTIFIC_IMPORT: {fullname}")
        source = (self.root / row["path"]).resolve(strict=True)
        if not source.is_relative_to(self.root) or sha256(source) != row["sha256"]:
            raise ImportError(f"SCIENTIFIC_SOURCE_DRIFT: {fullname}")
        loader = LockedSourceLoader(fullname, str(source), row["sha256"])
        return importlib.util.spec_from_file_location(fullname, source, loader=loader)

    def install(self):
        if not sys.dont_write_bytecode:
            raise RuntimeError("Scientific worker requires Python -B")
        if any(name.split(".")[0] in self.prefixes for name in sys.modules):
            raise RuntimeError("Scientific modules were imported before binding")
        sys.meta_path.insert(0, self)

    def loaded_modules(self):
        records = []
        for name, module in list(sys.modules.items()):
            if name.split(".")[0] not in self.prefixes:
                continue
            row = self.modules.get(name)
            actual = Path(module.__file__).resolve(strict=True)
            if row is None or actual != (self.root / row["path"]).resolve(strict=True) or sha256(actual) != row["sha256"]:
                raise RuntimeError(f"SCIENTIFIC_IMPORT_IDENTITY_MISMATCH: {name}")
            records.append({"module": name, "path": row["path"], "sha256": row["sha256"]})
        self.verify_files()
        return sorted(records, key=lambda row: row["module"])
