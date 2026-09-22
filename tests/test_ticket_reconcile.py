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

import contextlib
import subprocess
import sys
import time
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


@contextlib.contextmanager
def _foreign_ledger_lock_holder(lock_path: Path, *, ticket_id: str = "T-8888"):
    """T-5035: hold `lock_path` (`.frob/tickets.lock`, the ledger-splice
    lock `refuse_if_land_in_progress`'s default -- non-`whole_land` --
    probe actually reads, T-3612) from a REAL separate process, not this
    test process's own pid. Two reasons a same-process `os.getpid()`-
    stamped lock no longer proves the point this test needs: (1)
    `frob.tickets._leases`'s land-lock probing (T-2406) excludes the
    CALLING PROCESS's own pid as a foreign land holder by design where a
    pid IS compared (the `land.lock`/`whole_land=True` path); (2) T-3612
    moved the DEFAULT probe onto the bare advisory `tickets.lock`, which
    carries no holder metadata at all -- a `land.lock` JSON marker
    written by this test process, however stamped, is simply the wrong
    file for the guard this test actually exercises.

    Spawns a `python3 -c` child that flocks `lock_path` exclusively
    (writing its own JSON `pid`/`ticket_id` too, so a caller checking
    `LAND_LOCK_REL` for a correlated holder still sees one), touches a
    sibling `.ready` marker once the flock is held, then sleeps. Yields
    once that marker appears (polled, not a fixed sleep)."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    ready_path = lock_path.with_suffix(lock_path.suffix + ".ready")
    ready_path.unlink(missing_ok=True)
    script = (
        "import fcntl, json, os, time\n"
        f"path = {str(lock_path)!r}\n"
        f"ready_path = {str(ready_path)!r}\n"
        "fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)\n"
        "fcntl.flock(fd, fcntl.LOCK_EX)\n"
        f"os.write(fd, (json.dumps({{'pid': os.getpid(), 'ticket_id': {ticket_id!r}}}) + '\\n').encode())\n"
        "os.fsync(fd)\n"
        "open(ready_path, 'w').close()\n"
        "time.sleep(30)\n"
    )
    holder = subprocess.Popen([sys.executable, "-c", script])
    try:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and not ready_path.exists():
            time.sleep(0.02)
        assert ready_path.exists(), "foreign lock holder never signaled ready"
        yield holder.pid
    finally:
        holder.kill()
        holder.wait(timeout=5)
        ready_path.unlink(missing_ok=True)


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
        # tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_dry_run_reports_but_does_not_requeue  # noqa: E501
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

    # frob:tests src/frob/tickets/_reconcile.py::reconcile kind="unit"  # noqa: E501
    def test_apply_requeues_stale_hold_and_releases_lease(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_apply_requeues_stale_hold_and_releases_lease  # noqa: E501
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
        # tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_live_in_progress_ticket_with_lease_is_untouched  # noqa: E501
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


# frob:ticket T-4623
class TestReconcileApplyLandInProgressGuard:
    """Asserts `reconcile(apply=True)` refuses before writing anything
    while `.frob/land.lock` is held, and still succeeds normally when no
    lock is held."""
# frob:tests src/frob/tickets/_reconcile.py::reconcile kind="unit"  # noqa: E501

    def test_apply_refuses_and_writes_nothing_while_land_lock_held(
        self, repo: Path, caplog
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard.test_apply_refuses_and_writes_nothing_while_land_lock_held  # noqa: E501
        from frob.tickets._models import TicketError
        from frob.tickets._store import TICKETS_LEDGER_LOCK_REL

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

        lock_path = repo / TICKETS_LEDGER_LOCK_REL
        # T-5035: a REAL foreign process holds the ledger-splice lock --
        # this test process's own pid is excluded from land-in-progress
        # judgement by design (T-2406), and T-3612 moved the default
        # probe onto this bare `tickets.lock` anyway (see
        # `_foreign_ledger_lock_holder`'s own docstring).
        with _foreign_ledger_lock_holder(lock_path):
            status_before = _run(["git", "status", "--porcelain"], repo).stdout
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

    # frob:tests src/frob/tickets/_reconcile.py::reconcile kind="unit"  # noqa: E501
    def test_apply_still_requeues_when_no_land_in_progress(self, repo: Path) -> None:
        """Positive control: with no land lock held, `apply=True` still
        performs the ordinary requeue -- the new guard must not weaken the
        original T-0476 behaviour for the common, no-land-running case."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard.test_apply_still_requeues_when_no_land_in_progress  # noqa: E501
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
        # tests/test_ticket_reconcile.py::TestReconcileLiveWorktreeShield.test_live_default_worktree_with_no_lease_is_never_requeued  # noqa: E501
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
        # tests/test_ticket_reconcile.py::TestReconcileLiveWorktreeShield.test_still_requeues_a_genuinely_gone_worktree  # noqa: E501
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


class TestReconcileWorktreeMeasurementFailure:
    """T-3230: `_live_worktree_ticket_ids`'s own `git worktree list` spawn
    can fail (transient contention, a corrupt worktree admin dir, exec
    disabled) -- that must degrade to Nothing(), never to an empty set that
    reads as "confirmed no live worktree", or a stale-hold ledger sync
    (`_set_state_directly`, no lease) racing a genuinely live worktree could
    be requeued out from under it on nothing more than a flaky git spawn."""

    def test_live_worktrees_returns_nothing_on_a_real_spawn_failure(
        self, tmp_path: Path
    ) -> None:
        """Direct unit coverage of `_live_worktrees`'s own `spawned.is_err
        or spawned.danger_ok.returncode != 0` branch (T-3230): a REAL failed
        spawn (not-a-git-repo, not a monkeypatched return) against a
        non-git directory must yield `Nothing()`, never `Some(())` -- the
        two are NOT the same "no worktrees" answer."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileWorktreeMeasurementFailure.test_live_worktrees_returns_nothing_on_a_real_spawn_failure  # noqa: E501
        from frob.tickets._reconcile import _live_worktrees

        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()

        result = _live_worktrees(not_a_repo)
        assert result.is_nothing

    def test_live_worktrees_returns_some_empty_on_a_real_clean_measurement(
        self, repo: Path
    ) -> None:
        """Must-stay-quiet control for the same branch: a real, successful
        `git worktree list` against a repo with no OTHER linked worktree
        must yield `Some(())`, not `Nothing()` -- a genuinely measured
        empty result is not the same case as an unmeasurable one."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileWorktreeMeasurementFailure.test_live_worktrees_returns_some_empty_on_a_real_clean_measurement  # noqa: E501
        from frob.tickets._reconcile import _live_worktrees

        result = _live_worktrees(repo)
        assert result.is_some
        assert result.danger_some == ()

    def test_unmeasurable_worktree_signal_is_never_requeued(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-fire: force `_live_worktree_ticket_ids` to Nothing() (spawn
        failure) for an in-progress ticket with no lease -- pre-fix this
        would have requeued it (empty set collapsed with "no live
        worktree"); post-fix it must be left untouched."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileWorktreeMeasurementFailure.test_unmeasurable_worktree_signal_is_never_requeued  # noqa: E501
        from typani import Nothing

        from frob.tickets import _reconcile as reconcile_module

        created = new_ticket(repo, _spec("Unmeasurable", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        monkeypatch.setattr(
            reconcile_module, "_live_worktree_ticket_ids", lambda root: Nothing()
        )

        result = reconcile(repo, apply=True)
        assert result.is_ok
        assert tid not in result.danger_ok.requeued_tickets

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.IN_PROGRESS

    def test_measured_signal_still_requeues_normally(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-stay-quiet control: a genuinely MEASURED empty set (real
        `Some(frozenset())`, not `Nothing()`) still requeues a stale hold as
        before -- the fix narrows exactly the unmeasurable case, not the
        ordinary "measured, confirmed no live worktree" case."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileWorktreeMeasurementFailure.test_measured_signal_still_requeues_normally  # noqa: E501
        from typani import Some

        from frob.tickets import _reconcile as reconcile_module

        created = new_ticket(repo, _spec("MeasuredEmpty", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        monkeypatch.setattr(
            reconcile_module,
            "_live_worktree_ticket_ids",
            lambda root: Some(frozenset()),
        )

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
        # tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_live_worktree_with_no_lease_is_flagged_not_removed  # noqa: E501
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
# frob:tests src/frob/tickets/_reconcile.py::reconcile kind="unit"  # noqa: E501

    def test_apply_and_remove_orphans_actually_removes_it(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_apply_and_remove_orphans_actually_removes_it  # noqa: E501
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
        # tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_worktree_holding_a_live_lease_is_not_orphan  # noqa: E501
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
        # tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_dry_run_reports_but_does_not_clear  # noqa: E501
        _write_intent(repo, "T-crashed", repo)

        result = reconcile(repo)
        assert result.is_ok
        report = result.danger_ok
        assert report.orphaned_land_intents == ("T-crashed",)
        assert report.cleared_land_intents == ()
        assert len(_read_all_intents(repo)) == 1

    def test_apply_clears_the_orphaned_intent(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_apply_clears_the_orphaned_intent  # noqa: E501
        _write_intent(repo, "T-crashed", repo)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        report = result.danger_ok
        assert report.orphaned_land_intents == ("T-crashed",)
        assert report.cleared_land_intents == ("T-crashed",)
        assert _read_all_intents(repo) == ()

    def test_no_intents_reports_empty(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_no_intents_reports_empty  # noqa: E501
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


def _gitignore_frob_dir(repo: Path) -> None:
    """T-3567 fixture helper: gitignore `.frob/` and commit that change --
    the precondition `reconcile`'s own `_frob_dir_is_gitignored` guard
    requires before it will write `.frob/unlanded-summary-cache.json`.
    Every REAL frob-managed repo already has this (this project's own
    `.gitignore`); this fixture's own bare `repo`/`_git_init` does not,
    by design (T-1936's own tests need to see EVERY write `reconcile`
    makes, `.frob/` included, to prove nothing untracked is left behind
    when the precondition is genuinely absent -- see the sibling
    `test_skips_the_cache_write_when_frob_dir_is_not_gitignored`)."""
    gitignore = repo / ".gitignore"
    gitignore.write_text(".frob/\n", encoding="utf-8")
    _commit_all(repo, "gitignore .frob/")


class TestReconcileUnlandedBranchWork:
    """T-1934: reconcile's THIRD anomaly class -- finished-on-a-branch,
    not-terminal-on-main ticket work, report-only (never healed by
    # frob:tests src/frob/tickets/_reconcile.py::reconcile kind="unit"  # noqa: E501
    `apply`)."""

    # frob:tests src/frob/tickets/_reconcile.py::reconcile kind="unit"  # noqa: E501
    def test_reports_the_confirmed_leak_shape(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_reports_the_confirmed_leak_shape  # noqa: E501
        _write_finished_ticket_on_branch(repo, "runner-wiring", "T-1315")

        result = reconcile(repo)
        assert result.is_ok
        assert result.danger_ok.unlanded_branch_work == ("T-1315@runner-wiring",)

    def test_apply_never_heals_this_anomaly_class(self, repo: Path) -> None:
        """Report-only by design (T-1934's DO-NOT-auto-land requirement):
        `apply=True` must still just report, never touch the branch."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_apply_never_heals_this_anomaly_class  # noqa: E501
        _write_finished_ticket_on_branch(repo, "runner-wiring", "T-1315")

        result = reconcile(repo, apply=True)
        assert result.is_ok
        assert result.danger_ok.unlanded_branch_work == ("T-1315@runner-wiring",)
        # The branch itself is untouched -- still exists, still ahead.
        branches = _run(["git", "branch", "--list", "runner-wiring"], repo).stdout
        assert "runner-wiring" in branches

    def test_no_unlanded_work_reports_empty(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_no_unlanded_work_reports_empty  # noqa: E501
        # frob:tests src/frob/tickets/_unlanded_cache.py::_maybe_save_unlanded_summary_cache kind="unit"  # noqa: E501
        # frob:tests src/frob/tickets/_unlanded_cache.py::_frob_dir_is_gitignored kind="unit"  # noqa: E501
        result = reconcile(repo)
        assert result.is_ok
        assert result.danger_ok.unlanded_branch_work == ()
# frob:tests src/frob/tickets/_unlanded_cache.py::_maybe_save_unlanded_summary_cache kind="unit"  # noqa: E501
# frob:tests src/frob/tickets/_unlanded_cache.py::_frob_dir_is_gitignored kind="unit"  # noqa: E501

    # frob:tests src/frob/tickets/_reconcile.py::reconcile kind="unit"  # noqa: E501
    # frob:tests src/frob/app/ticket_runner/_query.py::_save_unlanded_summary_cache kind="unit"  # noqa: E501
    def test_populates_the_doable_summary_cache(self, repo: Path) -> None:
        """T-3522: reconcile now calls `_save_unlanded_summary_cache` with
        the branches its own scan just found -- the production write side
        `frob.app.ticket_runner._query._load_unlanded_summary_cache`
        (`doable`'s read side) was documented but never actually wired.
        T-3567: the write only happens when `.frob/` is gitignored (a
        precondition every real frob-managed repo already meets, unlike
        this bare fixture's default) -- set that up explicitly here."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_populates_the_doable_summary_cache  # noqa: E501
        from frob.app.ticket_runner._query import _load_unlanded_summary_cache

        _gitignore_frob_dir(repo)
        _write_finished_ticket_on_branch(repo, "runner-wiring", "T-1315")

        result = reconcile(repo)
        assert result.is_ok

        cached = _load_unlanded_summary_cache(repo)
        assert cached is not None
        assert cached.branches == ("runner-wiring",)

    # frob:tests src/frob/tickets/_reconcile.py::reconcile kind="unit"  # noqa: E501
    def test_populates_the_cache_even_on_a_dry_run(self, repo: Path) -> None:
        """The cache write is a best-effort performance memoization, not
        ticket state -- it refreshes on `apply=False` dry-runs too, unlike
        the ticket-state anomalies `reconcile`'s own docstring says a
        dry-run leaves untouched. T-3567: same `.frob/`-gitignored
        precondition as the sibling test above."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_populates_the_cache_even_on_a_dry_run  # noqa: E501
        from frob.app.ticket_runner._query import _load_unlanded_summary_cache

        _gitignore_frob_dir(repo)
        _write_finished_ticket_on_branch(repo, "runner-wiring", "T-1315")

        result = reconcile(repo, apply=False)
        assert result.is_ok

        cached = _load_unlanded_summary_cache(repo)
        assert cached is not None
        assert cached.branches == ("runner-wiring",)

    # frob:tests src/frob/tickets/_unlanded_cache.py::_maybe_save_unlanded_summary_cache kind="unit"  # noqa: E501
    # frob:tests src/frob/tickets/_unlanded_cache.py::_frob_dir_is_gitignored kind="unit"  # noqa: E501
    def test_skips_the_cache_write_when_frob_dir_is_not_gitignored(
        self, repo: Path
    ) -> None:
        """T-3567's own regression: the T-1936 incident this ticket fixed
        -- writing the cache into a repo that has NOT gitignored `.frob/`
        (this fixture's own default) must not happen at all, since it
        would leave an untracked file `git status` sees as dirty. Best-
        effort skip, matching `_save_unlanded_summary_cache`'s own
        existing log-and-swallow posture -- `reconcile` itself still
        succeeds."""
        # frob:tests \
        # tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_skips_the_cache_write_when_frob_dir_is_not_gitignored  # noqa: E501
        from frob.app.ticket_runner._query import _load_unlanded_summary_cache

        _write_finished_ticket_on_branch(repo, "runner-wiring", "T-1315")

        result = reconcile(repo)
        assert result.is_ok

        assert _load_unlanded_summary_cache(repo) is None
        status = _run(["git", "status", "--porcelain"], repo).stdout
        assert ".frob" not in status

    # frob:ticket T-3731
    # frob:tests src/frob/tickets/_unlanded.py::_unlanded_branch_work kind="unit"  # noqa: E501
    def test_reconcile_does_not_hang_with_many_branches(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3731: the CI-blocking hang -- `frob ticket reconcile --apply`
        ran 36+ minutes (run 33721091819) because the unlanded-branch-work
        scan (`_unlanded_branch_work`) iterated every local branch with no
        cap, and this repo carries 1578 of them. A budget of `0` (forcing
        an immediate cutoff, the same idea `wait_timeout_s=0` already uses
        elsewhere in this test module to avoid burning real wall-clock
        time) proves `reconcile` still returns a well-formed `Ok` report
        instead of hanging, even when the scan is cut short before it
        finishes."""
        import frob.tickets._unlanded as unlanded_mod

        monkeypatch.setattr(unlanded_mod, "_UNLANDED_SCAN_BUDGET_S", 0.0)
        _write_finished_ticket_on_branch(repo, "runner-wiring", "T-1315")

        result = reconcile(repo)

        assert result.is_ok
        # The budget fired before the scan reached this branch's finding
        # -- proving the cutoff is real, not merely present and unused.
        assert result.danger_ok.unlanded_branch_work == ()
