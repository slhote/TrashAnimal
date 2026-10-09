import asyncio
from unittest.mock import patch

import pytest

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from conftest import FakeGit, FakeRunner, reviewer_finding
from review_graph.graph import GraphDependencies, build_graph
from review_graph.runner import RunLimits
from review_graph.state import RESET, accumulate, fresh_run_state

CS_HUNKS = {"TrashAnimal/A.cs": [(1, 100)]}
LIMITS = RunLimits(max_attempts=1)


def make_graph(specs, runner, git, checkpointer=None):
    deps = GraphDependencies(runner=runner, git=git, specs=specs, reviewer_limits=LIMITS, verifier_limits=LIMITS)
    return build_graph(deps, checkpointer or MemorySaver())


def invoke(graph, graph_input, thread="t1"):
    config = {"configurable": {"thread_id": thread}}
    return asyncio.run(graph.ainvoke(graph_input, config))


START = {"scope_args": {"kind": "default"}}


def test_docs_only_change_skips_review_and_reports():
    runner = FakeRunner()
    result = invoke(make_graph({}, runner, FakeGit({"README.md": None})), START)
    assert runner.calls == [] and result["docs_only"] is True
    assert "No code changed" in result["report_markdown"]


def test_clean_review_runs_phase_one_then_architecture_and_is_clear(specs):
    runner = FakeRunner()
    result = invoke(make_graph(specs, runner, FakeGit(CS_HUNKS)), START)
    assert result["verdict"] == "CLEAR"
    assert runner.calls[-1] == "architecture-reviewer"
    assert set(runner.calls[:-1]) == {"backend-reviewer", "security-reviewer", "testing-reviewer"}
    assert "architecture-reviewer" in runner.prompts and "build on these" in runner.prompts["architecture-reviewer"]


def test_failed_security_reviewer_blocks_merge_and_is_reported(specs):
    runner = FakeRunner(failing={"security-reviewer"})
    result = invoke(make_graph(specs, runner, FakeGit(CS_HUNKS)), START)
    assert result["verdict"] == "BLOCK_MERGE" and result["incomplete_reviews"] == ["security-reviewer"]
    assert "did not complete" in result["report_markdown"] and "BLOCK MERGE" in result["report_markdown"]


def test_high_finding_pauses_for_approval_then_resumes(specs):
    runner = FakeRunner({"backend-reviewer": [reviewer_finding(severity="high", summary="real problem")]})
    graph = make_graph(specs, runner, FakeGit(CS_HUNKS))
    paused = invoke(graph, START)
    assert paused["__interrupt__"][0].value["verdict"] == "REQUIRES_APPROVAL"
    final = invoke(graph, Command(resume="approved"))
    assert final["approval_decision"] == "approved" and "Approval decision" in final["report_markdown"]


def test_block_merge_skips_the_approval_gate(specs):
    runner = FakeRunner({"security-reviewer": [reviewer_finding(severity="critical", category="security")]})
    result = invoke(make_graph(specs, runner, FakeGit(CS_HUNKS)), START)
    assert "__interrupt__" not in result and result["verdict"] == "BLOCK_MERGE" and result["security_block"]


def test_branch_switch_by_a_reviewer_is_restored_and_architecture_still_runs(specs):
    git = FakeGit(CS_HUNKS, ref="feature")
    runner = FakeRunner(on_run=lambda name: setattr(git, "ref", "main") if name == "backend-reviewer" else None)
    result = invoke(make_graph(specs, runner, git), START)
    assert git.checkouts == ["feature"] and result["warnings"]
    assert runner.calls.count("architecture-reviewer") == 1


def test_findings_outside_the_diff_are_dropped_before_synthesis(specs):
    runner = FakeRunner({"backend-reviewer": [reviewer_finding(file="Elsewhere.cs", severity="medium")]})
    result = invoke(make_graph(specs, runner, FakeGit(CS_HUNKS)), START)
    assert result["merged_findings"] == [] and len(result["dropped_findings"]) == 1


def test_accumulate_appends_and_reset_replaces():
    assert accumulate(None, [1]) == [1]
    assert accumulate([1], [2]) == [1, 2]
    assert accumulate([1, 2], [RESET]) == []
    assert accumulate([1, 2], [RESET, 3]) == [3]


def test_rerun_on_same_thread_does_not_accumulate_state(specs):
    runner = FakeRunner({"backend-reviewer": [reviewer_finding(severity="medium")]})
    graph = make_graph(specs, runner, FakeGit(CS_HUNKS))
    first = invoke(graph, START, "pr-53")
    second = invoke(graph, START, "pr-53")
    assert len(second["findings"]) == len(first["findings"]) == 1
    assert len(second["usage"]) == len(first["usage"])
    assert len(second["merged_findings"]) == 1


def test_stale_failure_does_not_change_next_run_verdict(specs):
    git, saver = FakeGit(CS_HUNKS), MemorySaver()
    failing = FakeRunner(failing={"security-reviewer"})
    assert invoke(make_graph(specs, failing, git, saver), START, "pr-53")["verdict"] == "BLOCK_MERGE"
    result = invoke(make_graph(specs, FakeRunner(), git, saver), START, "pr-53")
    assert result["verdict"] == "CLEAR" and result["failures"] == [] and result["incomplete_reviews"] == []


def test_fresh_run_after_pause_does_not_inherit_approval_state(specs):
    runner = FakeRunner({"backend-reviewer": [reviewer_finding(severity="high", summary="real")]})
    graph = make_graph(specs, runner, FakeGit(CS_HUNKS))
    assert invoke(graph, START, "pr-53")["__interrupt__"]
    final = invoke(graph, Command(resume="approved"), "pr-53")
    assert final["approval_decision"] == "approved"
    again = invoke(graph, START, "pr-53")
    assert again["__interrupt__"] and again.get("approval_decision", "") == ""


def test_resume_does_not_reset_run_state_and_reset_runs_once_per_fresh_invoke(specs):
    resets = []
    runner = FakeRunner({"backend-reviewer": [reviewer_finding(severity="high", summary="real")]})
    with patch("review_graph.graph.reset_run_node", side_effect=lambda s: resets.append(1) or fresh_run_state()):
        graph = make_graph(specs, runner, FakeGit(CS_HUNKS))
        paused = invoke(graph, START)
        counts = (len(paused["findings"]), len(paused["usage"]))
        final = invoke(graph, Command(resume="approved"))
    assert (len(final["findings"]), len(final["usage"])) == counts
    assert resets == [1]


class SimulatedProcessKill(BaseException):
    """Not an Exception, so the retry wrapper cannot swallow it: models the process dying."""


class KillingRunner(FakeRunner):
    def __init__(self, killed_agent, findings_by_agent=None):
        super().__init__(findings_by_agent)
        self.killed_agent = killed_agent

    async def run(self, spec, prompt, output_model, limits, cwd):
        if spec.name == self.killed_agent:
            await asyncio.sleep(0.05)
            raise SimulatedProcessKill()
        return await super().run(spec, prompt, output_model, limits, cwd)


def test_killed_mid_reviewer_step_resume_reruns_only_unfinished_reviewers(specs):
    saver = MemorySaver()
    findings = {"backend-reviewer": [reviewer_finding(severity="medium", summary="kept across the kill")]}
    killed = KillingRunner("security-reviewer", findings)
    with pytest.raises(SimulatedProcessKill):
        invoke(make_graph(specs, killed, FakeGit(CS_HUNKS), saver), START, "pr-9")
    assert {"backend-reviewer", "testing-reviewer"} <= set(killed.calls)

    resumed = FakeRunner()
    result = invoke(make_graph(specs, resumed, FakeGit(CS_HUNKS), saver), None, "pr-9")

    assert "security-reviewer" in resumed.calls
    assert "backend-reviewer" not in resumed.calls and "testing-reviewer" not in resumed.calls
    assert [f["summary"] for f in result["findings"]] == ["kept across the kill"]
    assert result["verdict"] == "CLEAR"


def test_real_graph_snapshots_report_what_find_resumable_relies_on(specs):
    async def scenario():
        saver = MemorySaver()
        config = {"configurable": {"thread_id": "pr-7"}}
        paused_graph = make_graph(
            specs, FakeRunner({"backend-reviewer": [reviewer_finding(severity="high")]}), FakeGit(CS_HUNKS), saver
        )
        await paused_graph.ainvoke(START, config)
        paused = await paused_graph.aget_state(config)

        await paused_graph.ainvoke(Command(resume="approved"), config)
        finished = await paused_graph.aget_state(config)

        crash_config = {"configurable": {"thread_id": "pr-8"}}
        crashed_graph = make_graph(specs, KillingRunner("security-reviewer"), FakeGit(CS_HUNKS), saver)
        with pytest.raises(SimulatedProcessKill):
            await crashed_graph.ainvoke(START, crash_config)
        crashed = await crashed_graph.aget_state(crash_config)
        unknown = await crashed_graph.aget_state({"configurable": {"thread_id": "never-ran"}})
        return paused, finished, crashed, unknown

    paused, finished, crashed, unknown = asyncio.run(scenario())
    assert paused.next == ("approval",) and paused.values["verdict"] == "REQUIRES_APPROVAL"
    assert finished.next == ()
    assert crashed.next and "approval" not in crashed.next
    assert unknown.next == ()


def test_checkpoint_survives_a_new_process_and_reviewers_are_not_rerun(specs, tmp_path):
    database = str(tmp_path / "checkpoints.sqlite")
    first_runner = FakeRunner({"backend-reviewer": [reviewer_finding(severity="high", summary="real")]})

    async def run_with(runner, graph_input):
        async with AsyncSqliteSaver.from_conn_string(database) as saver:
            graph = make_graph(specs, runner, FakeGit(CS_HUNKS), saver)
            return await graph.ainvoke(graph_input, {"configurable": {"thread_id": "pr-1"}})

    second_runner = FakeRunner()
    assert asyncio.run(run_with(first_runner, START))["__interrupt__"]
    final = asyncio.run(run_with(second_runner, Command(resume="rejected")))
    assert second_runner.calls == [] and final["approval_decision"] == "rejected"
