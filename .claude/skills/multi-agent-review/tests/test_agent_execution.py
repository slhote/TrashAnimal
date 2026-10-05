import asyncio

from conftest import FakeRunner
from review_graph.agent_execution import execute_with_retries
from review_graph.agents_loader import AgentSpec
from review_graph.runner import RunLimits
from review_graph.state import ReviewerOutput

SPEC = AgentSpec(name="slow-reviewer", description="", tools=[], prompt="")


class SlowRunner(FakeRunner):
    async def run(self, spec, prompt, output_model, limits, cwd):
        await asyncio.sleep(1)
        return await super().run(spec, prompt, output_model, limits, cwd)


def test_slow_attempt_times_out_and_is_recorded_as_a_failure():
    limits = RunLimits(timeout_seconds=0.05, max_attempts=2)
    outcome = asyncio.run(execute_with_retries(SlowRunner(), SPEC, "p", ReviewerOutput, limits, ".", "reviewer"))
    assert outcome.output is None and "timed out" in outcome.failure["reason"]


def test_retryable_failure_is_attempted_again_but_limit_errors_are_not():
    runner = FakeRunner(failing={"slow-reviewer"})
    outcome = asyncio.run(execute_with_retries(runner, SPEC, "p", ReviewerOutput, RunLimits(max_attempts=3), ".", "reviewer"))
    assert runner.calls == ["slow-reviewer"] and outcome.failure["reason"] == "simulated failure"
    assert outcome.usage[0]["cost_usd"] == 0.05
