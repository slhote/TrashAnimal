from __future__ import annotations

import os
import sys

# Win32 access right for OpenProcess: the minimum needed to query exit code and start time.
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
ERROR_ACCESS_DENIED = 5
FILETIME_TO_UNIX_SECONDS_OFFSET = 11644473600
CREATION_TIME_TOLERANCE_SECONDS = 5.0


def is_process_alive(pid: int, running_since: float | None = None) -> bool:
    """True if `pid` is a live process that could be the one that stamped `running_since`.

    On Windows a process created after `running_since` is a different process that reused the pid.
    os.kill(pid, 0) is never used on Windows: there it terminates the target process.
    """
    if sys.platform == "win32":
        return _windows_process_alive(pid, running_since)
    return _posix_process_alive(pid)


def _posix_process_alive(pid: int) -> bool:
    try:
        # Doesn't actually kill anything, it just checks if the process exists.
        os.kill(pid, 0)
    except ProcessLookupError:
        # ProcessLookupError: PID doesn't exist
        return False
    except PermissionError:
        # PermissionError: process exists but you can't signal it
        return True

    # No error: process exists
    return True


def _windows_process_alive(pid: int, running_since: float | None) -> bool:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # The process exists but you don't have permission to open it, so it's alive.
        # Other errors mean "the thing doesn't exist."
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        # If we got a handle, this checks if the process is alive and if it's the same process that started at running_since
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) or exit_code.value != STILL_ACTIVE:
            # Process is dead
            return False
        if running_since is None:
            # Process is alive
            return True
        created_at = _windows_creation_time(kernel32, handle, wintypes)

        # On Windows, PIDs get reused. If the old process died and a new one grabbed its PID, 
        # you need the creation timestamp to tell them apart. 
        return created_at is None or created_at <= running_since + CREATION_TIME_TOLERANCE_SECONDS
    finally:
        kernel32.CloseHandle(handle)


def _windows_creation_time(kernel32, handle, wintypes) -> float | None:
    import ctypes

    creation, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    ok = kernel32.GetProcessTimes(
        handle, ctypes.byref(creation), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)
    )
    if not ok:
        return None
    ticks = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    return ticks / 10_000_000 - FILETIME_TO_UNIX_SECONDS_OFFSET
