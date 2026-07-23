"""T-0877: `frob scaffold pool warm/lease/status` end-to-end -- the real
CLI subprocess, wired onto the T-0738 `frob.scaffold._pool` API. Exercised
against throwaway `tmp_path` git repos only (same safety rule as
`tests/system/test_scaffold_pool.py`): `warm`/`lease` really do run `git
worktree add`/`git merge`, never point this at the real `frob` clone."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]


# frob:ticket T-0877
def _git(*args: str, cwd: Path) -> None:
    """Run a git command in `cwd`, raising on failure -- setup helper only."""
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


# frob:ticket T-0877
def _repo(tmp_path: Path) -> Path:
    """A minimal one-commit git repo at `tmp_path/repo` with a `main`
    branch and a trivial `Makefile` with a no-op `core:` target -- the
    CLI has no way to inject a fake `build_fn` (it always runs the real
    default, `make core`, per worktree), so a fast, always-succeeding
    `core:` target here stands in for a real cargo/maturin compile,
    exactly the way `tests/system/test_cli_scaffold_apply.py`'s fixtures
    stand in for a real project."""
    root = tmp_path / "repo"
    root.mkdir()
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "README.md").write_text("hello\n")
    (root / "Makefile").write_text("core:\n\t@true\n")
    _git("add", "README.md", "Makefile", cwd=root)
    _git("commit", "-q", "-m", "initial", cwd=root)
    return root


# frob:ticket T-0877
class TestScaffoldPoolCli:
    """End-to-end CLI coverage for `frob scaffold pool` (T-0877)."""

    # frob:ticket T-0877
    # frob:tests tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli.test_warm_lease_status_roundtrip  # noqa: E501
    def test_warm_lease_status_roundtrip(self, tmp_path: Path) -> None:
        """`pool warm 2` fills two ready slots; `pool status` lists them;
        `pool lease` hands out one (removing it from status) and prints a
        real worktree path."""
        root = _repo(tmp_path)

        warm = subprocess.run(
            FROB + ["scaffold", "pool", "warm", "2"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        out = warm.stdout + warm.stderr
        assert warm.returncode == 0, out
        assert "0:" in out
        assert "1:" in out
        assert "ready=True" in out

        status = subprocess.run(
            FROB + ["scaffold", "pool", "status"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        status_out = status.stdout + status.stderr
        assert status.returncode == 0, status_out
        assert "0:" in status_out
        assert "1:" in status_out

        lease = subprocess.run(
            FROB + ["scaffold", "pool", "lease"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        lease_out = lease.stdout + lease.stderr
        assert lease.returncode == 0, lease_out
        # T-0877: the leased path is the only stdout/stderr line that
        # resolves to a real directory -- a concurrent background refill
        # thread (lease_worktree's own refill=True default) can interleave
        # its own log lines around it, so picking "the last line" alone is
        # not reliable; find the one line that actually is a directory.
        candidate_lines = [ln for ln in lease_out.splitlines() if ln.strip()]
        dir_lines = [ln for ln in candidate_lines if Path(ln.strip()).is_dir()]
        assert dir_lines, lease_out
        leased_path = dir_lines[0].strip()

        status_after = subprocess.run(
            FROB + ["scaffold", "pool", "status"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        status_after_out = status_after.stdout + status_after.stderr
        assert status_after.returncode == 0, status_after_out
        # Slot 0 was leased out; only slot 1 (and slot 0's background
        # refill, which may or may not have completed yet) can appear --
        # the leased path itself must not still be listed as a ready
        # pool entry.
        assert leased_path not in status_after_out

    # frob:ticket T-0877
    # frob:tests tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli.test_lease_on_empty_pool_fails  # noqa: E501
    def test_lease_on_empty_pool_fails(self, tmp_path: Path) -> None:
        """`pool lease` against a repo with no warmed pool reports the
        `PoolError.Empty` failure and a nonzero exit, not a silent no-op."""
        root = _repo(tmp_path)

        lease = subprocess.run(
            FROB + ["scaffold", "pool", "lease"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        out = lease.stdout + lease.stderr
        assert lease.returncode != 0
        assert "pool-lease failed" in out
