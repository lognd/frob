"""Tests for CACHE001 (T-1520): a `@memoize_per_run` function's observed
read-set must be covered by its own parameters (declared cache-key
inputs). `TestMemoizedReadCoverage` covers the memoize_per_run shape
directly (the ticket's own acceptance floor); `TestT1454RegressionShape`
reproduces the T-1454 incident's read-a-lock-file-unconditionally shape as
a synthetic fixture."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates._cache_gate import cache_gate


# frob:ticket T-1520
# frob:waive DUP001 reason="the git-init/commit/write trio is the established \
# real-git-fixture idiom this test module family repeats (tests/test_gates.py, \
# tests/test_ticket_land.py, tests/test_ticket_work_and_land_finish.py and siblings \
# all carry equivalent copies, several under this same verbatim waiver) -- extracting \
# one repo-wide shared conftest helper is a real, independent cleanup outside this \
# ticket's scope, not something to fold into its land"
def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-1520
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- WIRE001's reachability scan skips test paths by design \
# (conftest.py::_install_stackdump_handler's WIRE001/T-1466 precedent, \
# tests/test_tickets_migration.py's _git_init precedent), so any helper reached only \
# from within its own test file always reads as unwired" follow_up="T-1490"
# frob:waive DUP001 reason="the git-init/commit/write trio is the established \
# real-git-fixture idiom this test module family repeats (tests/test_gates.py, \
# tests/test_ticket_land.py, tests/test_ticket_work_and_land_finish.py and siblings \
# all carry equivalent copies, several under this same verbatim waiver) -- extracting \
# one repo-wide shared conftest helper is a real, independent cleanup outside this \
# ticket's scope, not something to fold into its land"
def _git_init_tracked(root: Path) -> None:
    """A minimal git repo with everything staged/committed -- `cache_gate`
    scans `git ls-files`, so a file must be tracked to be scanned at all."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "base", "--allow-empty"], cwd=root, check=True
    )


# frob:ticket T-1520
class TestMemoizedReadCoverage:
    """The ticket's own acceptance floor: fire on an uncovered read, stay
    silent on a param-derived one."""

    # frob:ticket T-1520
    # frob:tests \
    # tests/test_cache_gate.py::TestMemoizedReadCoverage.test_uncovered_read_fires
    def test_uncovered_read_fires(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_cache_gate.py::cache_gate"""
        _write(
            tmp_path,
            "src/frob/_fixture_bad.py",
            "from frob.check._memo import memoize_per_run\n\n"
            "@memoize_per_run\n"
            "def compute(root):\n"
            '    return open("frob.lock").read()\n',
        )
        _git_init_tracked(tmp_path)
        violations = cache_gate(tmp_path)
        assert any(v.rule == "CACHE001" for v in violations), (
            f"expected CACHE001, got {[v.rule for v in violations]}"
        )

    # frob:ticket T-1520
    # frob:tests tests/test_cache_gate.py::TestMemoizedReadCoverage.test_silent_shapes
    @pytest.mark.parametrize(
        ("rel", "source"),
        [
            (
                "src/frob/_fixture_good.py",
                "from frob.check._memo import memoize_per_run\n\n"
                "@memoize_per_run\n"
                "def compute(root):\n"
                "    return (root / 'frob.lock').read_text()\n",
            ),
            (
                "src/frob/_fixture_plain.py",
                "def compute():\n    return open('frob.lock').read()\n",
            ),
        ],
        ids=["param-derived-read", "non-memoized-function"],
    )
    def test_silent_shapes(self, tmp_path: Path, rel: str, source: str) -> None:
        """frob:tests src/frob/gates/_cache_gate.py::cache_gate"""
        _write(tmp_path, rel, source)
        _git_init_tracked(tmp_path)
        violations = cache_gate(tmp_path)
        assert not any(v.rule == "CACHE001" for v in violations)


# frob:ticket T-1520
class TestT1454RegressionShape:
    """The real incident this rule exists to catch: a memoized computation
    reads `os.environ`/a lock file with no path derived from its own args
    at all -- exactly the "no tracked source digest changed" T-1454 shape."""

    # frob:ticket T-1520
    # frob:tests tests/test_cache_gate.py::TestT1454RegressionShape.test_env_read_fires
    def test_env_read_fires(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_cache_gate.py::cache_gate"""
        _write(
            tmp_path,
            "src/frob/_fixture_env.py",
            "import os\n"
            "from frob.check._memo import memoize_per_run\n\n"
            "@memoize_per_run\n"
            "def compute(root):\n"
            "    mode = os.environ.get('FROB_MODE')\n"
            "    return mode\n",
        )
        _git_init_tracked(tmp_path)
        violations = cache_gate(tmp_path)
        assert any(v.rule == "CACHE001" for v in violations)
