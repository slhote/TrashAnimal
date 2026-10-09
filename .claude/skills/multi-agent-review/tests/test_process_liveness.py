import os
import subprocess
import sys
import time

import pytest

from review_graph.process_liveness import is_process_alive


def test_current_process_is_alive():
    assert is_process_alive(os.getpid(), time.time())


def test_exited_process_is_not_alive():
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    assert not is_process_alive(child.pid, time.time())


def test_nonexistent_pid_is_not_alive():
    assert not is_process_alive(2**22 + 12345)


@pytest.mark.skipif(sys.platform != "win32", reason="creation-time pid-reuse check is Windows-only")
def test_process_created_after_the_stamp_is_treated_as_a_reused_pid():
    assert not is_process_alive(os.getpid(), running_since=0.0)
