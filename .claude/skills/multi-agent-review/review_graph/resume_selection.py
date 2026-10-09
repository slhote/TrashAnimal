from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Literal, TextIO

from .resumable_threads import ResumableSearch, ResumableThread

NeedsInputReason = Literal["choose", "none_open", "none_match", "cancelled"]
ReviewChooser = Callable[[list[ResumableThread]], ResumableThread | None]


@dataclass(frozen=True)
class ResumeThread:
    thread_id: str


@dataclass(frozen=True)
class NeedsUserInput:
    reason: NeedsInputReason
    open_reviews: list[ResumableThread] = field(default_factory=list)
    running_elsewhere: int = 0


def reviews_for_scope(threads: list[ResumableThread], scope_args: dict) -> list[ResumableThread]:
    return [thread for thread in threads if thread.scope_args == scope_args]


def select_review(
    search: ResumableSearch,
    scope_args: dict | None,
    choose: ReviewChooser | None,
) -> ResumeThread | NeedsUserInput:
    """Decide which open review to resume, or why the user has to decide.

    `scope_args` is set only when the user named a scope with --resume (a filter). `choose` is set only when a
    person can be asked (interactive terminal). One filtered match is resumed without asking; an unfiltered
    list is never auto-picked.
    """
    candidates = reviews_for_scope(search.threads, scope_args) if scope_args else search.threads
    if not candidates:
        reason: NeedsInputReason = "none_match" if scope_args and search.threads else "none_open"
        return NeedsUserInput(reason, search.threads, search.running_elsewhere)
    if scope_args and len(candidates) == 1:
        return ResumeThread(candidates[0].thread_id)
    if choose is None:
        return NeedsUserInput("choose", candidates, search.running_elsewhere)
    picked = choose(candidates)
    if picked is None:
        return NeedsUserInput("cancelled", candidates, search.running_elsewhere)
    return ResumeThread(picked.thread_id)


def format_review(thread: ResumableThread) -> str:
    updated = datetime.fromtimestamp(thread.updated_at).strftime("%Y-%m-%d %H:%M")
    verdict = f", verdict {thread.verdict}" if thread.verdict else ""
    return f"{thread.thread_id}  [{thread.kind}]  scope {thread.scope_args or thread.scope_label}  updated {updated}{verdict}"


def describe_need(need: NeedsUserInput) -> str:
    running = f" ({need.running_elsewhere} running in another process)" if need.running_elsewhere else ""
    if need.reason == "none_open":
        return f"No open reviews to resume{running}."
    if need.reason == "none_match":
        return f"No open review matches that scope{running}. Other open reviews are listed in the output."
    if need.reason == "cancelled":
        return "Resume cancelled."
    return f"Several open reviews{running}: choose one and re-run with --resume --thread-id <id>."


def need_to_payload(need: NeedsUserInput) -> dict:
    return {
        "reason": need.reason,
        "running_elsewhere": need.running_elsewhere,
        "open_reviews": [asdict(thread) for thread in need.open_reviews],
    }


def make_terminal_chooser(read_line: Callable[[str], str], out: TextIO) -> ReviewChooser:
    def choose(threads: list[ResumableThread]) -> ResumableThread | None:
        print("Open reviews:", file=out)
        for number, thread in enumerate(threads, start=1):
            print(f"  {number}. {format_review(thread)}", file=out)
        while True:
            answer = read_line(f"Resume which review? [1-{len(threads)}, blank to cancel] ").strip().lower()
            if answer in {"", "c", "cancel", "q"}:
                return None
            if answer.isdigit() and 1 <= int(answer) <= len(threads):
                return threads[int(answer) - 1]
            print("Enter a number from the list, or press Enter to cancel.", file=out)

    return choose
