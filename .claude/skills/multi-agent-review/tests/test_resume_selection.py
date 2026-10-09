import io

from review_graph.resumable_threads import ResumableSearch, ResumableThread
from review_graph.resume_selection import (
    NeedsUserInput,
    ResumeThread,
    describe_need,
    make_terminal_chooser,
    need_to_payload,
    select_review,
)

PR_53 = {"kind": "pr", "value": 53}
PR_54 = {"kind": "pr", "value": 54}


def thread(thread_id, scope_args=PR_53, kind="UNFINISHED", updated_at=1000.0):
    return ResumableThread(thread_id, kind, "label", scope_args, updated_at, None)


def pick_first(threads):
    return threads[0]


def test_filtered_single_match_is_resumed_without_asking():
    search = ResumableSearch([thread("a"), thread("b", PR_54)])
    assert select_review(search, PR_53, choose=None) == ResumeThread("a")


def test_filtered_single_match_does_not_call_the_chooser():
    search = ResumableSearch([thread("a")])

    def fail(threads):
        raise AssertionError("must not ask")

    assert select_review(search, PR_53, fail) == ResumeThread("a")


def test_filtered_several_matches_need_a_choice_when_not_interactive():
    search = ResumableSearch([thread("a"), thread("b")])
    outcome = select_review(search, PR_53, choose=None)
    assert outcome == NeedsUserInput("choose", [thread("a"), thread("b")], 0)


def test_unfiltered_single_open_review_is_still_not_auto_picked():
    outcome = select_review(ResumableSearch([thread("a")]), None, choose=None)
    assert isinstance(outcome, NeedsUserInput) and outcome.reason == "choose"


def test_interactive_choice_is_resumed_and_only_filtered_candidates_are_offered():
    offered = []

    def choose(threads):
        offered.extend(threads)
        return threads[1]

    search = ResumableSearch([thread("a"), thread("other", PR_54), thread("b")])
    assert select_review(search, PR_53, choose) == ResumeThread("b")
    assert [t.thread_id for t in offered] == ["a", "b"]


def test_cancelled_choice_asks_the_user_what_to_do():
    outcome = select_review(ResumableSearch([thread("a"), thread("b")]), None, lambda threads: None)
    assert outcome.reason == "cancelled"


def test_nothing_matching_the_scope_reports_none_match_and_still_lists_other_reviews():
    search = ResumableSearch([thread("a", PR_54)], running_elsewhere=2)
    outcome = select_review(search, PR_53, choose=pick_first)
    assert outcome.reason == "none_match" and outcome.running_elsewhere == 2
    assert [t.thread_id for t in outcome.open_reviews] == ["a"]


def test_no_open_reviews_at_all_reports_none_open():
    assert select_review(ResumableSearch(), None, choose=pick_first).reason == "none_open"
    assert select_review(ResumableSearch(), PR_53, choose=pick_first).reason == "none_open"


def test_messages_mention_reviews_running_elsewhere():
    assert "3 running in another process" in describe_need(NeedsUserInput("none_open", [], 3))
    assert "running" not in describe_need(NeedsUserInput("none_open", [], 0))


def test_payload_is_json_ready_and_carries_what_the_skill_needs_to_ask():
    payload = need_to_payload(NeedsUserInput("choose", [thread("a")], 1))
    assert payload["reason"] == "choose" and payload["running_elsewhere"] == 1
    assert payload["open_reviews"][0]["thread_id"] == "a" and payload["open_reviews"][0]["scope_args"] == PR_53


def run_chooser(answers, threads):
    queue = iter(answers)
    output = io.StringIO()
    chooser = make_terminal_chooser(lambda prompt: next(queue), output)
    return chooser(threads), output.getvalue()


def test_terminal_chooser_returns_the_numbered_review():
    picked, output = run_chooser(["2"], [thread("a"), thread("b")])
    assert picked.thread_id == "b" and "1. a" in output and "2. b" in output


def test_terminal_chooser_cancels_on_blank_input():
    assert run_chooser([""], [thread("a")])[0] is None


def test_terminal_chooser_reprompts_on_invalid_input():
    picked, output = run_chooser(["9", "x", "1"], [thread("a")])
    assert picked.thread_id == "a" and output.count("Enter a number") == 2
