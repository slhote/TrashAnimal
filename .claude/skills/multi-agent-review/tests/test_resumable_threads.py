import asyncio
import itertools
from types import SimpleNamespace

import pytest

from review_graph.resumable_threads import find_resumable
from review_graph.thread_registry import ThreadRegistry


@pytest.fixture
def registry(tmp_path):
    ticks = itertools.count(100)
    return ThreadRegistry(tmp_path / "registry.sqlite", clock=lambda: float(next(ticks)), current_pid=lambda: 4242)


def snapshots(**next_nodes_by_thread):
    async def get_state(thread_id):
        pending, verdict = next_nodes_by_thread[thread_id]
        return SimpleNamespace(next=pending, values={"verdict": verdict})

    return get_state


def find(registry, get_state, alive=False):
    return asyncio.run(find_resumable(registry, get_state, is_alive=lambda pid, since: alive))


def idle_thread(registry, thread_id):
    registry.begin(thread_id, thread_id, fresh=True)
    registry.mark_idle(thread_id)


def test_thread_waiting_at_the_approval_node_is_paused_for_approval(registry):
    idle_thread(registry, "pr-1")
    [thread] = find(registry, snapshots(**{"pr-1": (("approval",), "REQUIRES_APPROVAL")}))
    assert thread.kind == "PAUSED_APPROVAL" and thread.verdict == "REQUIRES_APPROVAL"


def test_thread_with_other_work_left_and_no_owner_is_unfinished(registry):
    idle_thread(registry, "pr-1")
    [thread] = find(registry, snapshots(**{"pr-1": (("reviewer",), None)}))
    assert thread.kind == "UNFINISHED" and thread.scope_label == "pr-1"


def test_killed_process_leaves_running_since_set_and_is_unfinished(registry):
    registry.begin("pr-1", "pr-1", fresh=True)
    [thread] = find(registry, snapshots(**{"pr-1": (("verify_findings",), None)}), alive=False)
    assert thread.kind == "UNFINISHED"


def test_thread_owned_by_a_live_process_is_skipped_without_reading_its_checkpoint(registry):
    registry.begin("pr-1", "pr-1", fresh=True)
    reads = []

    async def get_state(thread_id):
        reads.append(thread_id)
        return SimpleNamespace(next=("approval",), values={})

    assert find(registry, get_state, alive=True) == [] and reads == []


def test_live_process_check_receives_the_stored_pid_and_start_time(registry):
    registry.begin("pr-1", "pr-1", fresh=True)
    seen = []
    asyncio.run(find_resumable(registry, snapshots(**{"pr-1": ((), None)}), lambda pid, since: seen.append((pid, since))))
    assert seen == [(4242, registry.get("pr-1").running_since)]


def test_finished_or_never_started_threads_are_not_resumable(registry):
    idle_thread(registry, "done")
    idle_thread(registry, "never-started")
    assert find(registry, snapshots(done=((), "CLEAR"), **{"never-started": ((), None)})) == []


def test_results_are_newest_first_and_mix_both_kinds(registry):
    idle_thread(registry, "older")
    idle_thread(registry, "newer")
    found = find(registry, snapshots(older=(("reviewer",), None), newer=(("approval",), "REQUIRES_APPROVAL")))
    assert [(t.thread_id, t.kind) for t in found] == [("newer", "PAUSED_APPROVAL"), ("older", "UNFINISHED")]
