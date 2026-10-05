from __future__ import annotations

from ..agent_execution import execute_with_retries
from ..agents_loader import AgentSpec
from ..runner import AgentRunner, RunLimits
from ..state import ARCHITECTURE_AGENT, ReviewerOutput, ReviewState
from .reviewer import FINDING_INSTRUCTIONS, to_findings


def summarize_phase_one(state: ReviewState) -> str:
    lines = [
        f"- [{f['agent']}] {f['file']}:{f.get('line') or '-'} {f['severity']}: {f['summary']}"
        for f in state.get("findings", [])
    ]
    for failure in state.get("failures", []):
        lines.append(f"- [{failure['agent']}] review did not complete: {failure['reason']}")
    return "\n".join(lines) or "- (no findings from the specialist reviewers)"


def build_architecture_prompt(state: ReviewState) -> str:
    file_list = "\n".join(f"- {file}" for file in state.get("changed_files", []))
    return (
        "Review the structure and maintainability of these changed files:\n"
        f"{file_list}\n\n"
        f"How to see the change: {state.get('diff_hint', '')}\n\n"
        "Findings already reported by the specialist reviewers (build on these, do not repeat them):\n"
        f"{summarize_phase_one(state)}\n\n"
        f"{FINDING_INSTRUCTIONS}"
    )


def make_architecture_node(runner: AgentRunner, specs: dict[str, AgentSpec], limits: RunLimits):
    async def architecture_node(state: ReviewState) -> dict:
        outcome = await execute_with_retries(
            runner,
            specs[ARCHITECTURE_AGENT],
            build_architecture_prompt(state),
            ReviewerOutput,
            limits,
            state.get("repo_root", "."),
            "architecture",
        )
        return {
            "architecture_done": True,
            "findings": to_findings(ARCHITECTURE_AGENT, outcome.output) if outcome.output else [],
            "failures": [outcome.failure] if outcome.failure else [],
            "usage": outcome.usage,
        }

    return architecture_node
