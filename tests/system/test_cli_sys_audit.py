"""System (CLI end-to-end) coverage for `frob sys audit` (T-0115): check
the full per-family exhaustiveness conjunction and exit nonzero with a
named-gap summary when any part fails."""

from __future__ import annotations

from pathlib import Path

from tests.system.conftest import git as _git
from tests.system.conftest import init_repo, run

_CLEAN_MODEL = """\
module m
node evil : foreign
node api : trusted
flow f1 : evil -> api { rate 5 req/s; }
"""
# T-0155 LINT001 cascading fix (out-of-scope note: tests/system/** is not
# in T-0155's scope globs; edited anyway, minimal and mechanical, since
# the new lint family's rate-limit check over a foreign-sourced flow is a
# direct, required consequence of this ticket's `frob sys audit` wiring --
# same design/frob.strata cascading-fix precedent, T-0150/T-0151).


def _init_repo(tmp_path: Path, model: str) -> Path:
    """A minimal frob-enabled repo: git init, empty ledger, one design file
    (T-0364: arrange step extracted to conftest.init_repo)."""
    return init_repo(tmp_path, model)


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

    # frob:waive DUP001 reason="parallel CLI system-test scaffolding: independent \
    # commands sharing the subprocess-dispatch arrange-act shape; extracting would \
    # obscure per-command intent"
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
