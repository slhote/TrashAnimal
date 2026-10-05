from __future__ import annotations

import operator
from typing import Annotated, Literal, Optional, TypedDict

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]
Category = Literal[
    "security", "performance", "accessibility", "maintainability", "testing", "api-contract", "other"
]
Verification = Literal["unchecked", "confirmed", "unverified"]
Verdict = Literal["BLOCK_MERGE", "REQUIRES_APPROVAL", "CLEAR"]

SEVERITY_ORDER: list[str] = ["low", "medium", "high", "critical"]

SECURITY_AGENT = "security-reviewer"
ARCHITECTURE_AGENT = "architecture-reviewer"
PHASE_ONE_AGENTS = ["frontend-reviewer", "backend-reviewer", "security-reviewer", "testing-reviewer"]


def severity_rank(severity: str) -> int:
    return SEVERITY_ORDER.index(severity)


def bump_severity(severity: str) -> str:
    return SEVERITY_ORDER[min(severity_rank(severity) + 1, len(SEVERITY_ORDER) - 1)]


class ReviewerFinding(BaseModel):
    file: str
    line: Optional[int] = None
    severity: Severity
    category: Category = "other"
    summary: str
    fix: str = ""


class ReviewerOutput(BaseModel):
    findings: list[ReviewerFinding] = Field(default_factory=list)


class VerifierOutput(BaseModel):
    confirmed: bool
    reason: str = ""


class Finding(TypedDict, total=False):
    agent: str
    file: str
    line: Optional[int]
    severity: str
    category: str
    summary: str
    fix: str
    verification: str


class MergedFinding(TypedDict, total=False):
    agents: list[str]
    file: str
    line: Optional[int]
    severity: str
    category: str
    summary: str
    fix: str
    verification: str
    notes: list[str]


class Failure(TypedDict):
    agent: str
    reason: str


class Usage(TypedDict):
    node: str
    agent: str
    cost_usd: float
    turns: int


class ReviewState(TypedDict, total=False):
    scope_args: dict
    repo_root: str
    diff_hint: str
    changed_files: list[str]
    changed_hunks: dict
    docs_only: bool
    routing: dict
    run_architecture: bool
    architecture_done: bool
    original_ref: str
    branch_changed: bool
    findings: Annotated[list[Finding], operator.add]
    failures: Annotated[list[Failure], operator.add]
    usage: Annotated[list[Usage], operator.add]
    warnings: Annotated[list[str], operator.add]
    current_ref: str
    verified_findings: list[Finding]
    dropped_findings: list[dict]
    merged_findings: list[MergedFinding]
    verdict: str
    security_block: bool
    incomplete_reviews: list[str]
    approval_decision: str
    report_markdown: str
    report_json: dict
