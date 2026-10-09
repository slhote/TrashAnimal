from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from review_graph.agents_loader import load_agent
from review_graph.git_client import GitClient
from review_graph.graph import GraphDependencies, build_graph
from review_graph.runner import RunLimits, SdkAgentRunner
from review_graph.state import ARCHITECTURE_AGENT, PHASE_ONE_AGENTS
from review_graph.thread_registry import ThreadRegistry

EXIT_CLEAR, EXIT_REJECTED, EXIT_BLOCKED, EXIT_PAUSED = 0, 1, 2, 3


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-agent code review orchestrated with LangGraph")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--pr", type=int, help="review a GitHub PR by number")
    scope.add_argument("--staged", action="store_true", help="review staged changes")
    scope.add_argument("--since", metavar="REF", help="review changes since a git ref")
    scope.add_argument("--paths", nargs="+", metavar="PATH", help="review these files or folders in full")
    parser.add_argument("--resume", action="store_true", help="continue an existing thread (needs --thread-id)")
    parser.add_argument("--thread-id", help="checkpoint thread id; printed at the start of every run")
    parser.add_argument("--decision", choices=["approved", "rejected"], help="answer a paused approval gate")
    parser.add_argument("--json-out", metavar="FILE", help="also write the structured report here")
    parser.add_argument("--agents-dir", help="folder with agent .md files (default: <repo>/.claude/agents)")
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--max-budget-usd", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=900.0, help="seconds per reviewer attempt")
    parser.add_argument("--attempts", type=int, default=2)
    return parser.parse_args(argv)


def scope_from_arguments(args: argparse.Namespace) -> tuple[dict, str]:
    if args.pr is not None:
        return {"kind": "pr", "value": args.pr}, f"pr-{args.pr}"
    if args.staged:
        return {"kind": "staged"}, "staged"
    if args.since:
        return {"kind": "since", "value": args.since}, f"since-{args.since}"
    if args.paths:
        return {"kind": "paths", "value": args.paths}, "paths"
    return {"kind": "default"}, "branch"


def exit_code_for(result: dict) -> int:
    if result.get("verdict") == "BLOCK_MERGE":
        return EXIT_BLOCKED
    if result.get("verdict") == "REQUIRES_APPROVAL" and result.get("approval_decision") != "approved":
        return EXIT_REJECTED
    return EXIT_CLEAR


def ask_for_decision(interrupt_payload: dict) -> str | None:
    if not sys.stdin.isatty():
        return None
    print("\nThis review REQUIRES APPROVAL before merge.", file=sys.stderr)
    for finding in interrupt_payload.get("high_findings", []):
        print(f"  - {finding}", file=sys.stderr)
    for agent in interrupt_payload.get("incomplete_reviews", []):
        print(f"  - review did not complete: {agent}", file=sys.stderr)
    answer = input("Approve? [y/N] ").strip().lower()
    return "approved" if answer in {"y", "yes"} else "rejected"


async def run_review(args: argparse.Namespace) -> int:
    git = GitClient()
    repo_root = Path(git.repo_root)
    agents_dir = Path(args.agents_dir) if args.agents_dir else repo_root / ".claude" / "agents"
    specs = {name: load_agent(agents_dir, name) for name in [*PHASE_ONE_AGENTS, ARCHITECTURE_AGENT]}
    limits = RunLimits(args.max_turns, args.max_budget_usd, args.timeout, args.attempts)
    dependencies = GraphDependencies(runner=SdkAgentRunner(), git=git, specs=specs, reviewer_limits=limits)

    scope_args, label = scope_from_arguments(args)
    if args.resume and not args.thread_id:
        print("--resume needs --thread-id", file=sys.stderr)
        return 64
    thread_id = args.thread_id or f"{label}-{datetime.now():%Y%m%d%H%M%S}"
    print(f"thread id: {thread_id}", file=sys.stderr)

    checkpoint_path = repo_root / ".claude" / "review-checkpoints.sqlite"
    registry = ThreadRegistry(checkpoint_path)
    async with AsyncSqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
        graph = build_graph(dependencies, checkpointer)
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}

        if args.resume:
            graph_input = Command(resume=args.decision) if args.decision else None
        else:
            if (await graph.aget_state(config)).next:
                print(
                    f"warning: thread {thread_id} has an unfinished review; starting over discards it "
                    f"(use --resume --thread-id {thread_id} to continue it instead)",
                    file=sys.stderr,
                )
            graph_input = {"scope_args": scope_args}

        # running_since stays set for the whole stretch this process owns the thread, including the
        # approval prompt, so another terminal never sees a thread we are still handling as resumable.
        registry.begin(thread_id, label, fresh=not args.resume)
        try:
            result = await graph.ainvoke(graph_input, config)

            while result.get("__interrupt__"):
                payload = result["__interrupt__"][0].value
                decision = await asyncio.to_thread(ask_for_decision, payload)
                if decision is None:
                    print(
                        "Paused: approval needed. Re-run with: "
                        f"--resume --thread-id {thread_id} --decision approved|rejected",
                        file=sys.stderr,
                    )
                    print(json.dumps({"paused": True, "thread_id": thread_id, **payload}, indent=2))
                    return EXIT_PAUSED

                result = await graph.ainvoke(Command(resume=decision), config)
            registry.remove(thread_id)
        finally:
            registry.mark_idle(thread_id)

    print(result["report_markdown"])
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result["report_json"], indent=2), encoding="utf-8")
    return exit_code_for(result)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(run_review(parse_arguments())))


if __name__ == "__main__":
    main()
