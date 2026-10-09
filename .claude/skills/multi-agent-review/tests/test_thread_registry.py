import itertools

import pytest

from review_graph.thread_registry import ThreadRegistry


@pytest.fixture
def registry(tmp_path):
    ticks = itertools.count(100)
    return ThreadRegistry(tmp_path / "registry.sqlite", clock=lambda: float(next(ticks)), current_pid=lambda: 4242)


def test_fresh_begin_records_owner_and_marks_running(registry):
    registry.begin("pr-53", "pr-53", fresh=True)
    record = registry.get("pr-53")
    assert record.pid == 4242 and record.scope_label == "pr-53"
    assert record.running_since == record.created_at == record.updated_at


def test_mark_idle_clears_running_since_but_keeps_the_row(registry):
    registry.begin("pr-53", "pr-53", fresh=True)
    registry.mark_idle("pr-53")
    record = registry.get("pr-53")
    assert record.running_since is None and record.updated_at > record.created_at


def test_resume_keeps_creation_time_and_scope_label(registry):
    registry.begin("pr-53", "pr-53", fresh=True)
    created_at = registry.get("pr-53").created_at
    registry.mark_idle("pr-53")
    registry.begin("pr-53", "branch", fresh=False)
    record = registry.get("pr-53")
    assert record.created_at == created_at and record.scope_label == "pr-53"
    assert record.running_since is not None


def test_resume_without_an_existing_row_inserts_one(registry):
    registry.begin("older-thread", "branch", fresh=False)
    assert registry.get("older-thread").scope_label == "branch"


def test_fresh_begin_on_a_reused_thread_id_replaces_the_row(registry):
    registry.begin("pr-53", "pr-53", fresh=True)
    first_created_at = registry.get("pr-53").created_at
    registry.mark_idle("pr-53")
    registry.begin("pr-53", "pr-53", fresh=True)
    assert registry.get("pr-53").created_at > first_created_at
    assert len(registry.list_all()) == 1


def test_remove_deletes_the_row_and_tolerates_unknown_ids(registry):
    registry.begin("pr-53", "pr-53", fresh=True)
    registry.remove("pr-53")
    registry.remove("never-existed")
    registry.mark_idle("pr-53")
    assert registry.get("pr-53") is None and registry.list_all() == []


def test_list_all_returns_most_recently_updated_first(registry):
    registry.begin("first", "a", fresh=True)
    registry.begin("second", "b", fresh=True)
    registry.mark_idle("first")
    assert [record.thread_id for record in registry.list_all()] == ["first", "second"]


def test_rows_survive_reopening_the_database(tmp_path):
    path = tmp_path / "registry.sqlite"
    ThreadRegistry(path).begin("pr-53", "pr-53", fresh=True)
    assert ThreadRegistry(path).get("pr-53") is not None
