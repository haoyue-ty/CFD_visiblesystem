from waitress import serve
import subprocess
import sys
import time

from backend import create_app


if __name__ == "__main__":
    app = create_app()
    settings = app.extensions["settings"]
    store = app.extensions["run_store"]
    manager = None
    if not store.manager_available():
        manager = subprocess.Popen([sys.executable, "-B", "-m", "backend.solver_runtime.run_manager"])
        for _ in range(40):
            if store.manager_available():
                break
            if manager.poll() is not None:
                raise RuntimeError("Run manager startup failed (another leader may already own the runtime)")
            time.sleep(.1)
        else:
            manager.terminate()
            manager.wait()
            raise RuntimeError("Run manager did not become ready")
    try:
        serve(app, host=settings.api_host, port=settings.api_port, threads=settings.waitress_threads)
    finally:
        if manager and manager.poll() is None:
            manager.terminate()
            manager.wait(timeout=10)
