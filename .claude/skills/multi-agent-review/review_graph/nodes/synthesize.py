from __future__ import annotations

from ..priority_matrix import agent_weight
from ..state import (
    SECURITY_AGENT,
    Failure,
    Finding,
    MergedFinding,
    ReviewState,
    bump_severity,
    severity_rank,
)

LINE_PROXIMITY = 5
FRONTEND_AGENT = "frontend-reviewer"
BACKEND_AGENT = "backend-reviewer"


def _lines_near(first: Finding, second: Finding) -> bool:
    first_line, second_line = first.get("line"), second.get("line")
    if first_line is None or second_line is None:
        return True
    return abs(first_line - second_line) <= LINE_PROXIMITY


def _are_related(first: Finding, second: Finding) -> bool:
    if first["agent"] == second["agent"]:
        return False
    both_api_contract = first.get("category") == "api-contract" and second.get("category") == "api-contract"
    if both_api_contract and {first["agent"], second["agent"]} == {FRONTEND_AGENT, BACKEND_AGENT}:
        return True
    if first["file"] != second["file"]:
        return False
    same_line = first.get("line") is not None and first.get("line") == second.get("line")
    same_issue_type = first.get("category") == second.get("category") and _lines_near(first, second)
    return same_line or same_issue_type


def _cluster_findings(findings: list[Finding]) -> list[list[Finding]]:
    parent = list(range(len(findings)))

    def find_root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i in range(len(findings)):
        for j in range(i + 1, len(findings)):
            if _are_related(findings[i], findings[j]):
                parent[find_root(i)] = find_root(j)

    clusters: dict[int, list[Finding]] = {}
    for index, finding in enumerate(findings):
        clusters.setdefault(find_root(index), []).append(finding)
    return list(clusters.values())


def _resolve_base_severity(cluster: list[Finding], category: str) -> str:
    best = max(cluster, key=lambda f: (agent_weight(f["agent"], category), severity_rank(f["severity"])))
    return best["severity"]


def _resolve_verification(cluster: list[Finding]) -> str:
    states = {f.get("verification", "unchecked") for f in cluster}
    if "confirmed" in states:
        return "confirmed"
    if "unverified" in states:
        return "unverified"
    return "unchecked"


def merge_cluster(cluster: list[Finding]) -> MergedFinding:
    agents = sorted({f["agent"] for f in cluster})
    lead = max(cluster, key=lambda f: (severity_rank(f["severity"]), agent_weight(f["agent"], f.get("category", "other"))))
    category = lead.get("category", "other")
    notes: list[str] = []

    severity = _resolve_base_severity(cluster, category)
    if len(agents) >= 2:
        severity = bump_severity(severity)
        notes.append(f"Raised one level: flagged by {', '.join(agents)}")

    security_critical = any(f["agent"] == SECURITY_AGENT and f["severity"] == "critical" for f in cluster)
    if security_critical and severity != "critical":
        severity = "critical"
        notes.append("Held at critical: security-reviewer rating is never downgraded")

    if FRONTEND_AGENT in agents and BACKEND_AGENT in agents:
        notes.append("Spans backend and frontend: treat the fix as one change across both sides")

    lines = [f["line"] for f in cluster if f.get("line") is not None]
    return {
        "agents": agents,
        "file": lead["file"],
        "line": min(lines) if lines else None,
        "severity": severity,
        "category": category,
        "summary": lead["summary"],
        "fix": lead.get("fix", ""),
        "verification": _resolve_verification(cluster),
        "notes": notes,
    }


def decide_verdict(merged: list[MergedFinding], failures: list[Failure]) -> tuple[str, bool]:
    security_block = any(
        SECURITY_AGENT in finding["agents"] and finding["severity"] == "critical" for finding in merged
    ) or any(failure["agent"] == SECURITY_AGENT for failure in failures)

    if security_block or any(finding["severity"] == "critical" for finding in merged):
        return "BLOCK_MERGE", security_block
    if any(finding["severity"] == "high" for finding in merged) or failures:
        return "REQUIRES_APPROVAL", False
    return "CLEAR", False


def synthesize(findings: list[Finding], failures: list[Failure]) -> dict:
    merged = [merge_cluster(cluster) for cluster in _cluster_findings(findings)]
    merged.sort(key=lambda f: (-severity_rank(f["severity"]), f["file"], f.get("line") or 0))
    verdict, security_block = decide_verdict(merged, failures)
    return {
        "merged_findings": merged,
        "verdict": verdict,
        "security_block": security_block,
        "incomplete_reviews": sorted({failure["agent"] for failure in failures}),
    }


def synthesize_node(state: ReviewState) -> dict:
    findings = state["verified_findings"] if "verified_findings" in state else state.get("findings", [])
    return synthesize(findings, state.get("failures", []))
