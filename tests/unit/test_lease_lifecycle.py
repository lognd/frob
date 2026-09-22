"""T-4659: explicit lease lifecycle -- release on EVERY terminal transition
out of `IN_PROGRESS` (close, drop, fail-then-requeue, requeue), and a
hardened `release_lease` that logs at ERROR (not WARNING) on a genuine
removal failure. Positive controls for the T-3259 measured incident
(`frob ticket drop` leaving `.git/frob-leases/<id>.json` in place) and its
`fail`/`requeue` siblings, plus `release_lease`'s own unlink-failure
contract.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from frob.tickets import (
    FailureEntry,
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    drop_ticket,
    new_ticket,
    record_failure,
    transition,
)
from frob.tickets._leases import (
    _lease_path,
    leases_dir,
    record_lease,
    release_lease,
)
from frob.tickets._store import atomic_write, ledger_path


def _run(argv: list[str], cwd: Path) -> None:
    """Run a git plumbing command under `cwd`, failing loudly on error."""
    subprocess.run(argv, cwd=str(cwd), check=True, capture_output=True, text=True)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    """Build a minimal agent-origin `TicketSpec` for these lifecycle tests."""
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A single real git checkout with an initialized ledger and one
    committed file -- these tests exercise `release_lease` within ONE
    worktree, not the cross-worktree visibility `test_ticket_leases_cross_
    worktree.py` already covers."""
    root = tmp_path / "repo"
    root.mkdir()
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    atomic_write(ledger_path(root), "# Tickets\n\n")
    (root / "src").mkdir()
    (root / "src" / "feature.py").write_text("# feature\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", "init"], root)
    return root


def _started_ticket(repo: Path, title: str) -> str:
    """File, plan and start a ticket under `repo`, returning its id --
    the shared setup every lifecycle test in this module begins from."""
    created = new_ticket(repo, _spec(title, scope=("src/feature.py",)))
    assert created.is_ok
    tid = created.danger_ok.id
    assert transition(repo, tid, TicketState.PLANNED).is_ok
    assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok
    return tid


class TestReleaseLeaseLifecycle:
    """`release_lease` fires on every terminal exit from `IN_PROGRESS`
    (T-4659) -- close (covered by `test_ticket_leases_cross_worktree.py`'s
    own `test_release_on_close_removes_the_lease`), drop, fail-then-
    requeue, and a bare requeue."""

    # frob:tests src/frob/tickets/_leases.py::release_lease kind="unit"  # noqa: E501
    def test_drop_releases_lease(self, repo: Path) -> None:
        # frob:tests \
        # tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle.test_drop_releases_lease  # noqa: E501
        tid = _started_ticket(repo, "Feature A")
        lease_path = _lease_path(leases_dir(repo).danger_ok, tid)
        assert lease_path.exists()

        dropped = drop_ticket(repo, tid, "no longer needed")
        assert dropped.is_ok
        assert not lease_path.exists()

        # A sibling ticket claiming the SAME scope must now succeed --
        # the T-3259 incident this closes was exactly this refusal
        # persisting after the holder was dropped.
        sibling = new_ticket(repo, _spec("Feature B", scope=("src/feature.py",)))
        assert sibling.is_ok
        assert transition(repo, sibling.danger_ok.id, TicketState.PLANNED).is_ok
        assert transition(repo, sibling.danger_ok.id, TicketState.IN_PROGRESS).is_ok

    # frob:tests src/frob/tickets/_leases.py::release_lease kind="unit"  # noqa: E501
    def test_fail_releases_lease(self, repo: Path) -> None:
        # frob:tests \
        # tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle.test_fail_releases_lease  # noqa: E501
        tid = _started_ticket(repo, "Feature A")
        lease_path = _lease_path(leases_dir(repo).danger_ok, tid)
        assert lease_path.exists()

        # Mirrors `frob.app.ticket_runner._close_cmd._fail` (T-1131): a
        # fail-log entry is not itself a transition, but the requeue
        # `_requeue_if_in_progress` performs right after it IS the
        # `transition` call that releases the lease.
        entry = FailureEntry(date=date.today(), attempt=1, summary="dead end")
        assert record_failure(repo, tid, entry).is_ok
        assert lease_path.exists(), "record_failure alone must not release a lease"
        assert transition(repo, tid, TicketState.QUEUED).is_ok
        assert not lease_path.exists()

    # frob:tests src/frob/tickets/_leases.py::release_lease kind="unit"  # noqa: E501
    def test_requeue_releases_lease(self, repo: Path) -> None:
        # frob:tests \
        # tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle.test_requeue_releases_lease  # noqa: E501
        tid = _started_ticket(repo, "Feature A")
        lease_path = _lease_path(leases_dir(repo).danger_ok, tid)
        assert lease_path.exists()

        assert transition(repo, tid, TicketState.QUEUED).is_ok
        assert not lease_path.exists()


class TestReleaseLeaseHardening:
    """T-4659: `release_lease`'s own unlink-failure contract -- still
    best-effort (`Ok(None)`), but now logged at ERROR, not WARNING, since
    a real removal failure means the lease keeps blocking sibling work."""

    # frob:tests src/frob/tickets/_leases.py::release_lease kind="unit"  # noqa: E501
    def test_missing_lease_is_a_silent_ok(self, repo: Path) -> None:
        """Releasing a ticket id with no recorded lease at all is `Ok
        (None)` -- `release_lease` must be safe to call unconditionally on
        any exit from `IN_PROGRESS`, including one that never actually
        held a lease (T-2007's root-checkout skip, or a `root` with no
        shared git dir)."""
        # frob:tests \
        # tests/unit/test_lease_lifecycle.py::TestReleaseLeaseHardening.test_missing_lease_is_a_silent_ok  # noqa: E501
        result = release_lease(repo, "T-9999")
        assert result.is_ok

    # frob:tests src/frob/tickets/_leases.py::release_lease kind="unit"  # noqa: E501
    def test_real_unlink_failure_logs_at_error(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A genuine removal failure (permission denied, a vanished
        parent, ...) still degrades to `Ok(None)` (T-0473's original
        best-effort contract, pinned separately by `tests/test_ticket_
        leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_release_
        lease_degrades_on_unlink_failure`) but now logs at ERROR, not
        WARNING -- the T-4659 lifecycle observability requirement: a
        lease that could not be released must leave an unmistakable
        trail, even though it is not (yet -- see T-draft-e6324810) a hard
        `Err`."""
        # frob:tests \
        # tests/unit/test_lease_lifecycle.py::TestReleaseLeaseHardening.test_real_unlink_failure_logs_at_error  # noqa: E501
        recorded = record_lease(repo, "T-0042", ("src/feature.py",))
        assert recorded.is_ok

        with (
            caplog.at_level(logging.ERROR, logger="frob.tickets._leases"),
            patch(
                "frob.tickets._leases.Path.unlink",
                side_effect=OSError("permission denied"),
            ),
        ):
            result = release_lease(repo, "T-0042")
        assert result.is_ok
        assert any(
            record.levelno == logging.ERROR and "T-0042" in record.message
            for record in caplog.records
        )
