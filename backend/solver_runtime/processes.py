"""Process identities prevent a recovered record from killing a reused PID."""
import ctypes
from ctypes import wintypes
import os
import subprocess


def process_identity(pid):
    if os.name != "nt":
        from pathlib import Path
        try:
            return str(pid) + ":" + Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
        except (OSError, IndexError):
            return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    times = [wintypes.FILETIME() for _ in range(4)]
    try:
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            return None
        return f"{pid}:{(times[0].dwHighDateTime << 32) | times[0].dwLowDateTime}"
    finally:
        kernel.CloseHandle(handle)


def terminate_worker(pid, identity):
    if not identity or process_identity(pid) != identity:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
    else:
        import signal
        os.kill(pid, signal.SIGKILL)
