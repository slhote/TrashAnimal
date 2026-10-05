---
name: multi-agent-review
description: Runs a full multi-specialist code review of changed TrashAnimal files using the frontend-reviewer, backend-reviewer, security-reviewer, testing-reviewer, and architecture-reviewer subagents — parallel specialist pass, then a sequential architecture pass with full context, then a rule-based synthesis into one prioritized report. Use when the user asks for a full/comprehensive review, a multi-agent review, or invokes /multi-agent-review, as opposed to a single ad hoc agent check.
---

# Multi-Agent Review

Orchestrates the five subagents in `.claude/agents/` (`frontend-reviewer`, `backend-reviewer`, `security-reviewer`, `testing-reviewer`, `architecture-reviewer`) into one review pass with consistent conflict resolution. Follow these steps in order.

## 1. Determine scope

Default: `git diff main...HEAD` plus untracked files (`git status --porcelain`) to get the full set of changed files.

If the user gave an argument (a PR number, "staged", "since <ref>", or a file/folder path), use that instead:
- A PR number → `gh pr diff <number>`
- "staged" → `git diff --staged`
- "since <ref>" → `git diff <ref>...HEAD`
- A path → treat as an explicit file list, skip the diff entirely

## 2. Route: select which agents apply

Bucket the changed files and skip any agent with nothing to review:

| Agent | Triggers on |
|---|---|
| `frontend-reviewer` | `TrashAnimal.Web/**/*.{ts,tsx,js,jsx,css}` |
| `backend-reviewer` | `TrashAnimal/**/*.cs`, `TrashAnimal.Api/**/*.cs` (excluding test projects) |
| `security-reviewer` | Any changed file, always included if the change set is non-empty |
| `testing-reviewer` | Any changed file in a non-test project (assesses coverage), or any changed file inside `TrashAnimal.Tests`/`TrashAnimal.Api.Tests`/web test files (assesses quality) |
| `architecture-reviewer` | Any changed `.cs`/`.ts`/`.tsx` file — always runs sequentially if any code (not docs-only) changed |

If the change set is docs-only (`*.md`, no code), skip the whole review and say so — don't spin up agents for nothing.

## 3. Safety: verify reviewers didn't mutate git state

Each of the five agent definitions in `.claude/agents/` already instructs itself not to run branch-mutating commands (`git checkout`, `git reset`, `git stash`, `git clean`, etc.) — that's the source of truth, don't re-inject it here. What this skill adds is an independent *check*, since an agent could still deviate from its own instructions and Bash is in its tool list:

Before starting step 4, capture the current branch: `git branch --show-current`. After each phase (parallel and sequential) completes, run it again and confirm it's unchanged. If it changed, stop, tell the user immediately, and restore the original branch with `git checkout <original-branch>` (checkout alone doesn't discard commits, so this is safe) before continuing or reporting results.

## 4. Parallel phase

In a single message, call the `Agent` tool once per selected agent from {`frontend-reviewer`, `backend-reviewer`, `security-reviewer`, `testing-reviewer`} (skip any not selected in step 2), each with `run_in_background: false` so results return before you continue. Give each agent:
- The list of changed files relevant to its scope (not the full diff — let it `Read`/`Grep` the files itself for full context)
- Instruction to report findings as: file, line, severity (critical/high/medium/low), one-sentence summary, suggested fix

Wait for all of them to return before moving on, then run the branch-unchanged check from step 3.

## 5. Sequential phase

If `architecture-reviewer` is selected, call it once, `run_in_background: false`, and include in its prompt:
- The same changed-file list
- A condensed summary of every finding from step 4 (agent name, file, severity, one-line summary) so it can reason with full context, per its own instructions to build on rather than repeat them

Then run the branch-unchanged check from step 3 again.

## 6. Synthesize

Collect all findings from steps 4 and 5 and apply these rules, in order:

**Rule 1 — Agreement escalates severity.** If two or more agents flag the same file+line (or same file+issue-type when line-level doesn't align) as related findings, bump the combined severity one level (e.g. two MEDIUMs → HIGH). Merge them into one finding attributed to both agents rather than listing duplicates.

**Rule 2 — Security always wins.** Any CRITICAL from `security-reviewer` keeps CRITICAL severity regardless of what other agents said about the same issue. Never downgrade a security CRITICAL during synthesis.

**Rule 3 — Cross-agent context.** When `backend-reviewer` and `frontend-reviewer` both touch the same concern (e.g. an API shape change), prefer the interpretation that accounts for both sides rather than treating them as independent — note the connection in the synthesized finding rather than reporting them separately.

**Rule 4 — Priority matrix.** When agents disagree on severity for the *same* underlying issue, resolve using whichever agent has the higher weight for that issue type:

| Issue type | Frontend | Backend | Security | Testing | Architecture |
|---|---|---|---|---|---|
| Security | 10 | 10 | 100 | 10 | 20 |
| Performance | 30 | 50 | 5 | 10 | 30 |
| Accessibility | 100 | 5 | 20 | 30 | 10 |
| Maintainability | 20 | 20 | 10 | 20 | 100 |
| Testing | 10 | 10 | 10 | 100 | 20 |

**Rule 5 — Escalation triggers.** After the above:
- Any CRITICAL from `security-reviewer` → **BLOCK MERGE**, call it out explicitly at the top of the report
- Any other CRITICAL → **BLOCK MERGE**
- Any HIGH → **REQUIRES APPROVAL** before merge
- MEDIUM/LOW → include in report, no gate

## 7. Report

Produce one prioritized report: escalation verdict first (block / requires approval / clear), then findings grouped by severity (not by agent), each showing which agent(s) raised it. If the calling context expects structured findings (e.g. this was invoked as part of `/code-review`), use `ReportFindings`; otherwise a markdown summary is fine. Don't re-print each agent's raw output verbatim — the value of this skill is the synthesis, not a transcript dump.
