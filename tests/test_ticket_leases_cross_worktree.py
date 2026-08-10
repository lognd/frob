"""T-0473: the cross-worktree scope-lease side-channel
(`frob.tickets._leases`) -- a lease taken by `transition(..., IN_PROGRESS)`
in ONE real git worktree must be visible to `leased_by`/`doable` in a
SECOND, separate worktree of the same repository, without either worktree
merging/landing into the other. Uses real `git worktree add` checkouts
(matching `tests/test_ticket_land.py`'s style) -- the whole point of T-0473
is real cross-process/cross-checkout visibility via the shared git common
dir, which a single in-memory `tmp_path` can never exercise.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    TicketError,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    doable,
    leased_by,
    load_all,
    mutate_scope,
    new_ticket,
    transition,
)
from frob.tickets._leases import (
    _git_common_dir,
    force_release_lease,
    lease_holder_worktree,
    read_all_leases,
    same_worktree_lease,
)
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


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger and one committed file,
    plus a second linked worktree (`wt`) of the SAME repository -- the two
    real checkouts this module's tests exercise a lease across."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


@pytest.fixture
def second_worktree(repo: Path) -> Path:
    """A second linked `git worktree` of `repo`, on its own branch -- shares
    `repo`'s git common dir (and therefore its `frob-leases/` side channel)
    but has its OWN checkout of `tickets.md`."""
    wt = repo.parent / "wt"
    _run(["git", "worktree", "add", "-b", "feature-wt", str(wt)], repo)
    return wt


class TestGitCommonDir:
    def test_shared_across_linked_worktrees(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestGitCommonDir.test_shared_acro\
        # ss_linked_worktrees
        main_common = _git_common_dir(repo)
        wt_common = _git_common_dir(second_worktree)
        assert main_common.is_ok
        assert wt_common.is_ok
        assert main_common.danger_ok == wt_common.danger_ok


class TestCrossWorktreeLeaseVisibility:
    """A lease recorded by `transition(..., IN_PROGRESS)` in one worktree is
    visible via `read_all_leases`/`leased_by`/`doable` from another."""

    def test_lease_written_in_one_worktree_seen_in_another(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_lease_written_in_one_worktree_seen_in_another
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        leases = read_all_leases(second_worktree)
        assert any(lease.ticket_id == tid for lease in leases)
        held = next(lease for lease in leases if lease.ticket_id == tid)
        assert held.scope == ("src/feature.py",)
        assert held.worktree == str(repo.resolve())

    def test_doable_in_second_worktree_hides_colliding_ticket(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_doable_in_second_worktree_hides_colliding_ticket
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid_a = created.danger_ok.id
        assert transition(repo, tid_a, TicketState.PLANNED).is_ok
        assert transition(repo, tid_a, TicketState.IN_PROGRESS).is_ok

        # A ticket the SECOND worktree's own local ledger only knows about
        # (never dispatched in `repo`), whose scope collides with the lease
        # `repo` holds. Before T-0473, `second_worktree`'s own doable would
        # never see `tid_a`'s lease (its local `tickets.md` never had it as
        # IN_PROGRESS) and would incorrectly offer the colliding ticket.
        created_b = new_ticket(
            second_worktree, _spec("Feature B collides", scope=("src/feature.py",))
        )
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id

        loaded = load_all(second_worktree)
        assert loaded.is_ok
        queue = TicketQueue(tickets=loaded.danger_ok)
        ticket_b = queue.tickets[tid_b]
        holds = leased_by(queue, ticket_b, second_worktree)
        assert any(holder_id == tid_a for holder_id, _glob in holds)

        offered = doable(queue, second_worktree)
        assert all(t.id != tid_b for t in offered)

    def test_release_on_close_removes_the_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_release_on_close_removes_the_lease
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok
        assert any(lease.ticket_id == tid for lease in read_all_leases(second_worktree))

        assert transition(repo, tid, TicketState.QUEUED).is_ok
        assert not any(
            lease.ticket_id == tid for lease in read_all_leases(second_worktree)
        )

    def test_stale_lease_for_a_removed_worktree_is_skipped(
        self, repo: Path, second_worktree: Path, tmp_path: Path
    ) -> None:
        """A lease recording a worktree path that no longer exists on disk
        (the dead-agent case T-0476 will reconcile more fully) must not
        wedge `doable` for every other worktree forever -- `read_all_leases`
        treats it as stale and skips it."""
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_stale_lease_for_a_removed_worktree_is_skipped
        doomed_wt = repo.parent / "doomed"
        _run(["git", "worktree", "add", "-b", "feature-doomed", str(doomed_wt)], repo)
        created = new_ticket(doomed_wt, _spec("Doomed", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(doomed_wt, tid, TicketState.PLANNED).is_ok
        assert transition(doomed_wt, tid, TicketState.IN_PROGRESS).is_ok
        assert any(lease.ticket_id == tid for lease in read_all_leases(second_worktree))

        # Simulate the worktree being torn down without `git worktree
        # remove` (a crashed/abandoned agent checkout).
        _run(["git", "worktree", "remove", "--force", str(doomed_wt)], repo)
        assert not doomed_wt.exists()

        assert not any(
            lease.ticket_id == tid for lease in read_all_leases(second_worktree)
        )

    def test_scope_mutation_refreshes_the_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_scope_mutation_refreshes_the_lease
        (repo / "src" / "other.py").write_text("# other\n")
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        mutated = mutate_scope(
            repo, tid, add=("src/other.py",), reason="widen for test"
        )
        assert mutated.is_ok

        leases = read_all_leases(second_worktree)
        held = next(lease for lease in leases if lease.ticket_id == tid)
        assert "src/other.py" in held.scope
        assert "src/feature.py" in held.scope


class TestLeaseAttributionProvenance:
    """T-1743: `lease_holder_worktree` names WHERE a `doable --show-blocked`
    attribution actually comes from, so a holder id with no real
    cross-worktree lease file (the incident's stale/wrong-attribution
    shape) is distinguishable from a genuine one."""

    def test_cross_worktree_holder_names_its_worktree(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestLeaseAttributionProvenance.te\
        # st_cross_worktree_holder_names_its_worktree
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        worktree = lease_holder_worktree(second_worktree, tid)
        assert worktree == str(repo.resolve())

    def test_local_only_holder_has_no_worktree(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestLeaseAttributionProvenance.te\
        # st_local_only_holder_has_no_worktree
        assert lease_holder_worktree(repo, "T-9999") is None


class TestForceReleaseLease:
    """T-1743: the supported release path for an orphaned lease -- reaches
    a lease file directly, independent of any ticket's own declared
    scope, so it can clear a holder `frob ticket scope --remove` cannot."""

    def test_removes_an_existing_lease_file(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease.test_remove\
        # s_an_existing_lease_file
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok
        assert any(lease.ticket_id == tid for lease in read_all_leases(second_worktree))

        released = force_release_lease(second_worktree, tid)
        assert released.is_ok
        assert released.danger_ok is True
        assert not any(
            lease.ticket_id == tid for lease in read_all_leases(second_worktree)
        )

    def test_no_op_when_no_lease_file_exists(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease.test_no_op_\
        # when_no_lease_file_exists
        released = force_release_lease(repo, "T-9999")
        assert released.is_ok
        assert released.danger_ok is False


# frob:ticket T-1868
class TestScopeAddRefusesLiveCrossWorktreeLease:
    """T-1868: reproduces the confirmed double-hold incident directly --
    two REAL, separate git worktrees of the same repository, each with its
    OWN unmerged local ticket ledger, one ticket in-progress in each. A
    `scope --add` in the SECOND worktree for a path the FIRST worktree's
    ticket already holds must be refused, even though the second
    worktree's own local ledger has never seen the first ticket's `start`
    (no merge between the two worktrees anywhere in this test) -- exactly
    the T-1863/T-1822 shape (`design/frob.strata`, thirty-six seconds
    apart, neither refused) and the T-1648 land-time reproduction
    (`frob ticket scope T-1648 --add design/frob.strata` succeeded against
    T-1863's live, unmerged lease on the same path)."""

    def test_scope_add_refused_by_unmerged_sibling_worktrees_live_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestScopeAddRefusesLiveCrossWorkt\
        # reeLease.test_scope_add_refused_by_unmerged_sibling_worktrees_live_lease
        # Ticket A: created and started IN `repo`, leasing src/feature.py.
        # `second_worktree` never merges this commit -- its own local
        # ticket ledger has no record of ticket A at all.
        created_a = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(repo, tid_a, TicketState.PLANNED).is_ok
        assert transition(repo, tid_a, TicketState.IN_PROGRESS).is_ok

        # Ticket B: created and started independently IN second_worktree,
        # with a scope that does NOT collide at filing time.
        created_b = new_ticket(
            second_worktree, _spec("Feature B", scope=("src/unrelated.py",))
        )
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        assert transition(second_worktree, tid_b, TicketState.PLANNED).is_ok
        assert transition(second_worktree, tid_b, TicketState.IN_PROGRESS).is_ok

        # Confirm the premise: second_worktree's own LOCAL ledger has never
        # heard of ticket A (no merge happened), so a queue-only check
        # would see no conflict at all.
        local_queue = load_all(second_worktree)
        assert local_queue.is_ok
        assert tid_a not in local_queue.danger_ok

        # The refusal this ticket adds: `mutate_scope` must catch the
        # collision via the LIVE cross-worktree lease side-channel even
        # though the local ledger cannot see it.
        mutated = mutate_scope(
            second_worktree,
            tid_b,
            add=("src/feature.py",),
            reason="T-1868 regression: must be refused",
        )
        assert mutated.is_err
        assert mutated.danger_err == TicketError.ScopeLeaseConflict

        # The refusal must be a true refusal, not a partial write.
        reloaded = load_all(second_worktree)
        assert reloaded.is_ok
        assert "src/feature.py" not in reloaded.danger_ok[tid_b].scope


# frob:ticket T-1909
class TestScopeAddIgnoresTerminalLease:
    """T-1909: reproduces the confirmed stale-worktree incident directly --
    a ticket's cross-worktree lease file (T-0473) is only ever removed by
    the SAME worktree that wrote it (`release_lease`, called from
    `transition`'s own exit-from-IN_PROGRESS path); a worktree abandoned
    after its ticket was dropped/closed some OTHER way (a coordinator
    marking it terminal on the shared ledger without that worktree's own
    `transition` ever running) leaves the lease file behind, live and
    unexpired, on the shared side-channel. A `scope --add` from a THIRD
    worktree must resolve that lease's holder against ITS OWN, current
    ledger view -- not the stale lease file's mere presence -- exactly
    the T-1893/T-1579 incident: `frob ticket new`/`start` for an unrelated
    ticket refused with `ScopeLeaseConflict` naming an already-dropped
    holder."""

    def test_dropped_ticket_on_local_ledger_does_not_block_live_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestScopeAddIgnoresTerminalLease.\
        # test_dropped_ticket_on_local_ledger_does_not_block_live_lease
        # Ticket A: started IN second_worktree, leasing src/feature.py --
        # this writes a live lease file to the SHARED side-channel that
        # only second_worktree's own transition() could ever release.
        created_a = new_ticket(
            second_worktree, _spec("Feature A", scope=("src/feature.py",))
        )
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(second_worktree, tid_a, TicketState.PLANNED).is_ok
        assert transition(second_worktree, tid_a, TicketState.IN_PROGRESS).is_ok

        started = load_all(second_worktree)
        assert started.is_ok
        in_progress_ticket = started.danger_ok[tid_a]

        # `repo`'s own ledger independently learns ticket A is DROPPED --
        # written directly (write_ticket), NOT via second_worktree's own
        # transition(), so second_worktree's lease file is never released
        # (T-1909's exact real-world shape: the drop happened somewhere
        # that never touches the abandoned worktree's own lease).
        dropped_ticket = in_progress_ticket.model_copy(
            update={"state": TicketState.DROPPED}
        )
        assert write_ticket(repo, dropped_ticket).is_ok

        # Confirm the premise: the lease file is still live on the shared
        # side-channel, visible from repo.
        live = read_all_leases(repo)
        assert any(lease.ticket_id == tid_a for lease in live)

        # Ticket B, started fresh in repo: a scope --add onto the same
        # path must NOT be blocked by ticket A's stale lease, because
        # repo's own ledger already knows ticket A is DROPPED.
        created_b = new_ticket(repo, _spec("Feature B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        assert transition(repo, tid_b, TicketState.PLANNED).is_ok
        assert transition(repo, tid_b, TicketState.IN_PROGRESS).is_ok

        mutated = mutate_scope(
            repo,
            tid_b,
            add=("src/feature.py",),
            reason="T-1909 regression: a dropped ticket's lease must not block",
        )
        assert mutated.is_ok
        reloaded = load_all(repo)
        assert reloaded.is_ok
        assert "src/feature.py" in reloaded.danger_ok[tid_b].scope


# frob:ticket T-1882
class TestRenumberRefusesLiveCrossWorktreeLease:
    """T-1882: a bulk (`renumber`) or single-id (`renumber_one`) id rewrite
    must refuse outright while a DIFFERENT worktree holds a live lease on
    ANY ticket -- the 2026-08-08 incident renumbered all 273 tickets in one
    shot; any one of those ids being live-leased to a sibling worktree at
    the time would have silently orphaned that worktree's lease file
    (keyed by ticket id string, never re-derived from content)."""

    # frob:ticket T-1882
    def test_bulk_renumber_refused_by_unmerged_sibling_worktrees_live_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorkt\
        # reeLease.test_bulk_renumber_refused_by_unmerged_sibling_worktrees_live_lease
        from frob.tickets import renumber

        # Ticket A: started in second_worktree -- a live lease `repo`'s
        # own local ledger has never merged.
        created_a = new_ticket(
            second_worktree, _spec("Feature A", scope=("src/feature.py",))
        )
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(second_worktree, tid_a, TicketState.PLANNED).is_ok
        assert transition(second_worktree, tid_a, TicketState.IN_PROGRESS).is_ok

        # A gap in repo's OWN local ledger for renumber to want to close.
        created_b = new_ticket(repo, _spec("Feature B", scope=("src/other.py",)))
        assert created_b.is_ok

        result = renumber(repo)
        assert result.is_err
        assert result.danger_err == TicketError.ScopeLeaseConflict

    # frob:ticket T-1882
    def test_bulk_renumber_dry_run_still_works_under_a_live_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorkt\
        # reeLease.test_bulk_renumber_dry_run_still_works_under_a_live_lease
        from frob.tickets import renumber

        created_a = new_ticket(
            second_worktree, _spec("Feature A", scope=("src/feature.py",))
        )
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(second_worktree, tid_a, TicketState.PLANNED).is_ok
        assert transition(second_worktree, tid_a, TicketState.IN_PROGRESS).is_ok

        created_b = new_ticket(repo, _spec("Feature B", scope=("src/other.py",)))
        assert created_b.is_ok

        # A read-only preview must never be blocked by a live lease -- it
        # writes nothing, so there is nothing to corrupt.
        result = renumber(repo, dry_run=True)
        assert result.is_ok

    # frob:ticket T-1918
    def test_single_id_renumber_succeeds_despite_unrelated_live_foreign_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        """T-1918 regression: `renumber_one` must NOT refuse over a live
        foreign lease on a DIFFERENT, unrelated ticket id -- exactly one
        lease file (`old_id`'s own) can ever be orphaned by a single-id
        rename, so a lease on any other id is not at risk. This is the
        shape that broke draft promotion at land time under parallel
        dispatch: any other agent's live lease, on any unrelated ticket,
        made every single-id renumber refuse."""
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorkt\
        # reeLease.test_single_id_renumber_succeeds_despite_unrelated_live_foreign_lease
        from frob.tickets import renumber_one

        # Ticket A: live-leased in second_worktree -- unrelated to the id
        # `repo` is about to renumber.
        created_a = new_ticket(
            second_worktree, _spec("Feature A", scope=("src/feature.py",))
        )
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(second_worktree, tid_a, TicketState.PLANNED).is_ok
        assert transition(second_worktree, tid_a, TicketState.IN_PROGRESS).is_ok

        # Ticket B: repo's own local ticket, entirely unrelated to A, being
        # single-id renumbered -- not the id A holds a lease on.
        created_b = new_ticket(repo, _spec("Feature B", scope=("src/other.py",)))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id

        result = renumber_one(repo, tid_b, "T-9999")
        assert result.is_ok

    # frob:ticket T-1918
    def test_single_id_renumber_still_refused_when_lease_is_on_the_id_being_renumbered(
        self, repo: Path, second_worktree: Path
    ) -> None:
        """A live foreign lease on the EXACT id being renumbered must still
        refuse -- T-1918 narrows the guard to the specific id at risk, it
        does not remove the protection T-1882 added."""
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorkt\
        # reeLease.test_single_id_renumber_still_refused_when_lease_is_on_the_id_being_\
        # renumbered
        from frob.tickets import renumber_one

        # Ticket A is created in repo (so both checkouts agree it exists),
        # then leased LIVE from second_worktree -- the id repo is about to
        # try to renumber out from under that lease.
        created_a = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        _run(["git", "merge", "main"], second_worktree)
        assert transition(second_worktree, tid_a, TicketState.PLANNED).is_ok
        assert transition(second_worktree, tid_a, TicketState.IN_PROGRESS).is_ok

        result = renumber_one(repo, tid_a, "T-9999")
        assert result.is_err
        assert result.danger_err == TicketError.ScopeLeaseConflict

    # frob:ticket T-1918
    def test_bulk_renumber_still_refuses_under_any_live_foreign_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        """Explicit anti-regression assertion for T-1882: the BULK
        `renumber()` path must keep refusing over ANY live foreign lease on
        ANY ticket, even one entirely unrelated to what would move -- T-1918
        narrows only the single-id paths, never this one."""
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorkt\
        # reeLease.test_bulk_renumber_still_refuses_under_any_live_foreign_lease
        from frob.tickets import renumber

        created_a = new_ticket(
            second_worktree, _spec("Feature A", scope=("src/feature.py",))
        )
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(second_worktree, tid_a, TicketState.PLANNED).is_ok
        assert transition(second_worktree, tid_a, TicketState.IN_PROGRESS).is_ok

        created_b = new_ticket(repo, _spec("Feature B", scope=("src/other.py",)))
        assert created_b.is_ok

        result = renumber(repo)
        assert result.is_err
        assert result.danger_err == TicketError.ScopeLeaseConflict


# frob:ticket T-1883
class TestSameWorktreeLease:
    """`same_worktree_lease` (T-1356's rule, T-1883's shared home): two
    tickets leased to the SAME worktree never count as conflicting with each
    other; two tickets leased to DIFFERENT worktrees do."""

    def test_both_leased_to_same_worktree_matches(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestSameWorktreeLease.test_both_l\
        # eased_to_same_worktree_matches
        created_a = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(repo, tid_a, TicketState.PLANNED).is_ok
        assert transition(repo, tid_a, TicketState.IN_PROGRESS).is_ok

        created_b = new_ticket(repo, _spec("Feature B", scope=("src/other.py",)))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        assert transition(repo, tid_b, TicketState.PLANNED).is_ok
        assert transition(repo, tid_b, TicketState.IN_PROGRESS).is_ok

        assert same_worktree_lease(repo, tid_b, tid_a) is True

    def test_different_worktrees_do_not_match(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestSameWorktreeLease.test_differ\
        # ent_worktrees_do_not_match
        created_a = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(repo, tid_a, TicketState.PLANNED).is_ok
        assert transition(repo, tid_a, TicketState.IN_PROGRESS).is_ok

        created_b = new_ticket(
            second_worktree, _spec("Feature B", scope=("src/other.py",))
        )
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        assert transition(second_worktree, tid_b, TicketState.PLANNED).is_ok
        assert transition(second_worktree, tid_b, TicketState.IN_PROGRESS).is_ok

        assert same_worktree_lease(second_worktree, tid_b, tid_a) is False


# frob:ticket T-1883
class TestDoableExcludesSameWorktreeLeases:
    """The bug T-1883 fixes: `doable --show-blocked`'s underlying
    `leased_by`/`doable` must not report a same-worktree lease as a blocker
    -- a grouped dispatch (several tickets sharing scope, one worktree, one
    agent) must never self-block. A genuinely different worktree's colliding
    lease must still block, unchanged."""

    def test_same_worktree_colliding_leases_do_not_block_each_other(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestDoableExcludesSameWorktreeLea\
        # ses.test_same_worktree_colliding_leases_do_not_block_each_other
        created_a = new_ticket(repo, _spec("Ticket A", scope=("docs/shared.md",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(repo, tid_a, TicketState.PLANNED).is_ok
        assert transition(repo, tid_a, TicketState.IN_PROGRESS).is_ok

        created_b = new_ticket(repo, _spec("Ticket B", scope=("docs/shared.md",)))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        assert transition(repo, tid_b, TicketState.PLANNED).is_ok
        assert transition(repo, tid_b, TicketState.IN_PROGRESS).is_ok

        loaded = load_all(repo)
        assert loaded.is_ok
        queue = TicketQueue(tickets=loaded.danger_ok)

        holds_a = leased_by(queue, queue.tickets[tid_a], repo)
        holds_b = leased_by(queue, queue.tickets[tid_b], repo)
        assert not any(holder_id == tid_b for holder_id, _glob in holds_a)
        assert not any(holder_id == tid_a for holder_id, _glob in holds_b)

    def test_cross_worktree_colliding_lease_still_blocks(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestDoableExcludesSameWorktreeLea\
        # ses.test_cross_worktree_colliding_lease_still_blocks
        created_a = new_ticket(repo, _spec("Ticket A", scope=("docs/shared.md",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(repo, tid_a, TicketState.PLANNED).is_ok
        assert transition(repo, tid_a, TicketState.IN_PROGRESS).is_ok

        created_b = new_ticket(
            second_worktree, _spec("Ticket B collides", scope=("docs/shared.md",))
        )
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id

        loaded = load_all(second_worktree)
        assert loaded.is_ok
        queue = TicketQueue(tickets=loaded.danger_ok)
        ticket_b = queue.tickets[tid_b]

        holds = leased_by(queue, ticket_b, second_worktree)
        assert any(holder_id == tid_a for holder_id, _glob in holds)

        offered = doable(queue, second_worktree)
        assert all(t.id != tid_b for t in offered)
