from __future__ import annotations

import asyncio

from ..agent_execution import execute_with_retries
from ..agents_loader import AgentSpec
from ..runner import AgentRunner, RunLimits
from ..state import SECURITY_AGENT, Finding, ReviewState, VerifierOutput
from .route import normalize_path

LINE_TOLERANCE = 3
RECHECK_SEVERITIES = {"critical", "high"}
VERIFIER_CONCURRENCY = 4

VERIFIER_SPEC = AgentSpec(
    name="finding-verifier",
    description="Confirms or refutes a single code review finding",
    tools=["Read", "Grep", "Glob", "Bash"],
    prompt=(
        "You verify one code review finding against the real code. Read the cited file and surrounding code. "
        "Set confirmed=true only if the problem genuinely exists as described; otherwise confirmed=false and say why. "
        "Be skeptical of findings that cite code you cannot find."
    ),
)


def is_security_critical(finding: Finding) -> bool:
    return finding["agent"] == SECURITY_AGENT and finding["severity"] == "critical"


def line_is_in_changed_ranges(line: int, ranges: list) -> bool:
    return any(start - LINE_TOLERANCE <= line <= end + LINE_TOLERANCE for start, end in ranges)


def out_of_scope_reason(finding: Finding, changed_files: set[str], hunks: dict) -> str | None:
    file = normalize_path(finding["file"])
    if file not in changed_files:
        return "file is not part of the change"
    ranges = hunks.get(file)
    line = finding.get("line")
    if ranges is not None and line is not None and not line_is_in_changed_ranges(line, ranges):
        return "line is outside the changed hunks"
    return None


def filter_findings(
    findings: list[Finding], changed_files: list[str], hunks: dict
) -> tuple[list[Finding], list[dict]]:
    scope = {normalize_path(path) for path in changed_files}
    kept: list[Finding] = []
    dropped: list[dict] = []
    for finding in findings:
        reason = out_of_scope_reason(finding, scope, hunks)
        if reason is None:
            kept.append(dict(finding))
        elif is_security_critical(finding):
            kept.append({**finding, "verification": "unverified"})
        else:
            dropped.append({**finding, "dropped_because": reason})
    return kept, dropped


def build_verifier_prompt(finding: Finding) -> str:
    return (
        f"Finding from {finding['agent']}:\n"
        f"- file: {finding['file']}\n- line: {finding.get('line')}\n- severity: {finding['severity']}\n"
        f"- summary: {finding['summary']}\n- suggested fix: {finding.get('fix', '')}\n\n"
        "Is this a real problem in the current code?"
    )


def make_verify_findings_node(runner: AgentRunner, limits: RunLimits):
    async def verify_findings_node(state: ReviewState) -> dict:
        kept, dropped = filter_findings(
            state.get("findings", []), state.get("changed_files", []), state.get("changed_hunks", {})
        )
        semaphore = asyncio.Semaphore(VERIFIER_CONCURRENCY)
        repo_root = state.get("repo_root", ".")
        usage: list = []
        warnings: list[str] = []

        async def recheck(finding: Finding) -> Finding | None:
            if finding["severity"] not in RECHECK_SEVERITIES or finding.get("verification") == "unverified":
                return finding
            async with semaphore:
                outcome = await execute_with_retries(
                    runner, VERIFIER_SPEC, build_verifier_prompt(finding), VerifierOutput, limits, repo_root, "verify_findings"
                )
            usage.extend(outcome.usage)
            if outcome.output is None:
                warnings.append(
                    f"Could not re-check {finding['file']}:{finding.get('line')} ({outcome.failure['reason']}); kept as unverified."
                )
                return {**finding, "verification": "unverified"}
            if outcome.output.confirmed:
                return {**finding, "verification": "confirmed"}
            if is_security_critical(finding):
                return {**finding, "verification": "unverified"}
            dropped.append({**finding, "dropped_because": f"refuted by verifier: {outcome.output.reason}"})
            return None

        async with asyncio.TaskGroup() as group:
            pending = [group.create_task(recheck(finding)) for finding in kept]
        rechecked = [task.result() for task in pending]
        return {
            "verified_findings": [finding for finding in rechecked if finding is not None],
            "dropped_findings": dropped,
            "usage": usage,
            "warnings": warnings,
        }

    return verify_findings_node
