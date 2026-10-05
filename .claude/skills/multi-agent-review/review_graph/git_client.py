from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .diff_parser import LineRanges, parse_diff_hunks

IGNORED_FOLDERS = {".git", "node_modules", ".venv", "__pycache__", "bin", "obj", "dist"}


class GitError(RuntimeError):
    pass


@dataclass
class ScopeResult:
    hunks: dict[str, LineRanges | None]
    diff_hint: str


class GitClient:
    def __init__(self, repo_root: str | None = None):
        self.repo_root = repo_root or self._run("rev-parse", "--show-toplevel", cwd=None).strip()

    def _run(self, *args: str, cwd: str | None = "") -> str:
        working_directory = self.repo_root if cwd == "" else cwd
        completed = subprocess.run(
            list(args) if args[0] == "gh" else ["git", *args],
            cwd=working_directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise GitError(f"{' '.join(args)} failed: {completed.stderr.strip()}")
        return completed.stdout

    def current_ref(self) -> str:
        branch = self._run("branch", "--show-current").strip()
        return branch or self._run("rev-parse", "HEAD").strip()

    def checkout(self, ref: str) -> None:
        self._run("checkout", ref)

    def scope_diff(self, scope_args: dict) -> ScopeResult:
        kind = scope_args.get("kind", "default")
        value = scope_args.get("value")
        if kind == "pr":
            diff = self._run("gh", "pr", "diff", str(value))
            return ScopeResult(dict(parse_diff_hunks(diff)), f"gh pr diff {value}")
        if kind == "staged":
            diff = self._run("diff", "--staged", "-U0")
            return ScopeResult(dict(parse_diff_hunks(diff)), "git diff --staged")
        if kind == "since":
            diff = self._run("diff", "-U0", f"{value}...HEAD")
            return ScopeResult(dict(parse_diff_hunks(diff)), f"git diff {value}...HEAD")
        if kind == "paths":
            return ScopeResult(self._expand_paths(value or []), "no diff: review the listed files in full")
        diff = self._run("diff", "-U0", "main...HEAD")
        hunks: dict[str, LineRanges | None] = dict(parse_diff_hunks(diff))
        for path in self._uncommitted_paths():
            hunks[path] = None
        return ScopeResult(hunks, "git diff main...HEAD (plus uncommitted and untracked files, review those in full)")

    def _uncommitted_paths(self) -> list[str]:
        paths: list[str] = []
        for line in self._run("status", "--porcelain", "--untracked-files=all").splitlines():
            status, entry = line[:2], line[3:]
            if "D" in status:
                continue
            paths.append(entry.split(" -> ")[-1].strip().strip('"'))
        return paths

    def _expand_paths(self, requested: list[str]) -> dict[str, LineRanges | None]:
        root = Path(self.repo_root)
        expanded: dict[str, LineRanges | None] = {}
        for requested_path in requested:
            candidate = Path(requested_path)
            absolute = candidate if candidate.is_absolute() else root / candidate
            files = [absolute] if absolute.is_file() else [
                f for f in absolute.rglob("*") if f.is_file() and not IGNORED_FOLDERS & set(f.parts)
            ]
            for file in files:
                expanded[file.resolve().relative_to(root.resolve()).as_posix()] = None
        return expanded
