from __future__ import annotations

from ..state import ReviewState
from .route import normalize_path


def make_scope_node(git):
    def scope_node(state: ReviewState) -> dict:
        result = git.scope_diff(state.get("scope_args", {"kind": "default"}))
        hunks = {normalize_path(path): ranges for path, ranges in result.hunks.items()}
        return {
            "repo_root": git.repo_root,
            "diff_hint": result.diff_hint,
            "changed_files": sorted(hunks),
            "changed_hunks": hunks,
        }

    return scope_node
