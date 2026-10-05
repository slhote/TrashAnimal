from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .agents_loader import AgentSpec

OutputModel = TypeVar("OutputModel", bound=BaseModel)

READ_ONLY_BASH = [
    "Bash(git diff:*)",
    "Bash(git show:*)",
    "Bash(git log:*)",
    "Bash(git status:*)",
    "Bash(git rev-parse:*)",
    "Bash(git branch --show-current)",
    "Bash(gh pr diff:*)",
    "Bash(gh pr view:*)",
]
FORBIDDEN_TOOLS = [
    "Edit",
    "Write",
    "NotebookEdit",
    "Bash(git checkout:*)",
    "Bash(git switch:*)",
    "Bash(git reset:*)",
    "Bash(git stash:*)",
    "Bash(git clean:*)",
    "Bash(git restore:*)",
]


@dataclass
class RunLimits:
    max_turns: int = 30
    max_budget_usd: float = 2.0
    timeout_seconds: float = 900.0
    max_attempts: int = 2


@dataclass
class RunResult:
    output: BaseModel
    cost_usd: float
    turns: int


class AgentRunError(Exception):
    def __init__(self, reason: str, cost_usd: float = 0.0, turns: int = 0, retryable: bool = True):
        super().__init__(reason)
        self.cost_usd = cost_usd
        self.turns = turns
        self.retryable = retryable


class AgentRunner(Protocol):
    async def run(
        self, spec: AgentSpec, prompt: str, output_model: type[OutputModel], limits: RunLimits, cwd: str
    ) -> RunResult: ...


def read_only_tool_options(spec: AgentSpec) -> tuple[list[str], list[str]]:
    base_tools = [tool for tool in spec.tools if tool not in {"Edit", "Write", "NotebookEdit"}]
    allowed = [tool for tool in base_tools if tool != "Bash"]
    if "Bash" in base_tools:
        allowed.extend(READ_ONLY_BASH)
    return base_tools, allowed


def extract_json_object(text: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{") : text.rfind("}") + 1]
    return json.loads(candidate)


class SdkAgentRunner:
    async def run(
        self, spec: AgentSpec, prompt: str, output_model: type[OutputModel], limits: RunLimits, cwd: str
    ) -> RunResult:
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

        base_tools, allowed_tools = read_only_tool_options(spec)
        options = ClaudeAgentOptions(
            system_prompt=spec.prompt,
            tools=base_tools,
            allowed_tools=allowed_tools,
            disallowed_tools=FORBIDDEN_TOOLS,
            permission_mode="dontAsk",
            max_turns=limits.max_turns,
            max_budget_usd=limits.max_budget_usd,
            cwd=cwd,
            model=spec.model,
            setting_sources=["project"],
            output_format={"type": "json_schema", "schema": output_model.model_json_schema()},
        )

        result: ResultMessage | None = None
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result = message

        if result is None:
            raise AgentRunError("agent produced no result")

        cost, turns = result.total_cost_usd or 0.0, result.num_turns
        if result.subtype in {"error_max_turns", "error_max_budget_usd"}:
            raise AgentRunError(f"limit reached: {result.subtype}", cost, turns, retryable=False)
        if result.is_error or result.subtype != "success":
            raise AgentRunError(f"agent error: {result.subtype}", cost, turns)

        try:
            payload = result.structured_output or extract_json_object(result.result or "")
            return RunResult(output_model.model_validate(payload), cost, turns)
        except ValueError as error:
            raise AgentRunError(f"invalid reviewer output: {error}", cost, turns) from error
