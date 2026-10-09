from __future__ import annotations

from ..state import ReviewState, fresh_run_state


def reset_run_node(state: ReviewState) -> dict:
    return fresh_run_state()
