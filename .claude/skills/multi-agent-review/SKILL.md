---
name: multi-agent-review
description: Runs a full multi-specialist code review of changed TrashAnimal files by executing the LangGraph pipeline in this folder (frontend, backend, security, testing, then architecture reviewers; finding verification; rule-based synthesis; human approval gate). Use when the user asks for a full/comprehensive review, a multi-agent review, or invokes /multi-agent-review, as opposed to a single ad hoc agent check.
---

# Multi-Agent Review

The orchestration lives in code (`review.py` + `review_graph/`), not in this file. Routing, the branch-safety checks, finding verification, severity synthesis and the approval gate are all deterministic Python; the reviewers are the agents in `.claude/agents/*.md`, run through the Claude Agent SDK. Your job here is to run it and relay the result.

## 1. Run it

From the repo root:

```bash
.claude/skills/multi-agent-review/.venv/Scripts/python .claude/skills/multi-agent-review/review.py [scope]
```

Scope (pick from what the user asked; default is `main...HEAD` plus uncommitted/untracked files):

| User asked for | Flag |
|---|---|
| A PR | `--pr <number>` |
| Staged changes | `--staged` |
| Changes since a ref | `--since <ref>` |
| Specific files/folders | `--paths <path> [<path> ...]` |
| Continue / resume an earlier review | `--resume` (see "Resuming a review" below) |

Optional: `--json-out <file>` for the structured report, `--max-budget-usd`, `--max-turns`, `--timeout`, `--attempts` to tune per-reviewer limits.

The run prints `thread id: ...` on stderr. Keep it; it is the checkpoint key. Passing a stable `--thread-id` (e.g. `pr-53`) to a new run (without `--resume`) starts clean: findings, failures, usage, warnings and verdict from earlier runs on that thread are discarded. `--resume` continues the paused run instead.

If the `.venv` folder is missing, set it up once (Python 3.14+):

```bash
cd .claude/skills/multi-agent-review
python -m venv .venv
.venv/Scripts/python -m pip install langgraph langgraph-checkpoint-sqlite claude-agent-sdk pydantic pytest
```

## 2. Handle the exit code

| Exit | Meaning | What to do |
|---|---|---|
| 0 | CLEAR, or REQUIRES APPROVAL that was approved | Relay the report |
| 2 | BLOCK MERGE | Relay the report; lead with the block verdict (and the security gate line if present) |
| 1 | REQUIRES APPROVAL and rejected | Relay the report |
| 3 | Paused at the approval gate (no interactive terminal) | Show the user the high findings from the JSON on stdout, ask whether to approve, then re-run: `review.py --resume --thread-id <id> --decision approved` (or `rejected`) |
| 4 | `--resume` needs the user to decide (JSON on stdout) | See "Resuming a review"; ask the user, never start a new review on your own |
| 64 | Bad arguments, or the `--thread-id` cannot be resumed | Relay the message; open reviews are listed on stderr |

## Resuming a review

If the run crashes or is interrupted, resume it without re-running finished reviewers. "Continue the review for pr-53" does **not** mean `--thread-id pr-53`: thread ids are normally `<scope>-<timestamp>`, and a scope can have several reviews. Use what you know:

- You have the exact id (printed as `thread id: ...` earlier in this conversation, or in the exit-3 JSON): `review.py --resume --thread-id <id>` (add `--decision approved|rejected` only for a review waiting at the approval gate).
- You only know the scope: pass the same scope flag as a filter, e.g. `review.py --resume --pr 53`. One open review for that scope is resumed automatically (the chosen thread id is printed).
- You know neither: `review.py --resume` lists the open reviews.

On exit 4 the stdout JSON has `reason` and `open_reviews` (thread id, `kind` PAUSED_APPROVAL or UNFINISHED, scope, last update, verdict):

| `reason` | Meaning | What to tell the user |
|---|---|---|
| `choose` | several open reviews | Show them, ask which to resume, re-run with `--resume --thread-id <id>` |
| `none_match` | nothing open for that scope | Say so, show any other open reviews, and ask what they want to do |
| `none_open` | nothing open at all | Say so and ask what they want to do |

When the user wants a fresh review instead, they must say which scope; run the normal scoped command then. Do not pick a scope for them.

## 3. Report

Relay the markdown report: verdict first, then findings grouped by severity with the agents that raised each, then any reviews that did not complete and cost. Do not paste raw agent output; the report is already synthesized. If the calling context expects structured findings (for example `/code-review`), use `ReportFindings` with the `--json-out` file.

## Notes

- Reviewers run read-only: Edit/Write and mutating git commands are disallowed, and Bash is narrowed to `git diff/show/log/status/rev-parse` and `gh pr diff/view`. The pipeline also checks the checked-out branch after each phase and restores it if it changed.
- A reviewer that fails, times out or exceeds its budget is reported as an incomplete review; a failed security review blocks the merge.
- Tests: `.claude/skills/multi-agent-review/.venv/Scripts/python -m pytest` from this folder.
- The previous prose-driven procedure is kept in `legacy-skill-procedure.md` as a fallback if the Python pipeline cannot run.
