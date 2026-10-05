from __future__ import annotations

from ..agent_execution import execute_with_retries
from ..agents_loader import AgentSpec
from ..runner import AgentRunner, RunLimits
from ..state import Finding, ReviewerOutput
from .route import normalize_path

FINDING_INSTRUCTIONS = (
    "Report each finding with: file (repo-relative), line (or null), severity (critical/high/medium/low), "
    "category (security/performance/accessibility/maintainability/testing/api-contract/other), "
    "a one-sentence summary, and a concrete suggested fix. Return an empty list when there is nothing to report."
)


def build_reviewer_prompt(files: list[str], diff_hint: str) -> str:
    file_list = "\n".join(f"- {file}" for file in files)
    return (
        "Review these changed files in the current repository:\n"
        f"{file_list}\n\n"
        f"How to see the change: {diff_hint}\n"
        "Read the files yourself for full context. Keep findings to this change; do not audit unrelated code.\n"
        f"{FINDING_INSTRUCTIONS}"
    )


def to_findings(agent: str, output: ReviewerOutput) -> list[Finding]:
    return [
        {
            "agent": agent,
            "file": normalize_path(item.file),
            "line": item.line,
            "severity": item.severity,
            "category": item.category,
            "summary": item.summary,
            "fix": item.fix,
            "verification": "unchecked",
        }
        for item in output.findings
    ]


def make_reviewer_node(runner: AgentRunner, specs: dict[str, AgentSpec], limits: RunLimits):
    async def reviewer_node(payload: dict) -> dict:
        spec = specs[payload["agent"]]
        prompt = build_reviewer_prompt(payload["files"], payload.get("diff_hint", ""))
        outcome = await execute_with_retries(
            runner, spec, prompt, ReviewerOutput, limits, payload.get("repo_root", "."), "reviewer"
        )
        return {
            "findings": to_findings(spec.name, outcome.output) if outcome.output else [],
            "failures": [outcome.failure] if outcome.failure else [],
            "usage": outcome.usage,
        }

    return reviewer_node
