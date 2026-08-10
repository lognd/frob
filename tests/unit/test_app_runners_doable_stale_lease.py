"""T-1876: `frob ticket doable` must FLAG (never silently hide, never
auto-release) a lease whose holding worktree looks dead -- a lease
survives its agent's death with no liveness check today, and blocks every
ticket in its scope indefinitely (the measured 2026-08-08 incident: a
lease recorded hours after its worktree's own last commit kept blocking
five other tickets, with `doable` presenting it identically to live
work).

`_stale_lease_reasons` (`frob.app.ticket_runner._query`) is the
read-only surfacing half of the fix: it reuses `lease_staleness_reason`
(T-1806, already used by `frob worktree release-lease`) rather than
inventing a second liveness signal, and proves BOTH directions -- a dead
holder's lease is reported stale, and a live holder's lease is NOT (the
assertion that stops this from becoming a corruption bug: a
too-eager staleness check would let two worktrees mutate the same scope
at once, T-1868's failure mode)."""

# frob:ticket T-1876

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.app.ticket_runner._query import (
    _render_unlanded_branch_work_summary,
    _stale_lease_reasons,
)
from frob.tickets._leases import LEASE_TTL_SECONDS, _LeaseRecord, leases_dir


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with a real git history and an initialized ledger,
    same shape as `tests/test_ticket_leases.py`'s own `repo` fixture."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# feature\n")
    ticket_run(
        AppConfig(
            ticket_command="new",
            ticket_path=main_repo,
            ticket_title="feature ticket",
            ticket_kind="docs",
            ticket_scope=["src/feature.py"],
            ticket_body="## Done report\n\nDone.\n",
        )
    )
    _commit_all(main_repo, "init: ticket + ledger committed")
    return main_repo


@pytest.fixture
def second_worktree(repo: Path) -> Path:
    """A second linked `git worktree` of `repo`, branched from the SAME
    commit `repo` is on -- the real double-dispatch shape."""
    wt = repo.parent / "wt"
    _run(["git", "worktree", "add", "-b", "feature-wt", str(wt)], repo)
    return wt


def _write_lease(
    root: Path, ticket_id: str, worktree: Path, *, recorded_at: str
) -> None:
    resolved = leases_dir(root)
    assert resolved.is_ok
    leases_root = resolved.danger_ok
    leases_root.mkdir(parents=True, exist_ok=True)
    record = _LeaseRecord(
        ticket_id=ticket_id,
        scope=("src/feature.py",),
        worktree=str(worktree),
        branch="feature-wt",
        recorded_at=recorded_at,
    )
    (leases_root / f"{ticket_id}.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


class TestStaleLeaseReasons:
    def test_dead_holder_flagged_with_reason(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons.test\
        # _dead_holder_flagged_with_reason
        # T-0001 is a real ticket in `repo`'s own ledger (per the `repo`
        # fixture) -- the holder-dead check requires the ticket id to
        # still exist in the ledger, only its lease's `recorded_at` to be
        # long past `LEASE_TTL_SECONDS` and its worktree to hold no live
        # process, matching the real dead-agent shape T-1876 measured.
        stale_time = (
            datetime.now(UTC) - timedelta(seconds=LEASE_TTL_SECONDS + 60)
        ).isoformat()
        _write_lease(repo, "T-0001", second_worktree, recorded_at=stale_time)

        reasons = _stale_lease_reasons(repo)

        assert reasons == {"T-0001": "holder-dead"}

    def test_live_holder_not_flagged(self, repo: Path, second_worktree: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons.test\
        # _live_holder_not_flagged
        # A lease recorded just now, for a worktree that genuinely exists
        # and a ticket genuinely in the ledger, must NOT be reported --
        # this is the assertion that stops the staleness surfacing from
        # becoming a corruption bug (a too-eager flag inviting a
        # premature reclaim of a merely-slow agent's lease, T-1868's
        # failure mode).
        _write_lease(
            repo,
            "T-0001",
            second_worktree,
            recorded_at=datetime.now(UTC).isoformat(),
        )

        reasons = _stale_lease_reasons(repo)

        assert reasons == {}

    def test_no_root_returns_empty(self) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons.test\
        # _no_root_returns_empty
        assert _stale_lease_reasons(None) == {}


# frob:ticket T-1934
class TestRenderUnlandedBranchWorkSummary:
    """T-1934 REQUIRED-C: `frob ticket doable` surfaces "N branch(es)
    carry unlanded ticket work" alongside T-1876's own stale-lease
    warning, in the same place a coordinator already looks."""

    def test_no_root_is_a_noop(self, capsys) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_no_root_is_a_noop
        _render_unlanded_branch_work_summary(None)
        assert capsys.readouterr().out == ""

    def test_no_unlanded_work_prints_nothing(self, repo: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_no_unlanded_work_prints_nothing
        _render_unlanded_branch_work_summary(repo)
        assert "unlanded ticket work" not in caplog.text

    def test_unlanded_branch_is_summarized(self, repo: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_unlanded_branch_is_summarized
        import logging

        caplog.set_level(logging.INFO)
        _run(["git", "checkout", "-q", "-b", "runner-wiring"], repo)
        ticket_dir = repo / "tickets" / "T-9101"
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "ticket.md").write_text(
            "---\nid: T-9101\ntitle: 'x'\nstate: in-progress\nkind: bug\n"
            "origin: human\ncreated: '2026-08-09'\n---\nbody\n",
            encoding="utf-8",
        )
        (ticket_dir / "done-report.md").write_text(
            "## Done report\n\nDone.\n", encoding="utf-8"
        )
        _commit_all(repo, "finish T-9101 on runner-wiring")
        _run(["git", "checkout", "-q", "main"], repo)
        _run(["git", "clean", "-fdq", "--", "tickets"], repo)

        _render_unlanded_branch_work_summary(repo)

        assert "1 branch(es) carry unlanded ticket work" in caplog.text
        assert "runner-wiring" in caplog.text
