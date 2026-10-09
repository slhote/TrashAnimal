from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from dataclasses import dataclass

from langgraph.types import Command

from .run_planning import RunPlan
from .session import ReviewSession


@dataclass(frozen=True)
class Completed:
    result: dict


@dataclass(frozen=True)
class Paused:
    thread_id: str
    payload: dict


def ask_for_decision(interrupt_payload: dict, interactive: bool, read_line: Callable[[str], str]) -> str | None:
    if not interactive:
        return None
    print("\nThis review REQUIRES APPROVAL before merge.", file=sys.stderr)
    for finding in interrupt_payload.get("high_findings", []):
        print(f"  - {finding}", file=sys.stderr)
    for agent in interrupt_payload.get("incomplete_reviews", []):
        print(f"  - review did not complete: {agent}", file=sys.stderr)
    try:
        answer = read_line("Approve? [y/N] ").strip().lower()
    except EOFError:
        return None

    return "approved" if answer in {"y", "yes"} else "rejected"


async def execute_run(session: ReviewSession, plan: RunPlan) -> Completed | Paused:
    """Drive the graph to the end, or to an approval gate nobody can answer right now.

    running_since stays set for the whole stretch this process owns the thread, including the approval
    prompt, so another terminal never sees a thread we are still handling as resumable.
    """
    thread_id = plan.thread_id
    session.registry.begin(thread_id, plan.registry_label, fresh=plan.fresh)
    try:
        result = await session.invoke(thread_id, plan.graph_input)
        while result.get("__interrupt__"):
            payload = result["__interrupt__"][0].value
            decision = await asyncio.to_thread(ask_for_decision, payload, session.interactive, session.read_line)
            if decision is None:
                return Paused(thread_id, payload)
            result = await session.invoke(thread_id, Command(resume=decision))
        session.registry.remove(thread_id)
        return Completed(result)
    finally:
        session.registry.mark_idle(thread_id)
