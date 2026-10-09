from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
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
    updated_at: float
    verdict: str | None


def is_in_progress(record: ThreadRecord, is_alive: Callable[[int, float | None], bool]) -> bool:
    return record.running_since is not None and record.pid is not None and is_alive(record.pid, record.running_since)


async def find_resumable(
    registry: ThreadRegistry,
    get_state: Callable[[str], Awaitable],
    is_alive: Callable[[int, float | None], bool] = is_process_alive,
) -> list[ResumableThread]:
    """Threads with work left that no live process is handling, newest first.

    Rows a live process owns are skipped before any checkpoint is read. The checkpoint decides the rest:
    nothing left to run means finished (or never started); a pending approval node means waiting on a human;
    anything else was interrupted by a crash or exception.
    """
    resumable: list[ResumableThread] = []
    for record in registry.list_all():
        if is_in_progress(record, is_alive):
            continue
        snapshot = await get_state(record.thread_id)
        if not snapshot.next:
            continue
        kind: ResumableKind = "PAUSED_APPROVAL" if APPROVAL_NODE in snapshot.next else "UNFINISHED"
        resumable.append(
            ResumableThread(
                thread_id=record.thread_id,
                kind=kind,
                scope_label=record.scope_label,
                updated_at=record.updated_at,
                verdict=(snapshot.values or {}).get("verdict"),
            )
        )
    return resumable
