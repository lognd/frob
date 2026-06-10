"""
End-to-end tests for `frob dup`.
"""

import json

from tests.system.conftest import FIXTURES, run

DUP_PYTHON_DIR = FIXTURES / "dup_python"


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_zero_on_fixture():
    r = run("dup", str(DUP_PYTHON_DIR))
    assert r.returncode == 0


def test_exit_zero_on_clean_dir(tmp_path):
    (tmp_path / "a.py").write_text("def func_a(x: int) -> int:\n    return x + 1\n")
    r = run("dup", str(tmp_path))
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_text_shows_group():
    r = run("dup", str(DUP_PYTHON_DIR))
    assert (
        "Group" in r.stdout
        or "group" in r.stdout.lower()
        or "duplicate" in r.stdout.lower()
    )


def test_clean_dir_says_no_duplicates(tmp_path):
    (tmp_path / "unique.py").write_text(
        "def func_unique(x: int) -> int:\n    return x * 3\n"
    )
    r = run("dup", str(tmp_path))
    assert "no duplicates" in r.stdout.lower()


# ---------------------------------------------------------------------------
# --json flag
# ---------------------------------------------------------------------------


def test_json_exit_zero():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    assert r.returncode == 0


def test_json_is_valid():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    assert isinstance(data, dict)


def test_json_has_groups_key():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    assert "groups" in data


def test_json_groups_nonempty():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    assert len(data["groups"]) >= 1


def test_json_group_has_clone_type():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    grp = data["groups"][0]
    assert "clone_type" in grp
    assert grp["clone_type"] in ("exact", "renamed", "gapped")


def test_json_group_has_size_lines():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    grp = data["groups"][0]
    assert "size_lines" in grp
    assert grp["size_lines"] >= 6


def test_json_group_has_fragments():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    grp = data["groups"][0]
    assert "fragments" in grp
    assert len(grp["fragments"]) >= 2


def test_json_fragment_fields():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    frag = data["groups"][0]["fragments"][0]
    assert "file" in frag
    assert "start_line" in frag
    assert "end_line" in frag
    assert "symbol" in frag


def test_json_alpha_and_beta_in_same_group():
    r = run("dup", str(DUP_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    grp = data["groups"][0]
    files = [f["file"] for f in grp["fragments"]]
    assert any("alpha.py" in f for f in files)
    assert any("beta.py" in f for f in files)


def test_json_clean_dir_empty_groups(tmp_path):
    (tmp_path / "single.py").write_text(
        "def unique_func(x: int) -> int:\n    return x * 99\n"
    )
    r = run("dup", str(tmp_path), "--json")
    data = json.loads(r.stdout)
    assert data["groups"] == []


# ---------------------------------------------------------------------------
# --min-lines flag
# ---------------------------------------------------------------------------


def test_min_lines_100_no_groups():
    r = run("dup", str(DUP_PYTHON_DIR), "--min-lines", "100")
    assert r.returncode == 0
    assert "no duplicates" in r.stdout.lower()


def test_min_lines_100_json_empty_groups():
    r = run("dup", str(DUP_PYTHON_DIR), "--min-lines", "100", "--json")
    data = json.loads(r.stdout)
    assert data["groups"] == []
