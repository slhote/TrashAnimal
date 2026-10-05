from __future__ import annotations

import re

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

LineRanges = list[tuple[int, int]]


def parse_diff_hunks(diff_text: str) -> dict[str, LineRanges]:
    hunks: dict[str, LineRanges] = {}
    current_file: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            target = line[4:].split("\t")[0].strip()
            current_file = None if target == "/dev/null" else target.removeprefix("b/")
            if current_file is not None:
                hunks.setdefault(current_file, [])
            continue
        match = HUNK_HEADER.match(line)
        if match and current_file is not None:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            hunks[current_file].append((start, start + max(count, 1) - 1))
    return hunks
