from review_graph.nodes.route import bucket_files, fan_out_to_reviewers, is_docs_only, needs_architecture_review, route_node


def test_docs_only_change_selects_no_agents():
    assert bucket_files(["README.md", "docs/notes.md"]) == {}
    assert is_docs_only(["README.md"])


def test_empty_change_set_selects_no_agents():
    assert bucket_files([]) == {}


def test_backend_change_routes_to_backend_security_and_testing():
    routing = bucket_files(["TrashAnimal/GameSession.cs"])
    assert set(routing) == {"backend-reviewer", "security-reviewer", "testing-reviewer"}


def test_api_files_route_to_backend_but_test_projects_do_not():
    routing = bucket_files(["TrashAnimal.Api/Program.cs", "TrashAnimal.Api.Tests/ApiTests.cs", "TrashAnimal.Tests/X.cs"])
    assert routing["backend-reviewer"] == ["TrashAnimal.Api/Program.cs"]
    assert len(routing["testing-reviewer"]) == 3


def test_frontend_files_route_only_for_web_code_extensions():
    routing = bucket_files(["TrashAnimal.Web/src/App.tsx", "TrashAnimal.Web/package.json", "TrashAnimal.Web/src/index.css"])
    assert routing["frontend-reviewer"] == ["TrashAnimal.Web/src/App.tsx", "TrashAnimal.Web/src/index.css"]
    assert "backend-reviewer" not in routing


def test_windows_separators_are_normalized():
    routing = bucket_files(["TrashAnimal.Web\\src\\App.tsx"])
    assert routing["frontend-reviewer"] == ["TrashAnimal.Web/src/App.tsx"]


def test_architecture_runs_only_for_cs_ts_tsx():
    assert needs_architecture_review(["a/B.cs"])
    assert not needs_architecture_review(["a/style.css", "b.json"])


def test_route_node_flags_docs_only():
    update = route_node({"changed_files": ["README.md"]})
    assert update["docs_only"] and not update["run_architecture"] and update["routing"] == {}


def test_fan_out_sends_one_task_per_selected_agent_and_reports_when_none():
    state = route_node({"changed_files": ["TrashAnimal/A.cs"], "diff_hint": "hint", "repo_root": "."})
    sends = fan_out_to_reviewers(state)
    assert [send.arg["agent"] for send in sends] == ["backend-reviewer", "security-reviewer", "testing-reviewer"]
    assert fan_out_to_reviewers({"routing": {}}) == "report"
