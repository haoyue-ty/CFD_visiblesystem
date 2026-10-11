import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time

import pytest

from backend.solver_runtime import artifacts


@pytest.mark.skipif(os.name != 'nt', reason='Windows reader handles deny atomic replacement')
def test_runtime_write_waits_for_real_windows_reader_to_close(tmp_path):
    original, updated = {'heartbeat': 1}, {'heartbeat': 2}
    artifacts.write_json(tmp_path, 'manager.json', original)
    reading = Event()

    def slow_reader():
        with (tmp_path / 'manager.json').open('rb') as stream:
            reading.set()
            time.sleep(.8)
            return json.load(stream)

    with ThreadPoolExecutor(max_workers=1) as pool:
        reader = pool.submit(slow_reader)
        assert reading.wait(5)
        artifacts.write_json(tmp_path, 'manager.json', updated)
        assert reader.result() == original
    assert json.loads((tmp_path / 'manager.json').read_text(encoding='utf-8')) == updated


@pytest.mark.parametrize('winerror', [5, 32, 33])
def test_transient_windows_reader_lock_keeps_atomic_json_commit(tmp_path, monkeypatch, winerror):
    original = {'status': 'RUNNING', 'heartbeat': 1}
    updated = {'status': 'RUNNING', 'heartbeat': 2}
    artifacts.write_json(tmp_path, 'manager.json', original)
    replace = Path.replace
    calls, delays = [], []

    def briefly_locked(source, destination):
        calls.append(destination)
        assert json.loads(Path(destination).read_text(encoding='utf-8')) == original
        if len(calls) < 3:
            error = PermissionError('reader temporarily owns the target')
            error.winerror = winerror
            raise error
        return replace(source, destination)

    monkeypatch.setattr(Path, 'replace', briefly_locked)
    monkeypatch.setattr(artifacts.time, 'sleep', delays.append)
    artifacts.write_json(tmp_path, 'manager.json', updated)
    assert json.loads((tmp_path / 'manager.json').read_text(encoding='utf-8')) == updated
    assert len(calls) == 3
    assert delays == [.01, .02]
    assert not (tmp_path / 'manager.json.tmp').exists()


def test_permanent_windows_lock_is_bounded_and_preserves_previous_record(tmp_path, monkeypatch):
    artifacts.write_json(tmp_path, 'manager.json', {'heartbeat': 1})
    calls = []

    def permanently_locked(source, destination):
        calls.append(destination)
        error = PermissionError('permanent access denial')
        error.winerror = 5
        raise error

    monkeypatch.setattr(Path, 'replace', permanently_locked)
    monkeypatch.setattr(artifacts.time, 'sleep', lambda _: None)
    with pytest.raises(PermissionError):
        artifacts.write_json(tmp_path, 'manager.json', {'heartbeat': 2})
    assert len(calls) == 20
    assert json.loads((tmp_path / 'manager.json').read_text(encoding='utf-8')) == {'heartbeat': 1}


def test_unrelated_permission_error_is_not_retried(tmp_path, monkeypatch):
    calls = []

    def denied(source, destination):
        calls.append(destination)
        raise PermissionError('not a Windows sharing error')

    monkeypatch.setattr(Path, 'replace', denied)
    with pytest.raises(PermissionError):
        artifacts.write_json(tmp_path, 'manager.json', {'heartbeat': 2})
    assert len(calls) == 1
