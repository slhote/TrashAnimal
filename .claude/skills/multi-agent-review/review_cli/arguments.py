from __future__ import annotations

import argparse


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-agent code review orchestrated with LangGraph")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--pr", type=int, help="review a GitHub PR by number")
    scope.add_argument("--staged", action="store_true", help="review staged changes")
    scope.add_argument("--since", metavar="REF", help="review changes since a git ref")
    scope.add_argument("--paths", nargs="+", metavar="PATH", help="review these files or folders in full")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="continue an open review: give --thread-id, a scope flag to filter by, or neither to list open reviews",
    )
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


def scope_was_given(args: argparse.Namespace) -> bool:
    return args.pr is not None or args.staged or bool(args.since) or bool(args.paths)


def validate_arguments(args: argparse.Namespace) -> str | None:
    if args.decision and not args.resume:
        return "--decision only applies together with --resume"
    if args.resume and args.thread_id and scope_was_given(args):
        return "--resume --thread-id continues a saved review; scope flags would be ignored, so drop them"
    return None
