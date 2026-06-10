"""
End-to-end tests for `frob cycle`.
"""

import json
from pathlib import Path

import pytest

from tests.system.conftest import run


@pytest.fixture
def no_cycle_dir(tmp_path):
    # linear chain: a imports b, b imports c, no cycle
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from c import something\n")
    (tmp_path / "c.py").write_text("x = 1\n")
    return tmp_path


@pytest.fixture
def cycle_dir(tmp_path):
    # a imports b, b imports a -> cycle
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from a import something\n")
    return tmp_path


@pytest.fixture
def deep_cycle_dir(tmp_path):
    # a -> b -> c -> a
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from c import something\n")
    (tmp_path / "c.py").write_text("from a import something\n")
    return tmp_path


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_no_cycle_exit_zero(no_cycle_dir):
    r = run("cycle", str(no_cycle_dir))
    assert r.returncode == 0


def test_cycle_exit_zero(cycle_dir):
    r = run("cycle", str(cycle_dir))
    assert r.returncode == 0


def test_deep_cycle_exit_zero(deep_cycle_dir):
    r = run("cycle", str(deep_cycle_dir))
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# No-cycle output
# ---------------------------------------------------------------------------


def test_no_cycle_says_no_cycles(no_cycle_dir):
    r = run("cycle", str(no_cycle_dir))
    assert "no cycle" in r.stdout.lower()


def test_no_cycle_does_not_say_cycle_detected(no_cycle_dir):
    r = run("cycle", str(no_cycle_dir))
    # should not say "cycle detected" or just "cycle" alone
    assert "cycle (" not in r.stdout.lower()


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def test_cycle_says_cycle(cycle_dir):
    r = run("cycle", str(cycle_dir))
    assert "cycle" in r.stdout.lower()


def test_cycle_mentions_a_py(cycle_dir):
    r = run("cycle", str(cycle_dir))
    assert "a.py" in r.stdout


def test_cycle_mentions_b_py(cycle_dir):
    r = run("cycle", str(cycle_dir))
    assert "b.py" in r.stdout


def test_deep_cycle_mentions_all_three(deep_cycle_dir):
    r = run("cycle", str(deep_cycle_dir))
    assert "a.py" in r.stdout
    assert "b.py" in r.stdout
    assert "c.py" in r.stdout


# ---------------------------------------------------------------------------
# --suggest flag
# ---------------------------------------------------------------------------


def test_suggest_cycle_exit_zero(cycle_dir):
    r = run("cycle", str(cycle_dir), "--suggest")
    assert r.returncode == 0


def test_suggest_output_contains_suggest(cycle_dir):
    r = run("cycle", str(cycle_dir), "--suggest")
    assert "suggest" in r.stdout.lower()


def test_suggest_no_cycle_exit_zero(no_cycle_dir):
    r = run("cycle", str(no_cycle_dir), "--suggest")
    assert r.returncode == 0
