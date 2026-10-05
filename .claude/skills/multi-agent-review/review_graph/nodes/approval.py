from __future__ import annotations

from langgraph.types import interrupt

from ..state import ReviewState


async def approval_node(state: ReviewState) -> dict:
    high_findings = [
        f"{finding['file']}:{finding.get('line') or '-'} [{finding['severity']}] {finding['summary']}"
        for finding in state.get("merged_findings", [])
        if finding["severity"] == "high"
    ]
    decision = interrupt(
        {
            "verdict": state.get("verdict"),
            "high_findings": high_findings,
            "incomplete_reviews": state.get("incomplete_reviews", []),
        }
    )
    return {"approval_decision": str(decision)}
