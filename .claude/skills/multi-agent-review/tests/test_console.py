import io
import sys

import pytest

from review_cli.console import stdin_is_console


class FakeStream(io.StringIO):
    def __init__(self, tty: bool):
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def test_non_tty_stdin_is_not_a_console():
    assert stdin_is_console(FakeStream(tty=False)) is False


@pytest.mark.skipif(sys.platform != "win32", reason="NUL device only exists on Windows")
def test_nul_device_is_not_a_console_even_though_isatty_is_true():
    with open("NUL", "r") as nul_stream:
        assert nul_stream.isatty() is True
        assert stdin_is_console(nul_stream) is False
