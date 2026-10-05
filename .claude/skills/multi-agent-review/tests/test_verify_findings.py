import asyncio

from conftest import FakeRunner, make_finding
from review_graph.nodes.verify_findings import filter_findings, make_verify_findings_node
from review_graph.runner import RunLimits


def test_findings_on_files_outside_the_change_are_dropped():
    kept, dropped = filter_findings([make_finding(file="Other.cs")], ["TrashAnimal/A.cs"], {"TrashAnimal/A.cs": [(1, 50)]})
    assert kept == [] and dropped[0]["dropped_because"] == "file is not part of the change"


def test_line_outside_hunks_is_dropped_but_tolerance_applies():
    hunks = {"TrashAnimal/A.cs": [(10, 12)]}
    near, _ = filter_findings([make_finding(line=15)], ["TrashAnimal/A.cs"], hunks)
    far, dropped = filter_findings([make_finding(line=40)], ["TrashAnimal/A.cs"], hunks)
    assert len(near) == 1 and far == [] and "outside" in dropped[0]["dropped_because"]


def test_whole_file_scope_and_file_level_findings_are_kept():
    kept, _ = filter_findings(
        [make_finding(line=999), make_finding(line=None)], ["TrashAnimal/A.cs"], {"TrashAnimal/A.cs": None}
    )
    assert len(kept) == 2
    kept_file_level, _ = filter_findings([make_finding(line=None)], ["TrashAnimal/A.cs"], {"TrashAnimal/A.cs": [(1, 2)]})
    assert len(kept_file_level) == 1


def test_out_of_scope_security_critical_is_kept_as_unverified():
    finding = make_finding("security-reviewer", file="Other.cs", severity="critical", category="security")
    kept, dropped = filter_findings([finding], ["TrashAnimal/A.cs"], {})
    assert dropped == [] and kept[0]["verification"] == "unverified"


def run_node(findings, runner):
    node = make_verify_findings_node(runner, RunLimits(max_attempts=1))
    state = {
        "findings": findings,
        "changed_files": ["TrashAnimal/A.cs"],
        "changed_hunks": {"TrashAnimal/A.cs": None},
        "repo_root": ".",
    }
    return asyncio.run(node(state))


def test_refuted_high_finding_is_dropped_and_confirmed_one_is_marked():
    findings = [make_finding(line=1, severity="high", summary="KEEP"), make_finding(line=2, severity="high", summary="DROP")]
    runner = FakeRunner(verifier=lambda prompt: "KEEP" in prompt)
    update = run_node(findings, runner)
    assert [f["summary"] for f in update["verified_findings"]] == ["KEEP"]
    assert update["verified_findings"][0]["verification"] == "confirmed"
    assert "refuted" in update["dropped_findings"][0]["dropped_because"]


def test_medium_and_low_findings_skip_the_recheck():
    runner = FakeRunner()
    update = run_node([make_finding(severity="medium")], runner)
    assert runner.calls == [] and update["verified_findings"][0]["verification"] == "unchecked"


def test_refuted_security_critical_is_kept_unverified_not_dropped():
    finding = make_finding("security-reviewer", severity="critical", category="security")
    update = run_node([finding], FakeRunner(verifier=lambda prompt: False))
    assert update["verified_findings"][0]["verification"] == "unverified" and update["dropped_findings"] == []


def test_verifier_failure_keeps_finding_unverified_and_warns():
    runner = FakeRunner(failing={"finding-verifier"})
    update = run_node([make_finding(severity="high")], runner)
    assert update["verified_findings"][0]["verification"] == "unverified"
    assert update["warnings"]
