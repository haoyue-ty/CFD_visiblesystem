"""Optional isolated Chromium printing of the already verified HTML report."""
import importlib.util
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys

from backend.core.settings import WORKSPACE_ROOT

_BROWSER_CACHE = {}


class PDFUnavailable(RuntimeError):
    pass


def pdf_capability(settings):
    if not settings.export_pdf_enabled:
        return None, "管理员已关闭 PDF 渲染；HTML 仍可下载。"
    if importlib.util.find_spec("playwright") is None:
        return None, "缺少可选依赖 playwright（安装 ShockPath 的 export-pdf 依赖）；HTML 仍可下载。"
    cached = _BROWSER_CACHE.get(settings.export_pdf_browser)
    if cached and Path(cached).is_file():
        return cached, None
    if not settings.export_pdf_browser:
        # Prefer the browser revision matched to Playwright, when installed.
        # A system Chrome can be managed by policies or updated independently.
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                candidate = Path(playwright.chromium.executable_path)
                if candidate.is_file():
                    _BROWSER_CACHE[settings.export_pdf_browser] = str(candidate)
                    return str(candidate), None
        except Exception:
            pass
    candidates = [settings.export_pdf_browser] if settings.export_pdf_browser else [
        shutil.which(name) for name in ("chromium", "chromium-browser", "google-chrome", "microsoft-edge")]
    if not settings.export_pdf_browser and os.name == "nt":
        for base in (os.getenv("PROGRAMFILES"), os.getenv("PROGRAMFILES(X86)"), os.getenv("LOCALAPPDATA")):
            if base:
                candidates += [str(Path(base) / p) for p in ("Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            resolved = str(Path(candidate).resolve())
            _BROWSER_CACHE[settings.export_pdf_browser] = resolved
            return resolved, None
    return None, "缺少可运行的 Chromium；安装 playwright chromium 或设置 EXPORT_PDF_BROWSER。HTML 仍可下载。"


def render_pdf(html, output, browser, *, timeout):
    env = {key: value for key, value in os.environ.items()
           if not any(word in key.upper() for word in ("API_KEY", "TOKEN", "SECRET", "PASSWORD"))}
    env["PYTHONPATH"] = str(WORKSPACE_ROOT)
    process = None
    try:
        process = subprocess.Popen([sys.executable, "-B", "-m", "backend.services.v2.pdf_worker", str(output), browser],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=WORKSPACE_ROOT, env=env, start_new_session=os.name != "nt")
        process.communicate(input=html.encode("utf-8"), timeout=timeout)
        if process.returncode:
            raise PDFUnavailable("Chromium PDF 渲染失败；HTML 仍可下载。")
        with output.open("rb") as stream:
            if stream.read(5) != b"%PDF-" or output.stat().st_size < 1024:
                raise PDFUnavailable("PDF 渲染未产生有效文档；HTML 仍可下载。")
            stream.seek(max(0, output.stat().st_size - 1024))
            if b"%%EOF" not in stream.read():
                raise PDFUnavailable("PDF 文档未完整生成；HTML 仍可下载。")
    except (subprocess.SubprocessError, OSError) as error:
        output.unlink(missing_ok=True)
        raise PDFUnavailable("Chromium PDF 渲染失败或超时；HTML 仍可下载，可稍后重试 PDF。") from error
    finally:
        if process and process.poll() is None:
            if os.name == "nt":
                from backend.solver_runtime.processes import process_identity, terminate_worker
                terminate_worker(process.pid, process_identity(process.pid))
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
