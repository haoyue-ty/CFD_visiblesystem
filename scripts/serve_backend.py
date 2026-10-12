from waitress import serve
import subprocess
import sys
import time

from backend import create_app
from backend.core.settings import WORKSPACE_ROOT
from dotenv import load_dotenv


def main():
    load_dotenv(WORKSPACE_ROOT / '.env', override=False, interpolate=False)
    print("ShockPath 后端正在初始化…", flush=True)
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
        print(f"正在启动后端 HTTP 服务：http://{settings.api_host}:{settings.api_port}", flush=True)
        print("此服务会持续运行，请保持窗口打开；在终端按 Ctrl+C 可停止。", flush=True)
        serve(app, host=settings.api_host, port=settings.api_port, threads=settings.waitress_threads)
    finally:
        if manager and manager.poll() is None:
            manager.terminate()
            manager.wait(timeout=10)


if __name__ == "__main__":
    main()
