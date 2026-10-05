from conftest import make_finding
from review_graph.nodes.synthesize import synthesize


def test_no_findings_is_clear():
    assert synthesize([], [])["verdict"] == "CLEAR"


def test_two_agents_on_same_line_raise_severity_one_level_and_merge():
    findings = [
        make_finding("backend-reviewer", severity="medium", category="maintainability"),
        make_finding("architecture-reviewer", severity="medium", category="maintainability"),
    ]
    result = synthesize(findings, [])
    assert len(result["merged_findings"]) == 1
    merged = result["merged_findings"][0]
    assert merged["severity"] == "high"
    assert merged["agents"] == ["architecture-reviewer", "backend-reviewer"]
    assert result["verdict"] == "REQUIRES_APPROVAL"


def test_security_critical_is_never_downgraded_by_other_agents():
    findings = [
        make_finding("security-reviewer", severity="critical", category="security"),
        make_finding("backend-reviewer", severity="low", category="security"),
    ]
    result = synthesize(findings, [])
    assert result["merged_findings"][0]["severity"] == "critical"
    assert result["verdict"] == "BLOCK_MERGE" and result["security_block"] is True


def test_priority_matrix_resolves_severity_disagreement_before_agreement_bump():
    findings = [
        make_finding("frontend-reviewer", file="TrashAnimal.Web/a.tsx", severity="low", category="accessibility"),
        make_finding("backend-reviewer", file="TrashAnimal.Web/a.tsx", severity="high", category="accessibility"),
    ]
    merged = synthesize(findings, [])["merged_findings"][0]
    assert merged["severity"] == "medium"


def test_unrelated_findings_stay_separate_and_sort_by_severity():
    findings = [
        make_finding(file="TrashAnimal/A.cs", line=1, severity="low"),
        make_finding(file="TrashAnimal/B.cs", line=1, severity="high"),
    ]
    merged = synthesize(findings, [])["merged_findings"]
    assert [m["severity"] for m in merged] == ["high", "low"]


def test_same_agent_findings_are_not_merged():
    findings = [make_finding(line=10), make_finding(line=11)]
    assert len(synthesize(findings, [])["merged_findings"]) == 2


def test_api_contract_findings_link_backend_and_frontend_across_files():
    findings = [
        make_finding("backend-reviewer", file="TrashAnimal.Api/Dto.cs", severity="medium", category="api-contract"),
        make_finding("frontend-reviewer", file="TrashAnimal.Web/api.ts", severity="medium", category="api-contract"),
    ]
    merged = synthesize(findings, [])["merged_findings"]
    assert len(merged) == 1
    assert any("backend and frontend" in note for note in merged[0]["notes"])


def test_any_other_critical_blocks_without_security_callout():
    result = synthesize([make_finding("backend-reviewer", severity="critical")], [])
    assert result["verdict"] == "BLOCK_MERGE" and result["security_block"] is False


def test_failed_security_reviewer_blocks_merge():
    result = synthesize([], [{"agent": "security-reviewer", "reason": "timed out"}])
    assert result["verdict"] == "BLOCK_MERGE" and result["security_block"] is True
    assert result["incomplete_reviews"] == ["security-reviewer"]


def test_failed_non_security_reviewer_requires_approval_instead_of_clear():
    result = synthesize([], [{"agent": "frontend-reviewer", "reason": "boom"}])
    assert result["verdict"] == "REQUIRES_APPROVAL"


def test_confirmed_verification_wins_when_merging():
    findings = [
        make_finding("backend-reviewer", verification="unverified"),
        make_finding("security-reviewer", verification="confirmed"),
    ]
    assert synthesize(findings, [])["merged_findings"][0]["verification"] == "confirmed"
