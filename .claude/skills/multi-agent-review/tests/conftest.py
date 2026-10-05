from __future__ import annotations

import pytest

from review_graph.agents_loader import AgentSpec
from review_graph.git_client import ScopeResult
from review_graph.runner import AgentRunError, RunResult
from review_graph.state import (
    ARCHITECTURE_AGENT,
    PHASE_ONE_AGENTS,
    ReviewerFinding,
    ReviewerOutput,
    VerifierOutput,
)


def make_finding(agent="backend-reviewer", file="TrashAnimal/A.cs", line=10, severity="medium", category="other", **extra):
    return {
        "agent": agent,
        "file": file,
        "line": line,
        "severity": severity,
        "category": category,
        "summary": f"{agent} issue",
        "fix": "fix it",
        "verification": "unchecked",
        **extra,
    }


def reviewer_finding(file="TrashAnimal/A.cs", line=10, severity="medium", category="other", summary="problem"):
    return {"file": file, "line": line, "severity": severity, "category": category, "summary": summary, "fix": "fix"}


class FakeGit:
    def __init__(self, hunks, ref="feature", diff_hint="git diff main...HEAD"):
        self.repo_root = "."
        self.hunks = hunks
        self.ref = ref
        self.diff_hint = diff_hint
        self.checkouts: list[str] = []

    def current_ref(self):
        return self.ref

    def checkout(self, ref):
        self.checkouts.append(ref)
        self.ref = ref

    def scope_diff(self, scope_args):
        return ScopeResult(self.hunks, self.diff_hint)


class FakeRunner:
    def __init__(self, findings_by_agent=None, failing=(), verifier=lambda prompt: True, on_run=None):
        self.findings_by_agent = findings_by_agent or {}
        self.failing = set(failing)
        self.verifier = verifier
        self.on_run = on_run
        self.calls: list[str] = []
        self.prompts: dict[str, str] = {}

    async def run(self, spec, prompt, output_model, limits, cwd):
        self.calls.append(spec.name)
        self.prompts[spec.name] = prompt
        if self.on_run:
            self.on_run(spec.name)
        if spec.name in self.failing:
            raise AgentRunError("simulated failure", cost_usd=0.05, turns=3, retryable=False)
        if output_model is VerifierOutput:
            return RunResult(VerifierOutput(confirmed=self.verifier(prompt), reason="checked"), 0.01, 1)
        findings = [ReviewerFinding(**f) for f in self.findings_by_agent.get(spec.name, [])]
        return RunResult(ReviewerOutput(findings=findings), 0.1, 2)


@pytest.fixture
def specs():
    return {
        name: AgentSpec(name=name, description="", tools=["Read", "Grep", "Glob", "Bash"], prompt=f"You are {name}.")
        for name in [*PHASE_ONE_AGENTS, ARCHITECTURE_AGENT]
    }
