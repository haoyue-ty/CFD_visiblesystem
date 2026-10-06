from pathlib import Path
import os
import subprocess
from uuid import uuid4

import pytest

from backend.solver_runtime.paths import run_directory, runtime_root


def test_runtime_is_server_owned_and_resolution_does_not_write(tmp_path):
    workspace, source = tmp_path / "software", tmp_path / "science"
    identity = str(uuid4())
    path = run_directory(identity, source, workspace=workspace)
    assert path == workspace / "runtime" / "runs" / identity
    assert not workspace.exists() and not source.exists()


@pytest.mark.parametrize("identity", ["../science", "D:/Paper", "run-1", "", "00000000000000000000000000000000"])
def test_untrusted_run_path_rejected(tmp_path, identity):
    with pytest.raises(ValueError):
        run_directory(identity, tmp_path / "source", workspace=tmp_path)


def test_overlapping_scientific_source_rejected(tmp_path):
    for source in (tmp_path, tmp_path / "runtime", tmp_path / "runtime/science"):
        with pytest.raises(ValueError):
            runtime_root(source, workspace=tmp_path)


def test_runtime_symlink_escape_rejected(tmp_path):
    workspace = tmp_path / "software"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (workspace / "runtime").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Windows symlink privilege unavailable")
    with pytest.raises(ValueError):
        runtime_root(tmp_path / "source", workspace=workspace)


@pytest.mark.skipif(os.name != "nt", reason="Windows directory junctions")
@pytest.mark.parametrize("link_location", ["runtime", "runtime/runs"])
def test_windows_junction_escape_rejected(tmp_path, link_location):
    workspace = tmp_path / "software"
    link = workspace / link_location
    link.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    env = os.environ | {"SHOCKPATH_TEST_LINK": str(link), "SHOCKPATH_TEST_TARGET": str(outside)}
    subprocess.run(["pwsh", "-NoProfile", "-Command",
                    "New-Item -ItemType Junction -Path $env:SHOCKPATH_TEST_LINK -Target $env:SHOCKPATH_TEST_TARGET -ErrorAction Stop | Out-Null"],
                   env=env, check=True, capture_output=True)
    with pytest.raises(ValueError):
        run_directory(str(uuid4()), tmp_path / "source", workspace=workspace)
