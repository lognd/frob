"""T-0476: `frob.tickets.reconcile` -- heal ticket<->worktree binding drift.

Real `git worktree add`/`git worktree remove` fixtures (matching
`tests/test_ticket_leases_cross_worktree.py`'s style) -- reconcile's whole
job is judging LIVE worktree state against the lease registry, which a
single in-memory tmp_path cannot exercise.

`reconcile` judges the LOCAL checkout's own `tickets.md` (an in-progress
ticket per that ledger, with no matching live lease, is a stale hold) --
this repo's real practice periodically syncs an in-progress state onto
main outside of a full land (see `tickets.md`'s history of "chore(tickets):
lease T-xxxx" commits), so a ticket can genuinely show `IN_PROGRESS` on the
checkout `reconcile` runs against while the lease that would justify it has
gone stale. The fixtures below model that directly: `_set_state_directly`
writes a ticket's ledger `state:` field WITHOUT going through `transition`
(and therefore without recording/touching a lease) -- exactly what a
lease-stamp sync onto main does; a real `transition` call in a worktree is
what actually records the lease the reconcile checks then judges live/dead.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    load_all,
    new_ticket,
    reconcile,
    transition,
)
from frob.tickets._journal import _read_all_intents, _write_intent
from frob.tickets._leases import read_all_leases
from frob.tickets._store import atomic_write, ledger_path, write_ticket


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


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


def _set_state_directly(root: Path, ticket_id: str, state: TicketState) -> None:
    """Write `ticket_id`'s `state:` field in `root`'s OWN ledger directly
    (bypassing `transition`, so no lease is recorded/touched) -- models a
    lease-stamp sync landing an in-progress state onto a checkout that
    never itself ran `frob ticket start`."""
    loaded = load_all(root)
    assert loaded.is_ok
    ticket = loaded.danger_ok[ticket_id]
    assert write_ticket(root, ticket.model_copy(update={"state": state})).is_ok


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


class TestReconcileStaleHold:
    def test_dry_run_reports_but_does_not_requeue(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_dry_run_reports_b\
        # ut_does_not_requeue
        created = new_ticket(repo, _spec("Stale", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-a", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        # Simulate a crashed/abandoned agent worktree, torn down without
        # ever requeuing or closing the ticket.
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)

        # Simulate the lease-stamp sync that lands the in-progress state
        # onto `repo`'s own ledger, independent of the (now-dead) lease.
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        result = reconcile(repo, apply=False)
        assert result.is_ok
        report = result.danger_ok
        assert report.requeued_tickets == (tid,)
        assert report.applied is False

        # Dry-run: the ledger is untouched.
        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.IN_PROGRESS

    def test_apply_requeues_stale_hold_and_releases_lease(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_apply_requeues_st\
        # ale_hold_and_releases_lease
        created = new_ticket(repo, _spec("Stale2", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-b", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        report = result.danger_ok
        assert report.requeued_tickets == (tid,)
        assert report.applied is True

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.QUEUED
        assert not any(lease.ticket_id == tid for lease in read_all_leases(repo))

    def test_live_in_progress_ticket_with_lease_is_untouched(self, repo: Path) -> None:
        """A ticket that IS in-progress with a real, live lease must never
        be reported as a stale hold -- reconcile only judges absence of a
        live lease, not the mere fact of being in-progress."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_live_in_progress_\
        # ticket_with_lease_is_untouched
        created = new_ticket(repo, _spec("Alive", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-c", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        assert tid not in result.danger_ok.requeued_tickets

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.IN_PROGRESS

        assert transition(wt, tid, TicketState.QUEUED).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)


class TestReconcileApplyLandInProgressGuard:
    """T-2291: `reconcile(apply=True)` must refuse BEFORE writing anything
    while a `frob ticket land` holds `.frob/land.lock` -- previously the
    equivalent guard fired only later, at the ledger-commit step, after
    `_requeue_stale_holds` had already mutated ticket.md on disk (the real
    9246d4b5a/2d854269c incident). Both a must-now-fail (refused, tree
    untouched) and a must-still-pass (no lock held, behaviour unchanged)
    case are required so the guard cannot regress into over-refusing."""

    def test_apply_refuses_and_writes_nothing_while_land_lock_held(
        self, repo: Path, caplog
    ) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard.test_ap\
        # ply_refuses_and_writes_nothing_while_land_lock_held
        import fcntl
        import json
        import os as _os

        from frob.tickets._leases import LAND_LOCK_REL
        from frob.tickets._models import TicketError

        created = new_ticket(repo, _spec("Stale3", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-d", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        lock_path = repo / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = _os.open(str(lock_path), _os.O_CREAT | _os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _os.write(
            holder_fd,
            (json.dumps({"pid": _os.getpid(), "ticket_id": "T-8888"}) + "\n").encode(),
        )
        try:
            status_before = _run(
                ["git", "status", "--porcelain"], repo
            ).stdout
            with caplog.at_level("WARNING"):
                result = reconcile(repo, apply=True, wait_timeout_s=0)
            assert result.is_err
            assert result.danger_err == TicketError.ReconcileLandInProgress

            # The write did not happen: ledger unchanged on disk AND the
            # working tree is exactly as dirty (or clean) as before the
            # call -- not "requeued and abandoned uncommitted".
            loaded = load_all(repo)
            assert loaded.is_ok
            assert loaded.danger_ok[tid].state == TicketState.IN_PROGRESS
            status_after = _run(["git", "status", "--porcelain"], repo).stdout
            assert status_after == status_before
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            _os.close(holder_fd)

    def test_apply_still_requeues_when_no_land_in_progress(self, repo: Path) -> None:
        """Positive control: with no land lock held, `apply=True` still
        performs the ordinary requeue -- the new guard must not weaken the
        original T-0476 behaviour for the common, no-land-running case."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard.test_ap\
        # ply_still_requeues_when_no_land_in_progress
        created = new_ticket(repo, _spec("Stale4", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-e", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        assert not (repo / ".frob" / "land.lock").exists()
        result = reconcile(repo, apply=True)
        assert result.is_ok
        report = result.danger_ok
        assert report.requeued_tickets == (tid,)
        assert report.applied is True

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.QUEUED


class TestReconcileLiveWorktreeShield:
    """T-2292: `reconcile --apply` must never requeue a ticket whose
    default-convention worktree is still LIVE on disk, even if the lease
    read comes back absent -- the real incident (T-2276 demoted mid-land
    while its worktree and agent were both live) came from trusting a
    momentarily-absent lease read as proof of abandonment. This is
    INDEPENDENT of T-2291's own land-in-progress guard: no land.lock and
    no live land process are involved here at all, only a live worktree
    with no lease -- the exact gap `_live_worktree_ticket_ids` closes."""

    def test_live_default_worktree_with_no_lease_is_never_requeued(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileLiveWorktreeShield.test_live_def\
        # ault_worktree_with_no_lease_is_never_requeued
        from frob.tickets._leases import release_lease

        created = new_ticket(repo, _spec("LiveNoLease", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        # A worktree cut on the SAME default-convention branch name
        # `frob ticket work`/`start` always uses: ticket_id.lower().
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", tid.lower(), str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        # Simulate the lease reading momentarily absent (the T-2292
        # incident's own hypothesis) WITHOUT removing the worktree --
        # the worktree is still fully live, on disk, agent's checkout
        # intact.
        release_lease(repo, tid)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        report = result.danger_ok
        assert tid not in report.requeued_tickets

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.IN_PROGRESS

        _run(["git", "worktree", "remove", "--force", str(wt)], repo)

    def test_still_requeues_a_genuinely_gone_worktree(self, repo: Path) -> None:
        """Must-still-pass control: once the worktree is ACTUALLY removed
        (the ordinary crashed-agent shape), the same ticket is requeued
        exactly as before -- the new worktree-branch shield does not
        widen into "never requeue a default-branch-named ticket"."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileLiveWorktreeShield.test_still_re\
        # queues_a_genuinely_gone_worktree
        created = new_ticket(repo, _spec("LiveThenGone", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", tid.lower(), str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        assert result.danger_ok.requeued_tickets == (tid,)

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.QUEUED


class TestReconcileOrphanWorktree:
    def test_live_worktree_with_no_lease_is_flagged_not_removed(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_live_worktre\
        # e_with_no_lease_is_flagged_not_removed
        wt = repo.parent / "orphan-wt"
        _run(["git", "worktree", "add", "-b", "feature-orphan", str(wt)], repo)

        result = reconcile(repo, apply=True)  # apply alone, no remove_orphans
        assert result.is_ok
        report = result.danger_ok
        assert str(wt.resolve()) in report.orphan_worktrees
        assert report.removed_worktrees == ()
        assert report.removed_orphans is False
        assert wt.exists()

        _run(["git", "worktree", "remove", "--force", str(wt)], repo)

    def test_apply_and_remove_orphans_actually_removes_it(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_apply_and_re\
        # move_orphans_actually_removes_it
        wt = repo.parent / "orphan-wt2"
        _run(["git", "worktree", "add", "-b", "feature-orphan2", str(wt)], repo)

        result = reconcile(repo, apply=True, remove_orphans=True)
        assert result.is_ok
        report = result.danger_ok
        assert str(wt.resolve()) in report.removed_worktrees
        assert report.removed_orphans is True
        assert not wt.exists()

    def test_worktree_holding_a_live_lease_is_not_orphan(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_worktree_hol\
        # ding_a_live_lease_is_not_orphan
        created = new_ticket(repo, _spec("Held", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "held-wt"
        _run(["git", "worktree", "add", "-b", "feature-held", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok

        result = reconcile(repo, apply=True, remove_orphans=True)
        assert result.is_ok
        assert str(wt.resolve()) not in result.danger_ok.orphan_worktrees
        assert wt.exists()

        assert transition(wt, tid, TicketState.QUEUED).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)


class TestReconcileOrphanedLandIntent:
    """T-0456: a `frob ticket land` intent-journal record still present
    under `repo` means the process that started that land never reached
    its own `_clear_intent` cleanup (crash/interrupt mid-land)."""

    def test_dry_run_reports_but_does_not_clear(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_dry_run_\
        # reports_but_does_not_clear
        _write_intent(repo, "T-crashed", repo)

        result = reconcile(repo)
        assert result.is_ok
        report = result.danger_ok
        assert report.orphaned_land_intents == ("T-crashed",)
        assert report.cleared_land_intents == ()
        assert len(_read_all_intents(repo)) == 1

    def test_apply_clears_the_orphaned_intent(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_apply_cl\
        # ears_the_orphaned_intent
        _write_intent(repo, "T-crashed", repo)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        report = result.danger_ok
        assert report.orphaned_land_intents == ("T-crashed",)
        assert report.cleared_land_intents == ("T-crashed",)
        assert _read_all_intents(repo) == ()

    def test_no_intents_reports_empty(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_no_inten\
        # ts_reports_empty
        result = reconcile(repo)
        assert result.is_ok
        assert result.danger_ok.orphaned_land_intents == ()


_UNLANDED_TICKET_MD = """---
id: {tid}
title: '{tid}'
state: {state}
kind: bug
origin: human
created: '2026-08-09'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Body for {tid}.
"""


def _write_finished_ticket_on_branch(
    repo: Path, branch: str, tid: str, *, state: str = "in-progress"
) -> None:
    """T-1934 fixture: commit a `tickets/<tid>/{{ticket,done-report}}.md`
    pair onto a fresh local `branch`, leaving `main` (`repo`'s own current
    checkout) untouched -- the "committed cleanly, died before land" shape
    `frob.tickets._unlanded` detects, using a raw v2-layout write
    independent of `repo`'s own `tickets.md`-seeded `_store_mode`."""
    _run(["git", "checkout", "-q", "-b", branch], repo)
    ticket_dir = repo / "tickets" / tid
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "ticket.md").write_text(
        _UNLANDED_TICKET_MD.format(tid=tid, state=state), encoding="utf-8"
    )
    (ticket_dir / "done-report.md").write_text(
        "## Done report\n\nFinished.\n", encoding="utf-8"
    )
    _commit_all(repo, f"finish {tid} on {branch}")
    _run(["git", "checkout", "-q", "main"], repo)
    # Directory not tracked on `main` -- clean up the working-tree copy
    # `git checkout` left behind so `main`'s own tree matches its commit.
    _run(["git", "clean", "-fdq", "--", "tickets"], repo)


class TestReconcileUnlandedBranchWork:
    """T-1934: reconcile's THIRD anomaly class -- finished-on-a-branch,
    not-terminal-on-main ticket work, report-only (never healed by
    `apply`)."""

    def test_reports_the_confirmed_leak_shape(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_reports_\
        # the_confirmed_leak_shape
        _write_finished_ticket_on_branch(repo, "runner-wiring", "T-1315")

        result = reconcile(repo)
        assert result.is_ok
        assert result.danger_ok.unlanded_branch_work == ("T-1315@runner-wiring",)

    def test_apply_never_heals_this_anomaly_class(self, repo: Path) -> None:
        """Report-only by design (T-1934's DO-NOT-auto-land requirement):
        `apply=True` must still just report, never touch the branch."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_apply_ne\
        # ver_heals_this_anomaly_class
        _write_finished_ticket_on_branch(repo, "runner-wiring", "T-1315")

        result = reconcile(repo, apply=True)
        assert result.is_ok
        assert result.danger_ok.unlanded_branch_work == ("T-1315@runner-wiring",)
        # The branch itself is untouched -- still exists, still ahead.
        branches = _run(["git", "branch", "--list", "runner-wiring"], repo).stdout
        assert "runner-wiring" in branches

    def test_no_unlanded_work_reports_empty(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_no_unlan\
        # ded_work_reports_empty
        result = reconcile(repo)
        assert result.is_ok
        assert result.danger_ok.unlanded_branch_work == ()
