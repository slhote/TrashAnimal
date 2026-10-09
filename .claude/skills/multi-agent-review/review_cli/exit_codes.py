from __future__ import annotations

EXIT_CLEAR, EXIT_REJECTED, EXIT_BLOCKED, EXIT_PAUSED, EXIT_USER_INPUT_NEEDED = 0, 1, 2, 3, 4
EXIT_USAGE = 64


def exit_code_for(result: dict) -> int:
    if result.get("verdict") == "BLOCK_MERGE":
        return EXIT_BLOCKED
    if result.get("verdict") == "REQUIRES_APPROVAL" and result.get("approval_decision") != "approved":
        return EXIT_REJECTED
    return EXIT_CLEAR
