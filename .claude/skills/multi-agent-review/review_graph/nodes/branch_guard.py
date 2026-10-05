from __future__ import annotations

from ..state import ReviewState


def make_branch_guard_nodes(git):
    def snapshot_branch(state: ReviewState) -> dict:
        return {"original_ref": git.current_ref(), "branch_changed": False}

    def verify_branch(state: ReviewState) -> dict:
        current = git.current_ref()
        return {"current_ref": current, "branch_changed": current != state["original_ref"]}

    def restore_branch(state: ReviewState) -> dict:
        original, current = state["original_ref"], state.get("current_ref", "unknown")
        git.checkout(original)
        return {
            "branch_changed": False,
            "warnings": [f"Checked-out ref changed during review ({original} -> {current}); restored {original}."],
        }

    return snapshot_branch, verify_branch, restore_branch
