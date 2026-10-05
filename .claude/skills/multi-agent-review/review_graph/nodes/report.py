from __future__ import annotations

from ..state import SEVERITY_ORDER, ReviewState

VERDICT_HEADLINES = {
    "BLOCK_MERGE": "BLOCK MERGE",
    "REQUIRES_APPROVAL": "REQUIRES APPROVAL before merge",
    "CLEAR": "CLEAR",
}


def total_cost(state: ReviewState) -> float:
    return round(sum(entry["cost_usd"] for entry in state.get("usage", [])), 4)


def cost_by_agent(state: ReviewState) -> dict[str, float]:
    totals: dict[str, float] = {}
    for entry in state.get("usage", []):
        totals[entry["agent"]] = totals.get(entry["agent"], 0.0) + entry["cost_usd"]
    return {agent: round(cost, 4) for agent, cost in totals.items()}


def render_finding(finding: dict) -> str:
    location = finding["file"] + (f":{finding['line']}" if finding.get("line") else "")
    lines = [
        f"- `{location}` ({', '.join(finding['agents'])}; {finding['verification']}): {finding['summary']}",
    ]
    if finding.get("fix"):
        lines.append(f"  - Fix: {finding['fix']}")
    lines.extend(f"  - Note: {note}" for note in finding.get("notes", []))
    return "\n".join(lines)


def render_markdown(state: ReviewState) -> str:
    verdict = state.get("verdict", "CLEAR")
    lines = [f"# Review verdict: {VERDICT_HEADLINES[verdict]}", ""]

    if state.get("security_block"):
        lines += ["**Security gate:** a security-reviewer CRITICAL finding or a failed security review blocks this merge.", ""]
    if state.get("approval_decision"):
        lines += [f"Approval decision: **{state['approval_decision']}**", ""]
    if state.get("docs_only"):
        lines += ["No code changed (docs-only or empty change set); no review was run.", ""]

    for failure in state.get("failures", []):
        lines.append(f"- Review did not complete: `{failure['agent']}` ({failure['reason']})")
    if state.get("failures"):
        lines.append("")

    merged = state.get("merged_findings", [])
    for severity in reversed(SEVERITY_ORDER):
        group = [finding for finding in merged if finding["severity"] == severity]
        if group:
            lines += [f"## {severity.upper()} ({len(group)})", *(render_finding(f) for f in group), ""]
    if not merged and not state.get("docs_only"):
        lines += ["No findings.", ""]

    dropped = state.get("dropped_findings", [])
    if dropped:
        lines += [f"{len(dropped)} finding(s) were dropped by verification (out of scope or refuted).", ""]
    if state.get("warnings"):
        lines += ["## Warnings", *(f"- {warning}" for warning in state["warnings"]), ""]

    per_agent = cost_by_agent(state)
    if per_agent:
        lines += ["## Cost", *(f"- {agent}: ${cost:.4f}" for agent, cost in per_agent.items()), f"- total: ${total_cost(state):.4f}"]
    return "\n".join(lines).rstrip() + "\n"


def report_node(state: ReviewState) -> dict:
    return {
        "report_markdown": render_markdown(state),
        "report_json": {
            "verdict": state.get("verdict", "CLEAR"),
            "security_block": state.get("security_block", False),
            "approval_decision": state.get("approval_decision"),
            "incomplete_reviews": state.get("incomplete_reviews", []),
            "findings": state.get("merged_findings", []),
            "dropped_findings": state.get("dropped_findings", []),
            "warnings": state.get("warnings", []),
            "cost_usd": {"total": total_cost(state), "by_agent": cost_by_agent(state)},
        },
    }
