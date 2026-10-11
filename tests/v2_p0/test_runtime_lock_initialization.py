import os
from pathlib import Path
from threading import Event, Thread, current_thread
import time

import pytest

from backend.solver_runtime.run_store import file_lock


@pytest.mark.skipif(os.name != 'nt', reason='Windows byte-range locks reject competing initialization writes')
def test_new_lock_file_is_safe_when_two_callers_open_it_empty(tmp_path, monkeypatch):
    lock = tmp_path / 'store.lock'
    positioned, owner_holds_lock = Event(), Event()
    failures = []
    open_file = Path.open

    class DelayedContender:
        def __init__(self, stream):
            self.stream = stream
            self.first_seek = True

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def seek(self, *args):
            result = self.stream.seek(*args)
            if self.first_seek:
                self.first_seek = False
                positioned.set()
                assert owner_holds_lock.wait(5)
            return result

    def competing_open(path, *args, **kwargs):
        stream = open_file(path, *args, **kwargs)
        return DelayedContender(stream) if path == lock and current_thread().name == 'lock-contender' else stream

    monkeypatch.setattr(Path, 'open', competing_open)

    def contender():
        try:
            with file_lock(lock):
                pass
        except Exception as error:
            failures.append(error)

    thread = Thread(target=contender, name='lock-contender')
    thread.start()
    try:
        assert positioned.wait(5)
        with file_lock(lock):
            owner_holds_lock.set()
            time.sleep(.1)
    finally:
        owner_holds_lock.set()
        thread.join(5)
    assert not thread.is_alive()
    assert failures == []
    assert lock.read_bytes() == b'\0'
