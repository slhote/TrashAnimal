from pathlib import Path

from review_graph.agents_loader import load_agent, parse_agent_markdown
from review_graph.diff_parser import parse_diff_hunks
from review_graph.runner import extract_json_object, read_only_tool_options

AGENTS_DIR = Path(__file__).resolve().parents[3] / "agents"

DIFF = """diff --git a/TrashAnimal/A.cs b/TrashAnimal/A.cs
--- a/TrashAnimal/A.cs
+++ b/TrashAnimal/A.cs
@@ -10,0 +11,3 @@ class A
@@ -20 +25 @@
diff --git a/old.cs b/old.cs
--- a/old.cs
+++ /dev/null
@@ -1,4 +0,0 @@
"""


def test_diff_hunks_are_parsed_per_file_and_deleted_files_skipped():
    hunks = parse_diff_hunks(DIFF)
    assert hunks == {"TrashAnimal/A.cs": [(11, 13), (25, 25)]}


def test_agent_frontmatter_is_parsed():
    spec = parse_agent_markdown("---\nname: x\ndescription: a: b\ntools: Read, Grep, Bash\n---\n\nBody text\n")
    assert spec.name == "x" and spec.description == "a: b"
    assert spec.tools == ["Read", "Grep", "Bash"] and spec.prompt == "Body text"


def test_real_agent_files_load():
    for name in ["frontend-reviewer", "backend-reviewer", "security-reviewer", "testing-reviewer", "architecture-reviewer"]:
        spec = load_agent(AGENTS_DIR, name)
        assert spec.name == name and spec.prompt


def test_bash_is_narrowed_to_read_only_patterns_and_edit_tools_are_removed():
    spec = parse_agent_markdown("---\nname: x\ntools: Read, Edit, Bash\n---\nbody")
    base, allowed = read_only_tool_options(spec)
    assert "Edit" not in base and "Bash" in base
    assert "Bash" not in allowed and "Bash(git diff:*)" in allowed and "Bash(git checkout:*)" not in allowed


def test_json_is_extracted_from_fenced_or_bare_text():
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json_object('here: {"a": 2} done') == {"a": 2}
