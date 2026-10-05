from __future__ import annotations

from dataclasses import dataclass, field

from langgraph.graph import END, START, StateGraph

from .agents_loader import AgentSpec
from .nodes.approval import approval_node
from .nodes.architecture import make_architecture_node
from .nodes.branch_guard import make_branch_guard_nodes
from .nodes.report import report_node
from .nodes.reviewer import make_reviewer_node
from .nodes.route import fan_out_to_reviewers, route_node
from .nodes.scope import make_scope_node
from .nodes.synthesize import synthesize_node
from .nodes.verify_findings import make_verify_findings_node
from .runner import AgentRunner, RunLimits
from .state import ReviewState


@dataclass
class GraphDependencies:
    runner: AgentRunner
    git: object
    specs: dict[str, AgentSpec]
    reviewer_limits: RunLimits = field(default_factory=RunLimits)
    verifier_limits: RunLimits = field(default_factory=lambda: RunLimits(max_turns=10, max_budget_usd=0.5))


def architecture_is_pending(state: ReviewState) -> bool:
    return bool(state.get("run_architecture")) and not state.get("architecture_done")


def next_after_first_check(state: ReviewState) -> str:
    if state.get("branch_changed"):
        return "restore_branch"
    return "architecture" if architecture_is_pending(state) else "verify_findings"


def next_after_second_check(state: ReviewState) -> str:
    return "restore_branch" if state.get("branch_changed") else "verify_findings"


def next_after_restore(state: ReviewState) -> str:
    return "architecture" if architecture_is_pending(state) else "verify_findings"


def next_after_synthesis(state: ReviewState) -> str:
    return "approval" if state.get("verdict") == "REQUIRES_APPROVAL" else "report"


def build_graph(deps: GraphDependencies, checkpointer=None):
    snapshot_branch, verify_branch, restore_branch = make_branch_guard_nodes(deps.git)

    graph = StateGraph(ReviewState)
    graph.add_node("snapshot_branch", snapshot_branch)
    graph.add_node("scope", make_scope_node(deps.git))
    graph.add_node("route", route_node)
    graph.add_node("reviewer", make_reviewer_node(deps.runner, deps.specs, deps.reviewer_limits))
    graph.add_node("verify_branch_1", verify_branch)
    graph.add_node("architecture", make_architecture_node(deps.runner, deps.specs, deps.reviewer_limits))
    graph.add_node("verify_branch_2", verify_branch)
    graph.add_node("restore_branch", restore_branch)
    graph.add_node("verify_findings", make_verify_findings_node(deps.runner, deps.verifier_limits))
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("approval", approval_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "snapshot_branch")
    graph.add_edge("snapshot_branch", "scope")
    graph.add_edge("scope", "route")
    graph.add_conditional_edges("route", fan_out_to_reviewers, ["reviewer", "report"])
    graph.add_edge("reviewer", "verify_branch_1")
    graph.add_conditional_edges(
        "verify_branch_1", next_after_first_check, ["restore_branch", "architecture", "verify_findings"]
    )
    graph.add_edge("architecture", "verify_branch_2")
    graph.add_conditional_edges("verify_branch_2", next_after_second_check, ["restore_branch", "verify_findings"])
    graph.add_conditional_edges("restore_branch", next_after_restore, ["architecture", "verify_findings"])
    graph.add_edge("verify_findings", "synthesize")
    graph.add_conditional_edges("synthesize", next_after_synthesis, ["approval", "report"])
    graph.add_edge("approval", "report")
    graph.add_edge("report", END)

    return graph.compile(checkpointer=checkpointer)
