from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime

from langgraph.types import Command

from review_graph.resumable_threads import APPROVAL_NODE
from review_graph.resume_selection import (
    NeedsUserInput,
    describe_need,
    format_review,
    make_terminal_chooser,
    need_to_payload,
    select_review,
)

from .arguments import scope_was_given
from .exit_codes import EXIT_USAGE, EXIT_USER_INPUT_NEEDED
from .session import ReviewSession


class ExitRequested(Exception):
    def __init__(self, code: int):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RunPlan:
    thread_id: str
    graph_input: dict | Command | None
    registry_label: str
    fresh: bool


def report_need(need: NeedsUserInput, interactive: bool) -> ExitRequested:
    print(describe_need(need), file=sys.stderr)
    if interactive:
        for thread in need.open_reviews:
            print(f"  - {format_review(thread)}", file=sys.stderr)
    else:
        print(json.dumps(need_to_payload(need), indent=2))
    return ExitRequested(EXIT_USER_INPUT_NEEDED)


async def require_resumable_thread(thread_id: str, session: ReviewSession) -> None:
    """Refuse an explicit --thread-id that is finished, unknown, or being run by a live process."""
    reason = None
    if session.is_owned_by_live_process(thread_id):
        reason = "is being handled by a running process"
    elif not await session.pending_nodes(thread_id):
        reason = "has nothing to resume (it finished or does not exist)"
    if reason is None:
        return
    print(f"thread {thread_id} {reason}.", file=sys.stderr)
    for thread in (await session.find_open_reviews()).threads:
        print(f"  open: {format_review(thread)}", file=sys.stderr)
    raise ExitRequested(EXIT_USAGE)


async def pick_open_review(args: argparse.Namespace, scope_args: dict, session: ReviewSession) -> str:
    search = await session.find_open_reviews()
    chooser = make_terminal_chooser(session.read_line, sys.stderr) if session.interactive else None
    scope_filter = scope_args if scope_was_given(args) else None
    outcome = await asyncio.to_thread(select_review, search, scope_filter, chooser)
    if isinstance(outcome, NeedsUserInput):
        raise report_need(outcome, session.interactive)
    return outcome.thread_id


async def plan_resume(args: argparse.Namespace, scope_args: dict, session: ReviewSession) -> RunPlan:
    if args.thread_id:
        await require_resumable_thread(args.thread_id, session)
        thread_id = args.thread_id
    else:
        thread_id = await pick_open_review(args, scope_args, session)

    decision = args.decision
    if decision and APPROVAL_NODE not in await session.pending_nodes(thread_id):
        print(f"warning: thread {thread_id} is not waiting for approval; ignoring --decision", file=sys.stderr)
        decision = None
    record = session.registry.get(thread_id)
    graph_input = Command(resume=decision) if decision else None
    return RunPlan(thread_id, graph_input, record.scope_label if record else thread_id, fresh=False)


async def plan_fresh_run(args: argparse.Namespace, scope_args: dict, label: str, session: ReviewSession) -> RunPlan:
    thread_id = args.thread_id or f"{label}-{datetime.now():%Y%m%d%H%M%S}"
    if await session.pending_nodes(thread_id):
        print(
            f"warning: thread {thread_id} has an unfinished review; starting over discards it "
            f"(use --resume --thread-id {thread_id} to continue it instead)",
            file=sys.stderr,
        )
    return RunPlan(thread_id, {"scope_args": scope_args}, label, fresh=True)


async def plan_run(args: argparse.Namespace, scope_args: dict, label: str, session: ReviewSession) -> RunPlan:
    if args.resume:
        return await plan_resume(args, scope_args, session)
    return await plan_fresh_run(args, scope_args, label, session)
