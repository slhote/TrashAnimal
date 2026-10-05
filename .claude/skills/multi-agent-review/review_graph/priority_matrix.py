PRIORITY_WEIGHTS: dict[str, dict[str, int]] = {
    "security": {"frontend": 10, "backend": 10, "security": 100, "testing": 10, "architecture": 20},
    "performance": {"frontend": 30, "backend": 50, "security": 5, "testing": 10, "architecture": 30},
    "accessibility": {"frontend": 100, "backend": 5, "security": 20, "testing": 30, "architecture": 10},
    "maintainability": {"frontend": 20, "backend": 20, "security": 10, "testing": 20, "architecture": 100},
    "testing": {"frontend": 10, "backend": 10, "security": 10, "testing": 100, "architecture": 20},
}

DEFAULT_WEIGHT = 1


def agent_weight(agent: str, category: str) -> int:
    short_name = agent.removesuffix("-reviewer")
    return PRIORITY_WEIGHTS.get(category, {}).get(short_name, DEFAULT_WEIGHT)
