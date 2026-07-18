"""
Scale and stress tests for the frob CLI.
All tests create large projects programmatically and run frob on them.
"""

import json
from pathlib import Path

from tests.system.conftest import run


def make_project(tmp_path: Path, n_files: int, n_functions_per_file: int) -> None:
    """Create n_files Python files each with n_functions_per_file functions."""
    for i in range(n_files):
        lines = [f"# file {i}"]
        for j in range(n_functions_per_file):
            lines += [
                f"def func_{i}_{j}(x: int, y: int) -> int:",
                f"    # implementation {j}",
                f"    result = x + y + {j}",
                "    return result",
                "",
            ]
        (tmp_path / f"module_{i}.py").write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# frob map scale
# ---------------------------------------------------------------------------


def test_map_50_files_json_lists_all(tmp_path):
    make_project(tmp_path, 50, 10)
    r = run("map", str(tmp_path), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert len(data["files"]) == 50


def test_map_50_files_total_tokens_positive(tmp_path):
    make_project(tmp_path, 50, 10)
    r = run("map", str(tmp_path), "--json")
    data = json.loads(r.stdout)
    total = sum(f["tokens"] for f in data["files"])
    assert total > 0


def test_map_50_files_all_basenames_present(tmp_path):
    make_project(tmp_path, 50, 10)
    r = run("map", str(tmp_path), "--json")
    data = json.loads(r.stdout)
    basenames = {Path(f["path"]).name for f in data["files"]}
    for i in range(50):
        assert f"module_{i}.py" in basenames


# ---------------------------------------------------------------------------
# frob xref scale
# ---------------------------------------------------------------------------


def test_xref_finds_func_in_large_project(tmp_path):
    make_project(tmp_path, 10, 5)
    r = run("xref", "func_0_0", str(tmp_path), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["symbol"] == "func_0_0"
    assert data["definition"] is not None
    assert "module_0.py" in data["definition"]["file"]


def test_xref_definition_line_is_correct(tmp_path):
    make_project(tmp_path, 10, 5)
    r = run("xref", "func_0_0", str(tmp_path), "--json")
    data = json.loads(r.stdout)
    # func_0_0 is the first function in module_0.py
    # line 1 is comment, line 2 is def func_0_0
    assert data["definition"]["line"] == 2


# ---------------------------------------------------------------------------
# frob dup scale
# ---------------------------------------------------------------------------


def test_dup_detects_duplicate_files(tmp_path):
    content = "\n".join(
        [
            "def shared_function(x: int, y: int) -> int:",
            "    result = x + y",
            "    intermediate = result * 2",
            "    final = intermediate - 1",
            "    return final",
            "",
            "def another_shared(s: str) -> str:",
            "    stripped = s.strip()",
            "    upper = stripped.upper()",
            "    return upper",
            "",
        ]
    )
    for i in range(20):
        (tmp_path / f"dup_{i}.py").write_text(content)
    r = run("dup", str(tmp_path), "--json", "--min-lines", "4")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert len(data["groups"]) >= 1


# ---------------------------------------------------------------------------
# frob arch scale
# ---------------------------------------------------------------------------


# frob:waive PERF001 reason="membership check runs once after the fixture-building loop above has finished, not inside it"
def test_arch_detects_deep_nesting_in_large_file(tmp_path):
    lines = ["def deep_func(data):"]
    indent = "    "
    for depth in range(8):
        lines.append(indent * (depth + 1) + f"if data[{depth}]:")
    lines.append(indent * 9 + "return True")
    # pad to 500 lines
    lines += ["    pass"] * (500 - len(lines))
    (tmp_path / "large.py").write_text("\n".join(lines) + "\n")
    r = run("arch", str(tmp_path), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    cats = [s["category"] for s in data["suggestions"]]
    assert "deep-nesting" in cats
