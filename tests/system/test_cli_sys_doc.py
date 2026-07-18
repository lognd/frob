"""System (CLI end-to-end) coverage for `frob sys doc` (T-0085): render the
per-family threat-catalog audit matrix from a small design model."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run

_MODEL = """\
module m
node evil : foreign
node api : trusted
flow f1 : evil -> api
"""


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    """A minimal frob-enabled repo: git init, empty ledger, one small
    design file with no fired capability obligations (the surface grammar
    cannot express `may` atoms yet, T-0132) -- enough to exercise the
    matrix's catalog-entries-always-listed shape end to end."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "tickets.md").write_text("# Tickets\n")
    (repo / "design").mkdir()
    (repo / "design" / "m.strata").write_text(_MODEL)
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    return repo


class TestSysDocCli:
    def test_renders_matrix_for_default_view(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        r = run("sys", "doc", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "# Audit matrix -- view 'owasp-top-10'" in out
        assert "## security" in out
        assert "| CWE-79 |" in out

    def test_unknown_view_exits_nonzero(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        r = run("sys", "doc", "--view", "no-such-view", cwd=repo)
        assert r.returncode != 0

    def test_no_design_dir_is_a_noop(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git("init", "-q", cwd=repo)
        _git("config", "user.email", "test@example.com", cwd=repo)
        _git("config", "user.name", "Test", cwd=repo)
        (repo / "tickets.md").write_text("# Tickets\n")
        _git("add", "-A", cwd=repo)
        _git("commit", "-q", "-m", "init", cwd=repo)
        r = run("sys", "doc", cwd=repo)
        assert r.returncode == 0
