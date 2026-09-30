"""Canonical registry surface.

The bootstrap loader (software metadata only) is retained unchanged; the Case8
registry adds real, source-bound scientific identities. Registry modules never
load scientific arrays.
"""
from pathlib import Path

from backend.core.settings import WORKSPACE_ROOT
from backend.models import ProjectInfo


def load_bootstrap_project(path: Path | None = None) -> ProjectInfo:
    return ProjectInfo.model_validate_json((path or WORKSPACE_ROOT / "config/bootstrap_project.json").read_text(encoding="utf-8"))


__all__ = ["load_bootstrap_project"]

