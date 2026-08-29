"""
End-to-end tests for `frob cycle`.
"""

import pytest

from tests.system.conftest import git, git_init_and_config, run


def _commit_all(path):
    """Stage and commit everything under `path` (T-2943: `frob cycle`'s
    directory walk needs real, committed content -- an initialized-but-
    empty repo still measures 0 nodes)."""
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", "init", cwd=path)


@pytest.fixture
def no_cycle_dir(tmp_path):
    # linear chain: a imports b, b imports c, no cycle
    # T-2943: git-init tmp_path so `_resolve_project_root` (T-2588) has a
    # repo boundary to resolve `frob cycle <tmp_path>` against -- without
    # this, `git -C tmp_path rev-parse --show-toplevel` fails "not a git
    # repository" (exit 128, unrelated to platform/safe.directory -- this
    # reproduces identically on Linux and macOS) and `frob cycle` correctly
    # refuses (exit 2) rather than silently measuring the wrong tree.
    git_init_and_config(tmp_path)
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from c import something\n")
    (tmp_path / "c.py").write_text("x = 1\n")
    _commit_all(tmp_path)
    return tmp_path


@pytest.fixture
def cycle_dir(tmp_path):
    # a imports b, b imports a -> cycle
    # T-2943: see no_cycle_dir's comment -- same git-init requirement.
    git_init_and_config(tmp_path)
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from a import something\n")
    _commit_all(tmp_path)
    return tmp_path


@pytest.fixture
def deep_cycle_dir(tmp_path):
    # a -> b -> c -> a
    # T-2943: see no_cycle_dir's comment -- same git-init requirement.
    git_init_and_config(tmp_path)
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from c import something\n")
    (tmp_path / "c.py").write_text("from a import something\n")
    _commit_all(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_no_cycle_exit_zero(no_cycle_dir):
    r = run("cycle", str(no_cycle_dir))
    assert r.returncode == 0


def test_cycle_exit_one(cycle_dir):
    # T-2968: frob.app.cycle_runner.run's own docstring documents exit 1
    # (not 0) when a real cycle is found -- this fixture deliberately
    # contains one, so the CLI's contract-correct exit code is 1.
    r = run("cycle", str(cycle_dir))
    assert r.returncode == 1


def test_deep_cycle_exit_one(deep_cycle_dir):
    # T-2968: see test_cycle_exit_one's comment -- same contract.
    r = run("cycle", str(deep_cycle_dir))
    assert r.returncode == 1


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


def test_suggest_cycle_exit_one(cycle_dir):
    # T-2968: --suggest does not change the exit-code contract -- a real
    # cycle still exits 1, matching cycle_runner.run's documented contract.
    r = run("cycle", str(cycle_dir), "--suggest")
    assert r.returncode == 1


def test_suggest_output_contains_suggest(cycle_dir):
    r = run("cycle", str(cycle_dir), "--suggest")
    assert "suggest" in r.stdout.lower()


def test_suggest_no_cycle_exit_zero(no_cycle_dir):
    r = run("cycle", str(no_cycle_dir), "--suggest")
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# T-3350: import-time vs. deferred edges -- positive control
#
# A deferred import (function/method/class-body-local, or inside
# `if TYPE_CHECKING:`) cannot deadlock a real import at module-load time --
# deferring is the standard remedy FOR a cycle, not a second occurrence of
# one -- so `frob cycle` must NOT fire when the only edges closing a would-
# be cycle are deferred, and must STILL fire on a genuine top-level cycle.
# Both fixtures below are as close to identical as possible (same two
# modules, same names) so the only variable is import placement.
# ---------------------------------------------------------------------------


@pytest.fixture
def toplevel_two_module_cycle_dir(tmp_path):
    """a <-> b, both imports at module level: a REAL import-time cycle."""
    git_init_and_config(tmp_path)
    (tmp_path / "a.py").write_text("from b import something\n\nsomething = 1\n")
    (tmp_path / "b.py").write_text("from a import something\n\nsomething = 1\n")
    _commit_all(tmp_path)
    return tmp_path


@pytest.fixture
def deferred_only_two_module_cycle_dir(tmp_path):
    """a <-> b, both imports deferred (function-local / TYPE_CHECKING):
    NOT a real import-time cycle -- this is the exact deferred-import
    remedy for the fixture above, applied to both sides."""
    git_init_and_config(tmp_path)
    (tmp_path / "a.py").write_text(
        "from typing import TYPE_CHECKING\n\n"
        "if TYPE_CHECKING:\n"
        "    from b import something\n\n"
        "def use_b():\n"
        "    from b import something\n"
        "    return something\n"
    )
    (tmp_path / "b.py").write_text(
        "def use_a():\n    from a import use_b\n    return use_b\n"
    )
    _commit_all(tmp_path)
    return tmp_path


def test_toplevel_two_module_cycle_fires(toplevel_two_module_cycle_dir):
    # frob:tests src/frob/app/cycle_runner.py::run kind="e2e"
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="e2e"
    """A genuine top-level a<->b import cycle is still caught (CYCLE001's
    positive control -- T-3350)."""
    r = run("cycle", str(toplevel_two_module_cycle_dir))
    assert r.returncode == 1
    assert "cycle (" in r.stdout.lower()


def test_deferred_only_cycle_does_not_fire(deferred_only_two_module_cycle_dir):
    # frob:tests src/frob/app/cycle_runner.py::run kind="e2e"
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="e2e"
    """The SAME shape of a<->b cycle, but every edge is deferred (function-
    local or `if TYPE_CHECKING:`) -- CYCLE001 must not fire, because
    deferring an import is the standard remedy FOR an import cycle, not a
    second occurrence of one (T-3350's negative control)."""
    r = run("cycle", str(deferred_only_two_module_cycle_dir))
    assert r.returncode == 0
    assert "no cycle" in r.stdout.lower()
