"""T-0887: `frob ticket done-report --base-ref` must fail fast (seconds,
naming the unresolvable ref) when the named base ref does not exist in the
clone, rather than hanging -- and must behave unchanged when the ref does
exist. Each test is written to FAIL against the pre-T-0887 behavior (no
such check existed at all: `base_ref_resolvable` did not exist and
`set_done_report` passed an unvalidated `base_ref` straight through to
`compute_changed_lines`/the claims-capture callables) and PASS after it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.tickets import (
    Origin,
    TicketError,
    TicketKind,
    TicketSpec,
    base_ref_resolvable,
    new_ticket,
    set_done_report,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    # `-b main` pins the default branch name explicitly, matching the
    # sibling `test_tickets_live_tracker.py` convention -- a sandbox whose
    # ambient `git init.defaultBranch` is `master` must not accidentally
    # make "main" resolvable here.
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")


def _commit_all(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _spec(title: str) -> TicketSpec:
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)


class TestBaseRefResolvable:
    """Direct unit coverage of the fail-fast primitive `set_done_report`
    is built on."""

    def test_unresolvable_ref_in_a_real_repo_is_false(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_unresolva\
        # ble_ref_in_a_real_repo_is_false  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
        _commit_all(tmp_path, "init")
        assert base_ref_resolvable(tmp_path, "totally-made-up-ref") is False

    def test_resolvable_ref_is_true(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_resolvabl\
        # e_ref_is_true  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
        _commit_all(tmp_path, "init")
        assert base_ref_resolvable(tmp_path, "main") is True

    def test_non_git_root_is_none(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_non_git_r\
        # oot_is_none  # noqa: E501
        """A `root` that is not a git checkout at all is a DIFFERENT signal
        than an unresolvable ref -- `None` ("unknown"), never `False`
        ("unresolvable"), preserving the long-standing best-effort
        contract every non-git `set_done_report` caller already relies
        on (e.g. the bare-`tmp_path` tests in
        `tests/test_ticket_done_report_claims.py`)."""
        assert base_ref_resolvable(tmp_path, "main") is None


class TestSetDoneReportBaseRefFailsFast:
    def test_unresolvable_base_ref_returns_err_immediately(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast.te\
        # st_unresolvable_base_ref_returns_err_immediately  # noqa: E501
        """The acceptance criterion this ticket exists for: a clone with
        no local/remote-tracking `main` (here: any ref that plain does
        not exist) must fail `done-report --base-ref` with a clear,
        immediate `Err` naming the problem -- never hang."""
        _init_repo(tmp_path)
        (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
        _commit_all(tmp_path, "init")
        created = new_ticket(tmp_path, _spec("Base ref missing"))
        assert created.is_ok
        tid = created.danger_ok.id

        result = set_done_report(
            tmp_path,
            tid,
            why="did the thing",
            base_ref="no-such-ref-anywhere",
        )
        assert result.is_err
        assert result.danger_err is TicketError.BaseRefUnresolvable

    def test_resolvable_base_ref_behavior_unchanged(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast.te\
        # st_resolvable_base_ref_behavior_unchanged  # noqa: E501
        """GIVEN a repo where the base ref exists, `done-report` behavior
        is unchanged: it still succeeds and still renders a Changed
        block from the real diff."""
        _init_repo(tmp_path)
        (tmp_path / "a.txt").write_text("hi\n", encoding="utf-8")
        _commit_all(tmp_path, "init")
        _git(tmp_path, "branch", "base-tag")
        (tmp_path / "a.txt").write_text("hi again\n", encoding="utf-8")
        _commit_all(tmp_path, "second")

        created = new_ticket(tmp_path, _spec("Base ref present"))
        assert created.is_ok
        tid = created.danger_ok.id

        result = set_done_report(
            tmp_path,
            tid,
            why="did the thing",
            base_ref="base-tag",
        )
        assert result.is_ok
        assert "a.txt" in result.danger_ok.body

    def test_non_git_root_still_succeeds_best_effort(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast.te\
        # st_non_git_root_still_succeeds_best_effort  # noqa: E501
        """A non-git root (no `base_ref` signal available at all) keeps
        the pre-T-0887 best-effort behavior: `done-report` still
        succeeds, just with an empty Changed block, rather than being
        newly refused."""
        created = new_ticket(tmp_path, _spec("No git repo here"))
        assert created.is_ok
        tid = created.danger_ok.id

        result = set_done_report(tmp_path, tid, why="did the thing")
        assert result.is_ok
