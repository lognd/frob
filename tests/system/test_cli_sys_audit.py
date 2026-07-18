"""System (CLI end-to-end) coverage for `frob sys audit` (T-0115): check
the full per-family exhaustiveness conjunction and exit nonzero with a
named-gap summary when any part fails."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run

_CLEAN_MODEL = """\
module m
node evil : foreign
node api : trusted
flow f1 : evil -> api
"""


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(tmp_path: Path, model: str) -> Path:
    """A minimal frob-enabled repo: git init, empty ledger, one design file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "tickets.md").write_text("# Tickets\n")
    (repo / "design").mkdir()
    (repo / "design" / "m.strata").write_text(model)
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    return repo


class TestSysAuditCli:
    def test_clean_model_exits_zero(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path, _CLEAN_MODEL)
        r = run("sys", "audit", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "PROVED" in out

    def test_undischarged_capability_exits_nonzero_with_named_gap(
        self, tmp_path: Path
    ) -> None:
        model = """\
module m
node evil : foreign
node web : trusted {
    may "sql";
}
flow f1 : evil -> web
"""
        repo = _init_repo(tmp_path, model)
        r = run("sys", "audit", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "GAP" in out
        assert "CWE-89" in out

    def test_file_arg_fails(self, tmp_path: Path) -> None:
        """T-0163: `frob sys audit <file.strata>` used to silently join
        `design_dir` onto the file path (`<file>/design`), find nothing,
        and exit 0 with a vacuous PASS. It must now fail loudly and name
        the expected directory invocation instead."""
        repo = _init_repo(tmp_path, _CLEAN_MODEL)
        design_file = repo / "design" / "m.strata"
        r = run("sys", "audit", str(design_file), cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "PROVED" not in out
        assert str(design_file) in out
        assert "repo root" in out
        assert str(repo) in out
        assert "is a file" in out

    def test_no_design_dir_is_a_noop(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git("init", "-q", cwd=repo)
        _git("config", "user.email", "test@example.com", cwd=repo)
        _git("config", "user.name", "Test", cwd=repo)
        (repo / "tickets.md").write_text("# Tickets\n")
        _git("add", "-A", cwd=repo)
        _git("commit", "-q", "-m", "init", cwd=repo)
        r = run("sys", "audit", cwd=repo)
        assert r.returncode == 0
