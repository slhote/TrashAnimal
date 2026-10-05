from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from pydantic import BaseModel

from .agents_loader import AgentSpec
from .runner import AgentRunError, AgentRunner, RunLimits
from .state import Failure, Usage


@dataclass
class ExecutionOutcome:
    output: BaseModel | None = None
    failure: Failure | None = None
    usage: list[Usage] = field(default_factory=list)


async def execute_with_retries(
    runner: AgentRunner,
    spec: AgentSpec,
    prompt: str,
    output_model: type[BaseModel],
    limits: RunLimits,
    cwd: str,
    node: str,
) -> ExecutionOutcome:
    outcome = ExecutionOutcome()
    reason = "no attempts made"

    for _ in range(max(limits.max_attempts, 1)):
        try:
            async with asyncio.timeout(limits.timeout_seconds):
                result = await runner.run(spec, prompt, output_model, limits, cwd)
        except TimeoutError:
            reason = f"timed out after {limits.timeout_seconds:.0f}s"
            continue
        except AgentRunError as error:
            reason = str(error)
            outcome.usage.append(
                {"node": node, "agent": spec.name, "cost_usd": error.cost_usd, "turns": error.turns}
            )
            if not error.retryable:
                break
            continue
        except Exception as error:
            reason = f"{type(error).__name__}: {error}"
            continue

        outcome.usage.append({"node": node, "agent": spec.name, "cost_usd": result.cost_usd, "turns": result.turns})
        outcome.output = result.output
        return outcome

    outcome.failure = {"agent": spec.name, "reason": reason}
    return outcome
