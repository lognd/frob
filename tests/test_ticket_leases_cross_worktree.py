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
    add_evidence,
    doable,
    leased_by,
    load_all,
    mutate_scope,
    new_ticket,
    set_done_report,
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

    # frob:ticket T-2271
    def test_scope_change_while_queued_then_start_leases_with_post_change_scope(
        self, repo: Path, second_worktree: Path
    ) -> None:
        """T-2271's suspected mechanism: a `scope --add` while the ticket is
        still QUEUED (before `_auto_plan_if_queued`'s own queued->planned
        write), immediately followed by the planned->in-progress
        transition. `mutate_scope` does not record a lease for a
        not-yet-in-progress ticket (correctly -- there is nothing to lease
        yet), so the only recording opportunity is the IN_PROGRESS
        transition itself; this proves it fires with the POST-change
        scope, not a stale pre-change snapshot."""
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_scope_change_while_queued_then_start_leases_with_post_change_scope
        (repo / "src" / "other.py").write_text("# other\n")
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id

        # Ticket is still QUEUED here -- mirrors T-2259's own git history
        # (four `scope` commits before the start transition).
        mutated = mutate_scope(
            repo, tid, add=("src/other.py",), reason="widen before start"
        )
        assert mutated.is_ok
        assert not any(lease.ticket_id == tid for lease in read_all_leases(repo)), (
            "a QUEUED ticket must not hold a lease yet"
        )

        # `_auto_plan_if_queued` + the IN_PROGRESS transition, exactly as
        # `frob ticket start` drives them.
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        leases = read_all_leases(second_worktree)
        held = next((lease for lease in leases if lease.ticket_id == tid), None)
        assert held is not None, (
            "the in-progress transition must record a lease even when a "
            "scope change happened first, in the same worktree, while "
            "still queued"
        )
        assert "src/other.py" in held.scope
        assert "src/feature.py" in held.scope

    # frob:ticket T-2271
    def test_local_close_releases_the_lease_before_a_second_worktree_sees_done(
        self, repo: Path, second_worktree: Path
    ) -> None:
        """T-2271's ACTUAL mechanism (not the suspected scope-change one):
        `frob ticket land`'s own `_land_finalize_and_close` transitions a
        ticket to DONE in the WORKTREE, releasing the shared cross-worktree
        lease immediately, BEFORE the merge commit reaches the primary
        checkout's own copy of `tickets/<id>/ticket.md` (`_land_squash_
        apply` is a later, separate step). A ticket can therefore read
        in-progress from `second_worktree`'s own local ledger view while
        already holding NO shared lease at all -- this is the exact shape
        T-2271 was filed from (T-2259: `state: in-progress` on main, no
        `.git/frob-leases/T-2259.json`), reproduced here directly against
        `transition`/`read_all_leases` with no `_land.py` involved at all:
        `_sync_cross_worktree_lease` releases synchronously and
        unconditionally the moment `from_state is IN_PROGRESS`, regardless
        of whether any OTHER worktree's own ledger copy has caught up to
        the same state yet. Not a bug in the recorder -- the lease and a
        stale peer worktree's ticket-state READ answer different
        questions, exactly the distinction this ticket's own 'do not
        infer occupancy from state' constraint protects."""
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_local_close_releases_the_lease_before_a_second_worktree_sees_done
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok
        assert any(lease.ticket_id == tid for lease in read_all_leases(second_worktree))

        # `second_worktree`'s own local ledger has never seen this ticket
        # at all -- it never merged/pulled `repo`'s commits, exactly like
        # the primary checkout's `tickets/<id>/ticket.md` before a land's
        # squash-apply step reaches it.
        stale_view = load_all(second_worktree)
        assert stale_view.is_ok
        assert tid not in stale_view.danger_ok

        # `repo` (standing in for the worktree land finalizes in) closes
        # the ticket LOCALLY, exactly what `_finalize_and_close_ticket`
        # does before `_land_squash_apply` ever touches the primary
        # checkout.
        assert add_evidence(repo, tid, ["tests/test_x.py::test_a"]).is_ok
        assert set_done_report(repo, tid, why="did the thing").is_ok
        assert transition(repo, tid, TicketState.DONE).is_ok

        # The shared lease is gone immediately...
        assert not any(
            lease.ticket_id == tid for lease in read_all_leases(second_worktree)
        )
        # ...even though `second_worktree`'s OWN ledger view still has no
        # record of this ticket at all (the pre-merge equivalent of a
        # peer's stale "state: in-progress" read) -- proving the lease
        # answers "is anyone actively holding this right now", not
        # "does every peer's ledger copy agree on the current state".
        assert tid not in load_all(second_worktree).danger_ok


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


# frob:ticket T-1993
class TestLeaseDeltaReconciliation:
    """T-1993: `mutate_scope`'s cross-worktree lease write must never revert
    a NARROWER scope another worktree already recorded, just because a
    STALE worktree (one that never merged the narrowing commit) runs its
    OWN legitimate scope mutation afterward -- the confirmed 2026-08-10
    incident (T-1696): the `profile-collapse` worktree still carried the
    ledger's OLD, broader scope on disk, and its own `scope --add` call
    re-recorded the shared lease from that stale snapshot, silently
    reverting a sibling worktree's already-landed narrowing."""

    def test_stale_worktrees_add_does_not_revert_a_siblings_narrowing(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestLeaseDeltaReconciliation.test\
        # _stale_worktrees_add_does_not_revert_a_siblings_narrowing
        created = new_ticket(
            repo, _spec("Feature", scope=("src/feature.py", "src/other.py"))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok
        _commit_all(repo, "start ticket")

        # second_worktree merges up through the START commit -- it has the
        # ticket's ORIGINAL (broad) scope on disk, matching the shared
        # lease at this point.
        _run(["git", "merge", "main"], second_worktree)
        held = next(
            lease
            for lease in read_all_leases(second_worktree)
            if lease.ticket_id == tid
        )
        assert set(held.scope) == {"src/feature.py", "src/other.py"}

        # repo (the OWNING worktree) narrows the scope and commits it --
        # but second_worktree never merges this commit, so its own on-disk
        # ticket.md stays on the pre-narrowing snapshot.
        narrowed = mutate_scope(
            repo,
            tid,
            remove=("src/other.py",),
            reason="narrow to the real touched file",
        )
        assert narrowed.is_ok
        _commit_all(repo, "narrow scope")
        held = next(lease for lease in read_all_leases(repo) if lease.ticket_id == tid)
        assert held.scope == ("src/feature.py",)

        # second_worktree, still stale, makes its OWN legitimate scope
        # change (adding a brand-new path nobody has touched). Before
        # T-1993, this re-recorded the lease from second_worktree's stale
        # ticket.md (scope=feature.py+other.py), reverting repo's
        # narrowing -- "src/other.py" would reappear in the shared lease.
        added = mutate_scope(
            second_worktree,
            tid,
            add=("src/new_thing.py",),
            reason="also touching a new file",
        )
        assert added.is_ok

        held = next(lease for lease in read_all_leases(repo) if lease.ticket_id == tid)
        assert "src/other.py" not in held.scope
        assert "src/feature.py" in held.scope
        assert "src/new_thing.py" in held.scope

    def test_a_legitimate_expansion_from_the_owning_worktree_still_takes_effect(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestLeaseDeltaReconciliation.test\
        # _a_legitimate_expansion_from_the_owning_worktree_still_takes_effect
        created = new_ticket(repo, _spec("Feature", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        expanded = mutate_scope(
            repo, tid, add=("src/another.py",), reason="also needed"
        )
        assert expanded.is_ok

        held = next(
            lease
            for lease in read_all_leases(second_worktree)
            if lease.ticket_id == tid
        )
        assert set(held.scope) == {"src/feature.py", "src/another.py"}


# frob:ticket T-2095
class TestScopeLeaseConflictPrefersLiveNarrowingOverStaleQueue:
    """T-2095: a narrowing published to the live cross-worktree lease
    side-channel (`mutate_scope` -> `record_lease`, T-0473/T-1993) must
    actually be CONSULTED by `scope_lease_conflict` before a stale local
    ledger's queue-based check refuses a candidate ticket over a path the
    holder has already released.

    Reproduces the exact T-2079/T-2093 shape live-measured on this repo's
    own main: ticket A starts holding a broad scope covering path P (this
    commit lands on `repo`, i.e. main -- matching main's copy of T-2079's
    ticket.md). A's own worktree then narrows away P (matching that
    worktree's copy of the ticket.md, and the live lease `mutate_scope`
    republishes). A THIRD worktree is created from `repo` BEFORE the
    narrowing (never merges it, matching every dispatched agent's
    worktree, which never re-merges main mid-ticket) and tries to start a
    ticket needing only P.

    `_scope_add_queue_conflict` (stale local-ledger check, sees A's
    ORIGINAL broad scope) runs BEFORE `_scope_add_live_lease_conflict`
    (fresh side-channel check, sees A's narrowed scope) inside
    `_scope_add_conflicts`, and returns its own stale conflict immediately
    without ever consulting the live, authoritative lease -- so this
    currently refuses a candidate whose only overlap is a path the holder
    has already released. Must be `None` after the fix."""

    def test_narrowed_away_path_is_not_blocked_by_a_stale_local_queue(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestScopeLeaseConflictPrefersLive\
        # NarrowingOverStaleQueue.test_narrowed_away_path_is_not_blocked_by_a_stale_loc\
        # al_queue
        from frob.tickets._scope import scope_lease_conflict

        (repo / "src" / "other.py").write_text("# other\n")
        _commit_all(repo, "add src/other.py")

        # Ticket A starts directly on `repo` (main), holding a broad scope
        # that covers both `src/feature.py` (the path a later candidate
        # needs) and `src/other.py` (a path it keeps).
        created_a = new_ticket(
            repo,
            _spec("Feature A", scope=("src/feature.py", "src/other.py")),
        )
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(repo, tid_a, TicketState.PLANNED).is_ok
        assert transition(repo, tid_a, TicketState.IN_PROGRESS).is_ok
        # `transition()` (the low-level API used here, matching this
        # module's other direct-API tests) writes the state change into
        # `repo`'s ticket file but does not commit it -- only the CLI's
        # `frob ticket start` (`commit_start_transition`) does that. A
        # `git worktree add` below clones from the last COMMIT, so the
        # in-progress transition must be committed first or every new
        # worktree would see the ticket as still QUEUED.
        _commit_all(repo, "start T-0001")

        # Worktree A: A's own agent worktree, cut from `repo`'s current
        # tip -- its local ticket.md still matches main's broad scope at
        # this point.
        worktree_a = repo.parent / "wt-a"
        _run(["git", "worktree", "add", "-b", "agent-a", str(worktree_a)], repo)

        # Worktree C: a THIRD, independent agent worktree cut from the
        # SAME tip as worktree_a -- before A's narrowing exists anywhere.
        # It never merges anything from worktree_a; this is the stale
        # local-ledger view every dispatched agent's fresh worktree has.
        worktree_c = repo.parent / "wt-c"
        _run(["git", "worktree", "add", "-b", "agent-c", str(worktree_c)], repo)

        # A narrows in ITS OWN worktree, releasing src/feature.py -- this
        # updates worktree_a's local ticket.md AND (per mutate_scope's
        # T-0473/T-1993 contract) republishes the narrowed scope onto the
        # shared live lease. Never merged into `repo` or worktree_c.
        narrowed = mutate_scope(
            worktree_a,
            tid_a,
            remove=("src/feature.py",),
            reason="T-2095 repro: release src/feature.py for others",
        )
        assert narrowed.is_ok

        # Acceptance criterion 2: the narrowing published via the ONLY
        # mechanism this fix relies on (the existing lease side-channel,
        # T-0473/T-1993) -- worktree_a never wrote main's (`repo`'s) own
        # ticket file directly, and `repo` (the shared root in this
        # scenario) is not left dirty by worktree_a's mutation.
        main_view = load_all(repo)
        assert main_view.is_ok
        assert "src/feature.py" in main_view.danger_ok[tid_a].scope
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo),
            check=True,
            capture_output=True,
            text=True,
        )
        assert status.stdout.strip() == ""

        # Confirm the premise: worktree_c's own local ledger still shows
        # A's ORIGINAL broad scope (it never merged worktree_a's commit).
        local_queue = load_all(worktree_c)
        assert local_queue.is_ok
        assert "src/feature.py" in local_queue.danger_ok[tid_a].scope

        # Confirm the premise: the live lease HAS already narrowed away
        # src/feature.py, visible from worktree_c via the shared
        # side-channel.
        live = next(
            lease for lease in read_all_leases(worktree_c) if lease.ticket_id == tid_a
        )
        assert "src/feature.py" not in live.scope

        # The actual bug: a candidate ticket in worktree_c needing ONLY
        # the already-released src/feature.py must not collide with A --
        # the live lease (fresher, narrower) must be consulted rather
        # than the stale local queue's broad scope.
        conflict = scope_lease_conflict(
            "T-9999-candidate",
            ("src/feature.py",),
            dict(local_queue.danger_ok),
            root=worktree_c,
        )
        assert conflict is None
