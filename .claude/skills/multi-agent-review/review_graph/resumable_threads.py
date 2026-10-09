from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal

from .process_liveness import is_process_alive
from .thread_registry import ThreadRecord, ThreadRegistry

APPROVAL_NODE = "approval"
ResumableKind = Literal["PAUSED_APPROVAL", "UNFINISHED"]


@dataclass(frozen=True)
class ResumableThread:
    thread_id: str
    kind: ResumableKind
    scope_label: str
    scope_args: dict
    updated_at: float
    verdict: str | None


@dataclass(frozen=True)
class ResumableSearch:
    threads: list[ResumableThread] = field(default_factory=list)
    running_elsewhere: int = 0


def is_in_progress(record: ThreadRecord, is_alive: Callable[[int, float | None], bool]) -> bool:
    return record.running_since is not None and record.pid is not None and is_alive(record.pid, record.running_since)


def kind_for_pending_nodes(pending_nodes: tuple) -> ResumableKind:
    return "PAUSED_APPROVAL" if APPROVAL_NODE in pending_nodes else "UNFINISHED"


async def find_resumable(
    registry: ThreadRegistry,
    get_state: Callable[[str], Awaitable],
    is_alive: Callable[[int, float | None], bool] = is_process_alive,
) -> ResumableSearch:
    """Threads with work left that no live process is handling, newest first.

    Rows a live process owns are counted, not read. The checkpoint decides the rest: nothing left to run
    means finished (or never started); a pending approval node means waiting on a human; anything else was
    interrupted by a crash or exception.
    """
    resumable: list[ResumableThread] = []
    running_elsewhere = 0
    for record in registry.list_all():
        if is_in_progress(record, is_alive):
            running_elsewhere += 1
            continue
        snapshot = await get_state(record.thread_id)
        if not snapshot.next:
            continue
        values = snapshot.values or {}
        resumable.append(
            ResumableThread(
                thread_id=record.thread_id,
                kind=kind_for_pending_nodes(snapshot.next),
                scope_label=record.scope_label,
                scope_args=values.get("scope_args") or {},
                updated_at=record.updated_at,
                verdict=values.get("verdict"),
            )
        )
    return ResumableSearch(resumable, running_elsewhere)
