from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentSpec:
    name: str
    description: str
    tools: list[str]
    prompt: str
    model: str | None = None


def parse_agent_markdown(text: str) -> AgentSpec:
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("agent file is missing frontmatter")
    closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if closing is None:
        raise ValueError("agent file frontmatter is not closed")

    fields: dict[str, str] = {}
    for line in lines[1:closing]:
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()

    return AgentSpec(
        name=fields["name"],
        description=fields.get("description", ""),
        tools=[tool.strip() for tool in fields.get("tools", "").split(",") if tool.strip()],
        prompt="\n".join(lines[closing + 1 :]).strip(),
        model=fields.get("model") or None,
    )


def load_agent(agents_dir: Path, name: str) -> AgentSpec:
    return parse_agent_markdown((agents_dir / f"{name}.md").read_text(encoding="utf-8"))
