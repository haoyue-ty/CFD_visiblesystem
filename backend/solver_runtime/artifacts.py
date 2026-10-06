"""Run-local writes with containment checks and atomic JSON commits."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def target(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()) or path.resolve() == root.resolve():
        raise ValueError("Artifact path escapes the run")
    # Refuse even internal links: all run output is newly owned by this worker.
    for part in path.parents:
        if part == root.parent:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Linked artifact directory is not allowed")
        if part == root:
            break
    if path.is_symlink():
        raise ValueError("Linked artifact is not allowed")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(root: Path, relative: str, value):
    path = target(root, relative)
    temporary = target(root, relative + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                                    allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def output_inventory(root: Path):
    # Mutable process log and lifecycle are not scientific result identity.
    return [{"path": p.relative_to(root).as_posix(), "size": p.stat().st_size, "sha256": sha256(p)}
            for p in sorted(root.rglob("*")) if p.is_file()
            and p.relative_to(root).parts[0] not in ("cache", "tmp", "ai", "report")
            and not p.name.endswith(".tmp")
            and p.name not in ("status.json", "run_control.json", "provenance.json", "solver.log")]
