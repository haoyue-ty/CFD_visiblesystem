import pytest


@pytest.fixture(autouse=True)
def offline_run_service(monkeypatch):
    # P1 checks configuration independently of any live server on the machine.
    from backend.solver_runtime.run_store import RunStore
    monkeypatch.setattr(RunStore, "manager_available", lambda self: False)
