from conftest import FakeGit
from review_graph.nodes.branch_guard import make_branch_guard_nodes


def test_unchanged_branch_is_not_flagged():
    git = FakeGit({})
    snapshot, verify, _ = make_branch_guard_nodes(git)
    state = snapshot({})
    assert verify(state)["branch_changed"] is False


def test_changed_branch_is_flagged_and_restored_with_a_warning():
    git = FakeGit({}, ref="feature")
    snapshot, verify, restore = make_branch_guard_nodes(git)
    state = snapshot({})
    git.ref = "main"
    state.update(verify(state))
    assert state["branch_changed"] is True
    update = restore(state)
    assert git.checkouts == ["feature"] and git.ref == "feature"
    assert update["branch_changed"] is False and "feature" in update["warnings"][0]
