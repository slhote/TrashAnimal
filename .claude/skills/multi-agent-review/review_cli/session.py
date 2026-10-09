from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from review_graph.process_liveness import is_process_alive
from review_graph.resumable_threads import ResumableSearch, find_resumable, is_in_progress
from review_graph.thread_registry import ThreadRegistry

RECURSION_LIMIT = 60


@dataclass
class ReviewSession:
    """The compiled graph, the thread registry and the environment a review runs in."""

    graph: Any
    registry: ThreadRegistry
    interactive: bool
    read_line: Callable[[str], str] = input
    is_alive: Callable[[int, float | None], bool] = is_process_alive

    async def snapshot(self, thread_id: str):
        return await self.graph.aget_state({"configurable": {"thread_id": thread_id}})

    async def pending_nodes(self, thread_id: str) -> tuple:
        return (await self.snapshot(thread_id)).next

    async def find_open_reviews(self) -> ResumableSearch:
        return await find_resumable(self.registry, self.snapshot, self.is_alive)

    def is_owned_by_live_process(self, thread_id: str) -> bool:
        record = self.registry.get(thread_id)
        return record is not None and is_in_progress(record, self.is_alive)

    async def invoke(self, thread_id: str, graph_input):
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}
        return await self.graph.ainvoke(graph_input, config)
