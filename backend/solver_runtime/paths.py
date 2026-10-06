"""Resolve server-owned runtime paths before any future solver writes."""
from pathlib import Path
from uuid import UUID

from backend.core.settings import WORKSPACE_ROOT


def runtime_root(scientific_root: Path, *, workspace: Path = WORKSPACE_ROOT) -> Path:
    workspace = workspace.resolve()
    source = scientific_root.resolve()
    target = (workspace / "runtime").resolve()
    if not target.is_relative_to(workspace) or target == workspace:
        raise ValueError("Runtime must stay inside the software workspace")
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("Runtime and scientific source must be disjoint")
    return target


def run_directory(run_id: str, scientific_root: Path, *, workspace: Path = WORKSPACE_ROOT) -> Path:
    # Generated UUID only. A user/AI cannot choose a directory name or command.
    if str(UUID(run_id)) != run_id:
        raise ValueError("Run identity must be a canonical UUID")
    root = runtime_root(scientific_root, workspace=workspace)
    lexical = workspace.resolve() / "runtime" / "runs" / run_id
    target = lexical.resolve()
    if target != lexical:
        raise ValueError("Run directory links cannot redirect a run identity")
    if not target.is_relative_to(root):
        raise ValueError("Run path escapes runtime")
    if target.is_relative_to(scientific_root.resolve()):
        raise ValueError("Run path enters scientific source")
    return target
