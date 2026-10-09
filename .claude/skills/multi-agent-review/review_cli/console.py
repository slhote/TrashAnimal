from __future__ import annotations

import sys
from typing import TextIO


def stdin_is_console(stream: TextIO | None = None) -> bool:
    """True only when a person can type at stdin.

    On Windows, isatty() is also true for the NUL device (`< /dev/null`, or a tool shell whose stdin is NUL), 
    so a real console is confirmed with GetConsoleMode, which fails for anything else.
    """
    stream = stream or sys.stdin
    if not stream.isatty():
        return False
    if sys.platform != "win32":
        return True

    import ctypes
    import msvcrt
    from ctypes import wintypes

    try:
        handle = msvcrt.get_osfhandle(stream.fileno())
    except (OSError, ValueError):
        return False
    console_mode = wintypes.DWORD()
    return bool(ctypes.windll.kernel32.GetConsoleMode(wintypes.HANDLE(handle), ctypes.byref(console_mode)))
