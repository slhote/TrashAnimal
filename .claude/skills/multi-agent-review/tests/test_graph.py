import asyncio

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from conftest import FakeGit, FakeRunner, reviewer_finding
from review_graph.graph import GraphDependencies, build_graph
from review_graph.runner import RunLimits

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
