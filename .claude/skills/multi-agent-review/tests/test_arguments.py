from review_cli.arguments import parse_arguments, scope_from_arguments, scope_was_given, validate_arguments
from review_cli.exit_codes import EXIT_BLOCKED, EXIT_CLEAR, EXIT_REJECTED, exit_code_for


def args_for(*argv):
    return parse_arguments(list(argv))


def test_decision_without_resume_is_rejected():
    assert "--decision" in validate_arguments(args_for("--decision", "approved"))


def test_scope_flags_with_resume_and_thread_id_are_rejected():
    assert validate_arguments(args_for("--resume", "--thread-id", "x", "--pr", "53"))


def test_resume_alone_filter_or_explicit_id_are_valid():
    assert validate_arguments(args_for("--resume")) is None
    assert validate_arguments(args_for("--resume", "--pr", "53")) is None
    assert validate_arguments(args_for("--resume", "--thread-id", "x", "--decision", "approved")) is None


def test_scope_was_given_distinguishes_a_filter_from_the_default():
    assert not scope_was_given(args_for("--resume"))
    assert scope_was_given(args_for("--resume", "--staged"))


def test_scope_and_label_for_each_scope_flag():
    assert scope_from_arguments(args_for("--pr", "53")) == ({"kind": "pr", "value": 53}, "pr-53")
    assert scope_from_arguments(args_for("--staged")) == ({"kind": "staged"}, "staged")
    assert scope_from_arguments(args_for("--since", "main")) == ({"kind": "since", "value": "main"}, "since-main")
    assert scope_from_arguments(args_for("--paths", "a", "b")) == ({"kind": "paths", "value": ["a", "b"]}, "paths")
    assert scope_from_arguments(args_for()) == ({"kind": "default"}, "branch")


def test_exit_code_follows_the_verdict_and_the_approval_decision():
    assert exit_code_for({"verdict": "CLEAR"}) == EXIT_CLEAR
    assert exit_code_for({"verdict": "BLOCK_MERGE"}) == EXIT_BLOCKED
    assert exit_code_for({"verdict": "REQUIRES_APPROVAL", "approval_decision": "rejected"}) == EXIT_REJECTED
    assert exit_code_for({"verdict": "REQUIRES_APPROVAL", "approval_decision": "approved"}) == EXIT_CLEAR
