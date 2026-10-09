import asyncio
import itertools
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from conftest import FakeGit, FakeRunner, reviewer_finding
from review_cli.arguments import parse_arguments
from review_cli.exit_codes import EXIT_USAGE, EXIT_USER_INPUT_NEEDED
from review_cli.run_planning import ExitRequested, plan_fresh_run, plan_resume, plan_run, require_resumable_thread
from review_cli.session import ReviewSession
from review_graph.graph import GraphDependencies, build_graph
from review_graph.runner import RunLimits
from review_graph.thread_registry import ThreadRegistry

PR_53 = {"kind": "pr", "value": 53}


def args_for(*argv):
    return parse_arguments(list(argv))


@pytest.fixture
def registry(tmp_path):
    ticks = itertools.count(100)
    return ThreadRegistry(tmp_path / "registry.sqlite", clock=lambda: float(next(ticks)), current_pid=lambda: 4242)


class FakeGraph:
    def __init__(self, pending_by_thread, scope_args=None):
        self.pending_by_thread = pending_by_thread
        self.scope_args = scope_args or {}

    async def aget_state(self, config):
        thread_id = config["configurable"]["thread_id"]
        return SimpleNamespace(
            next=self.pending_by_thread.get(thread_id, ()), values={"scope_args": self.scope_args, "verdict": None}
        )


def make_session(registry, graph, interactive=False, read_line=input, alive=False):
    return ReviewSession(graph, registry, interactive, read_line, is_alive=lambda pid, since: alive)


def open_thread(registry, thread_id, label="pr-53"):
    registry.begin(thread_id, label, fresh=True)
    registry.mark_idle(thread_id)


def run(coroutine):
    return asyncio.run(coroutine)


def test_explicit_finished_thread_is_refused_with_usage_exit(registry, capsys):
    open_thread(registry, "done")
    with pytest.raises(ExitRequested) as refused:
        run(require_resumable_thread("done", make_session(registry, FakeGraph({}))))
    assert refused.value.code == EXIT_USAGE and "nothing to resume" in capsys.readouterr().err


def test_explicit_thread_owned_by_a_live_process_is_refused(registry, capsys):
    registry.begin("busy", "pr-53", fresh=True)
    session = make_session(registry, FakeGraph({"busy": ("approval",)}), alive=True)
    with pytest.raises(ExitRequested):
        run(require_resumable_thread("busy", session))
    assert "running process" in capsys.readouterr().err


def test_explicit_unfinished_thread_is_accepted(registry):
    open_thread(registry, "crashed")
    run(require_resumable_thread("crashed", make_session(registry, FakeGraph({"crashed": ("reviewer",)}))))


def test_resume_with_filter_picks_the_single_matching_review(registry):
    open_thread(registry, "pr-53-1")
    session = make_session(registry, FakeGraph({"pr-53-1": ("approval",)}, scope_args=PR_53))
    plan = run(plan_resume(args_for("--resume", "--pr", "53"), PR_53, session))
    assert plan.thread_id == "pr-53-1" and not plan.fresh and plan.registry_label == "pr-53"


def test_resume_in_a_terminal_lets_the_user_choose_from_the_menu(registry):
    open_thread(registry, "a")
    open_thread(registry, "b")
    graph = FakeGraph({"a": ("reviewer",), "b": ("approval",)})
    session = make_session(registry, graph, interactive=True, read_line=lambda prompt: "1")
    plan = run(plan_resume(args_for("--resume"), {"kind": "default"}, session))
    assert plan.thread_id == "b"  # newest first


def test_resume_without_a_tty_lists_open_reviews_and_exits_4(registry, capsys):
    open_thread(registry, "a")
    open_thread(registry, "b")
    session = make_session(registry, FakeGraph({"a": ("reviewer",), "b": ("approval",)}))
    with pytest.raises(ExitRequested) as needed:
        run(plan_resume(args_for("--resume"), {"kind": "default"}, session))
    assert needed.value.code == EXIT_USER_INPUT_NEEDED
    assert '"reason": "choose"' in capsys.readouterr().out


def test_resume_with_no_match_exits_4_instead_of_starting_a_review(registry, capsys):
    open_thread(registry, "a")
    session = make_session(registry, FakeGraph({"a": ("reviewer",)}, scope_args={"kind": "pr", "value": 99}))
    with pytest.raises(ExitRequested) as needed:
        run(plan_resume(args_for("--resume", "--pr", "53"), PR_53, session))
    assert needed.value.code == EXIT_USER_INPUT_NEEDED
    assert '"reason": "none_match"' in capsys.readouterr().out


def test_decision_is_passed_to_a_thread_waiting_for_approval(registry):
    open_thread(registry, "paused")
    session = make_session(registry, FakeGraph({"paused": ("approval",)}))
    plan = run(plan_resume(args_for("--resume", "--thread-id", "paused", "--decision", "approved"), {}, session))
    assert isinstance(plan.graph_input, Command) and plan.graph_input.resume == "approved"


def test_decision_is_dropped_with_a_warning_for_an_unfinished_thread(registry, capsys):
    open_thread(registry, "crashed")
    session = make_session(registry, FakeGraph({"crashed": ("reviewer",)}))
    plan = run(plan_resume(args_for("--resume", "--thread-id", "crashed", "--decision", "approved"), {}, session))
    assert plan.graph_input is None and "ignoring --decision" in capsys.readouterr().err


def test_resuming_a_thread_missing_from_the_registry_labels_it_with_its_id(registry):
    session = make_session(registry, FakeGraph({"old": ("approval",)}))
    plan = run(plan_resume(args_for("--resume", "--thread-id", "old"), {}, session))
    assert plan.thread_id == "old" and plan.registry_label == "old"


def test_fresh_run_builds_scope_input_and_a_timestamped_thread_id(registry):
    plan = run(plan_fresh_run(args_for("--pr", "53"), PR_53, "pr-53", make_session(registry, FakeGraph({}))))
    assert plan.fresh and plan.graph_input == {"scope_args": PR_53}
    assert plan.thread_id.startswith("pr-53-")


def test_fresh_run_on_a_stable_thread_id_uses_it_and_warns_when_unfinished(registry, capsys):
    session = make_session(registry, FakeGraph({"pr-53": ("reviewer",)}))
    plan = run(plan_fresh_run(args_for("--pr", "53", "--thread-id", "pr-53"), {}, "pr-53", session))
    assert plan.thread_id == "pr-53" and "unfinished review" in capsys.readouterr().err


def test_plan_run_dispatches_on_the_resume_flag(registry):
    session = make_session(registry, FakeGraph({"x": ("approval",)}))
    assert run(plan_run(args_for("--resume", "--thread-id", "x"), {}, "branch", session)).fresh is False
    assert run(plan_run(args_for(), {"kind": "default"}, "branch", session)).fresh is True


def test_paused_review_on_a_real_graph_is_listed_resumed_and_then_gone(registry, specs):
    limits = RunLimits(max_attempts=1)
    runner = FakeRunner({"backend-reviewer": [reviewer_finding(severity="high")]})
    deps = GraphDependencies(runner, FakeGit({"TrashAnimal/A.cs": [(1, 100)]}), specs, limits, limits)
    session = make_session(registry, build_graph(deps, MemorySaver()))

    async def scenario():
        registry.begin("branch-1", "branch", fresh=True)
        await session.invoke("branch-1", {"scope_args": {"kind": "default"}})
        registry.mark_idle("branch-1")
        listed = await session.find_open_reviews()

        plan = await plan_resume(
            args_for("--resume", "--thread-id", "branch-1", "--decision", "approved"), {}, session
        )
        registry.begin(plan.thread_id, plan.registry_label, fresh=plan.fresh)
        await session.invoke(plan.thread_id, plan.graph_input)
        registry.remove("branch-1")
        return listed, await session.find_open_reviews()

    listed, after = run(scenario())
    assert [(t.thread_id, t.kind, t.scope_args) for t in listed.threads] == [
        ("branch-1", "PAUSED_APPROVAL", {"kind": "default"})
    ]
    assert after.threads == [] and registry.get("branch-1") is None
