from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from review_cli.arguments import parse_arguments, scope_from_arguments, validate_arguments
from review_cli.console import stdin_is_console
from review_cli.exit_codes import EXIT_PAUSED, EXIT_USAGE, exit_code_for
from review_cli.run_execution import Completed, Paused, execute_run
from review_cli.run_planning import ExitRequested, plan_run
from review_cli.session import ReviewSession
from review_graph.agents_loader import load_agent
from review_graph.git_client import GitClient
from review_graph.graph import GraphDependencies, build_graph
from review_graph.runner import RunLimits, SdkAgentRunner
from review_graph.state import ARCHITECTURE_AGENT, PHASE_ONE_AGENTS
from review_graph.thread_registry import ThreadRegistry


def build_dependencies(args, git: GitClient, repo_root: Path) -> GraphDependencies:
    agents_dir = Path(args.agents_dir) if args.agents_dir else repo_root / ".claude" / "agents"
    specs = {name: load_agent(agents_dir, name) for name in [*PHASE_ONE_AGENTS, ARCHITECTURE_AGENT]}
    limits = RunLimits(args.max_turns, args.max_budget_usd, args.timeout, args.attempts)
    return GraphDependencies(runner=SdkAgentRunner(), git=git, specs=specs, reviewer_limits=limits)


def report_pause(paused: Paused) -> int:
    print(
        "Paused: approval needed. Re-run with: "
        f"--resume --thread-id {paused.thread_id} --decision approved|rejected",
        file=sys.stderr,
    )
    print(json.dumps({"paused": True, "thread_id": paused.thread_id, **paused.payload}, indent=2))
    return EXIT_PAUSED


def report_completion(completed: Completed, json_out: str | None) -> int:
    print(completed.result["report_markdown"])
    if json_out:
        Path(json_out).write_text(json.dumps(completed.result["report_json"], indent=2), encoding="utf-8")
    return exit_code_for(completed.result)


async def run_review(args) -> int:
    problem = validate_arguments(args)
    if problem:
        print(problem, file=sys.stderr)
        return EXIT_USAGE

    git = GitClient()
    repo_root = Path(git.repo_root)
    dependencies = build_dependencies(args, git, repo_root)
    scope_args, label = scope_from_arguments(args)
    checkpoint_path = repo_root / ".claude" / "review-checkpoints.sqlite"

    async with AsyncSqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
        session = ReviewSession(
            graph=build_graph(dependencies, checkpointer),
            registry=ThreadRegistry(checkpoint_path),
            interactive=stdin_is_console(),
        )
        try:
            plan = await plan_run(args, scope_args, label, session)
        except ExitRequested as exit_request:
            return exit_request.code

        print(f"thread id: {plan.thread_id}", file=sys.stderr)
        outcome = await execute_run(session, plan)

    if isinstance(outcome, Paused):
        return report_pause(outcome)
    return report_completion(outcome, args.json_out)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(run_review(parse_arguments())))


if __name__ == "__main__":
    main()
