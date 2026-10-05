from __future__ import annotations

from pathlib import PurePosixPath

from langgraph.types import Send

from ..state import PHASE_ONE_AGENTS, ReviewState

DOC_EXTENSIONS = {".md", ".mdx", ".txt"}
FRONTEND_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css"}
ARCHITECTURE_EXTENSIONS = {".cs", ".ts", ".tsx"}
BACKEND_ROOTS = {"TrashAnimal", "TrashAnimal.Api"}
FRONTEND_ROOT = "TrashAnimal.Web"


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _extension(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def _top_level_folder(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if parts else ""


def is_docs_only(changed_files: list[str]) -> bool:
    return all(_extension(path) in DOC_EXTENSIONS for path in changed_files)


def bucket_files(changed_files: list[str]) -> dict[str, list[str]]:
    files = [normalize_path(path) for path in changed_files]
    if not files or is_docs_only(files):
        return {}

    frontend = [
        f for f in files if _top_level_folder(f) == FRONTEND_ROOT and _extension(f) in FRONTEND_EXTENSIONS
    ]
    backend = [f for f in files if _top_level_folder(f) in BACKEND_ROOTS and _extension(f) == ".cs"]

    buckets = {
        "frontend-reviewer": frontend,
        "backend-reviewer": backend,
        "security-reviewer": files,
        "testing-reviewer": files,
    }
    return {agent: agent_files for agent, agent_files in buckets.items() if agent_files}


def needs_architecture_review(changed_files: list[str]) -> bool:
    return any(_extension(path) in ARCHITECTURE_EXTENSIONS for path in changed_files)


def route_node(state: ReviewState) -> dict:
    changed_files = [normalize_path(path) for path in state.get("changed_files", [])]
    routing = bucket_files(changed_files)
    return {
        "docs_only": not routing,
        "routing": routing,
        "run_architecture": bool(routing) and needs_architecture_review(changed_files),
        "architecture_done": False,
    }


def fan_out_to_reviewers(state: ReviewState):
    routing = state.get("routing", {})
    if not routing:
        return "report"
    ordered_agents = [agent for agent in PHASE_ONE_AGENTS if agent in routing]
    return [
        Send(
            "reviewer",
            {
                "agent": agent,
                "files": routing[agent],
                "diff_hint": state.get("diff_hint", ""),
                "repo_root": state.get("repo_root", "."),
            },
        )
        for agent in ordered_agents
    ]
