import asyncio
import itertools
from types import SimpleNamespace

import pytest
from langgraph.types import Command

from review_cli.run_execution import Completed, Paused, ask_for_decision, execute_run
from review_cli.run_planning import RunPlan
from review_cli.session import ReviewSession
from review_graph.thread_registry import ThreadRegistry


@pytest.fixture
def registry(tmp_path):
    ticks = itertools.count(100)
    return ThreadRegistry(tmp_path / "registry.sqlite", clock=lambda: float(next(ticks)), current_pid=lambda: 4242)


class ScriptedGraph:
    """Returns the scripted results in order and records each invoke."""

    def __init__(self, *results, error=None):
        self.results = list(results)
        self.error = error
        self.inputs = []

    async def ainvoke(self, graph_input, config):
        self.inputs.append((graph_input, config["configurable"]["thread_id"]))
        if self.error:
            raise self.error
        return self.results.pop(0)


def interrupt(**payload):
    return {"__interrupt__": [SimpleNamespace(value=payload)]}


def session_for(registry, graph, interactive=False, answers=()):
    queue = iter(answers)
    return ReviewSession(graph, registry, interactive, read_line=lambda prompt: next(queue), is_alive=lambda p, s: False)


def plan_for(thread_id="t1"):
    return RunPlan(thread_id, {"scope_args": {"kind": "default"}}, "branch", fresh=True)


def run(coroutine):
    return asyncio.run(coroutine)


def test_completed_review_returns_its_result_and_removes_the_thread_row(registry):
    graph = ScriptedGraph({"verdict": "CLEAR"})
    outcome = run(execute_run(session_for(registry, graph), plan_for()))
    assert outcome == Completed({"verdict": "CLEAR"}) and registry.get("t1") is None


def test_row_is_marked_running_while_the_graph_runs(registry):
    seen = []

    class Watching(ScriptedGraph):
        async def ainvoke(self, graph_input, config):
            seen.append(registry.get("t1").running_since)
            return await super().ainvoke(graph_input, config)

    run(execute_run(session_for(registry, Watching({"verdict": "CLEAR"})), plan_for()))
    assert seen[0] is not None


def test_unanswerable_approval_pauses_and_leaves_an_idle_row_for_resume(registry):
    graph = ScriptedGraph(interrupt(verdict="REQUIRES_APPROVAL", high_findings=["x"]))
    outcome = run(execute_run(session_for(registry, graph), plan_for()))
    assert outcome == Paused("t1", {"verdict": "REQUIRES_APPROVAL", "high_findings": ["x"]})
    record = registry.get("t1")
    assert record is not None and record.running_since is None


def test_approval_answered_in_a_terminal_resumes_the_graph_in_the_same_process(registry):
    graph = ScriptedGraph(interrupt(high_findings=["x"]), {"verdict": "REQUIRES_APPROVAL", "approval_decision": "approved"})
    outcome = run(execute_run(session_for(registry, graph, interactive=True, answers=["y"]), plan_for()))
    assert isinstance(outcome, Completed) and outcome.result["approval_decision"] == "approved"
    resumed_input, _ = graph.inputs[1]
    assert isinstance(resumed_input, Command) and resumed_input.resume == "approved"
    assert registry.get("t1") is None


def test_exception_propagates_and_the_row_is_marked_idle(registry):
    graph = ScriptedGraph(error=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        run(execute_run(session_for(registry, graph), plan_for()))
    record = registry.get("t1")
    assert record is not None and record.running_since is None


def test_ask_for_decision_never_prompts_without_a_terminal():
    def fail(prompt):
        raise AssertionError("must not prompt")

    assert ask_for_decision({"high_findings": ["x"]}, interactive=False, read_line=fail) is None


@pytest.mark.parametrize("answer,expected", [("y", "approved"), ("YES", "approved"), ("n", "rejected"), ("", "rejected")])
def test_ask_for_decision_maps_the_answer(answer, expected):
    assert ask_for_decision({}, interactive=True, read_line=lambda prompt: answer) == expected
