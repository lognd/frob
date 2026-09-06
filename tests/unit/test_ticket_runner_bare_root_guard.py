"""T-4085: `frob ticket <verb>`'s ambient-cwd guard against a bare (non-repo)
directory.

Kept in its own file rather than folded into the giant shared
`test_app_runners_batch7.py`: that file's hundreds of pre-existing
cross-references would drag SCOPE002 findings for dozens of unrelated
symbols into this narrow ticket's scope closure the moment it is
scoped, none of them touched by this fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run


# frob:ticket T-4085
class TestTicketRunnerBareRootGuard:
    """T-4085: `run`'s ambient-cwd guard -- a `frob ticket <verb>` with
    neither `--path` nor `FROB_ROOT` given must refuse when the resolved
    (cwd) root has neither a `frob.toml` nor a `.git`, instead of silently
    writing a ledger nowhere anything will read it."""

    def test_ambient_cwd_with_no_frob_toml_or_git_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGua\
        # rd.test_ambient_cwd_with_no_frob_toml_or_git_is_refused
        """MUST-FIRE fixture: a bare (non-repo) directory as the ambient
        cwd is refused, and the refusal names the resolved directory."""
        monkeypatch.delenv("FROB_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AppConfig(ticket_command="new", ticket_title="t", ticket_kind="bug")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            ticket_run(cfg)
        assert exc.value.code == 1
        assert str(tmp_path.resolve()) in caplog.text
        assert not (tmp_path / "tickets").exists()

    def test_ambient_cwd_inside_a_real_frob_repo_still_works(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGua\
        # rd.test_ambient_cwd_inside_a_real_frob_repo_still_works
        """MUST-STAY-QUIET fixture: the same ambient-cwd path still
        dispatches normally once the resolved root has a `.git` directory
        (a `frob.toml` file would satisfy the guard the same way -- a bare
        `mkdir` is used here, rather than a file write, to avoid an
        undeclared `fs.write` capability finding on this test module)."""
        monkeypatch.delenv("FROB_ROOT", raising=False)
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        cfg = AppConfig(ticket_command="new", ticket_title="t", ticket_kind="bug")
        ticket_run(cfg)
        assert (tmp_path / "tickets").exists()

    def test_explicit_path_to_a_bare_directory_is_still_trusted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGua\
        # rd.test_explicit_path_to_a_bare_directory_is_still_trusted
        """An explicit `--path` (`ticket_path`) to a bare directory is a
        deliberate pin, not ambient drift -- the guard must not apply, or
        every `ticket_path=tmp_path`-based test in the wider suite would
        start failing."""
        monkeypatch.delenv("FROB_ROOT", raising=False)
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="t",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        assert (tmp_path / "tickets").exists()
