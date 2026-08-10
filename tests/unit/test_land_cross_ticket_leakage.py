"""T-1355: regression tests for `frob.tickets._land`'s cross-ticket
leakage preflight (`_check_cross_ticket_leakage`) -- the incident class
where landing one ticket out of a multi-ticket series worktree silently
carries a SIBLING ticket's own committed, still-open work onto main. Real
git fixture repos throughout (matching `tests/test_ticket_land.py`'s own
style for this module), not mocks -- the whole point is real `git merge
--squash` behavior against a real worktree branch.

The real incident this reproduces: worktree t-1276 hosted T-1276 (paused,
still `in-progress`) and T-1352 (an independent fix). Landing T-1352
carried T-1276's own committed files onto main while T-1276's ledger
state stayed `in-progress` -- main shipped code whose ticket the ledger
says is still open."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land
from frob.tickets._models import LandError
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="fixture-repo git-init boilerplate already duplicated \
# verbatim across tests/test_ticket_land.py, tests/test_ticket_merge_driver.py, \
# tests/test_tickets_collision.py, and others -- each land/ticket test module owns its \
# own tiny copy rather than importing across test files (the existing convention this \
# repo's test suite already follows for fixture helpers)"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


# frob:waive DUP001 reason="fixture-repo git-commit boilerplate already duplicated \
# verbatim across several land/ticket test modules -- see _git_init's waiver above for \
# the same rationale"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


# frob:waive DUP001 reason="fixture-repo ticket-closeability boilerplate (planned -> \
# in-progress + minimal evidence/Done-report) already duplicated verbatim in \
# tests/test_ticket_land.py -- see _git_init's waiver above for the same rationale"
def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept:
    planned -> in-progress, evidence + Done report attached."""
    assert transition(root, ticket_id, TicketState.PLANNED).is_ok
    assert transition(root, ticket_id, TicketState.IN_PROGRESS).is_ok
    loaded = load_all(root)
    ticket = loaded.danger_ok[ticket_id]
    ticket = ticket.model_copy(
        update={
            "evidence": ("tests/test_x.py::test_ok",),
            "body": ticket.body + "\n## Done report\n\nevidence attached\n",
        }
    )
    assert write_ticket(root, ticket).is_ok


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger and one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


# frob:ticket T-1639
class TestCrossTicketLeakage:
    """`land()` refuses when the branch carries a sibling ticket's own
    committed, still-open work -- unless explicitly overridden."""

    def _seed_two_ticket_worktree(self, repo: Path) -> tuple[Path, str, str]:
        """One worktree hosting two tickets, mirroring the real T-1276/
        T-1352 series-worktree shape: `held.py` is committed under the
        FIRST ticket's own declared scope and left `in-progress`
        (deliberately paused); `fix.py` is a disjoint, independent second
        ticket's own change, ready to land."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], repo)

        held = new_ticket(wt, _spec("Paused work", scope=("src/held.py",)))
        assert held.is_ok
        held_id = held.danger_ok.id
        assert transition(wt, held_id, TicketState.PLANNED).is_ok
        assert transition(wt, held_id, TicketState.IN_PROGRESS).is_ok
        (wt / "src" / "held.py").write_text(
            "# T-held's own work, deliberately paused\n"
        )
        _commit_all(wt, f"{held_id}: paused work in flight")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        return wt, held_id, landing_id

    def test_refuses_when_sibling_ticket_still_open(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage kind="unit"
        # T-1370: the genuine cross-AGENT leak the guard exists for -- the
        # held ticket is leased to a DIFFERENT worktree (`wt2`, standing in
        # for a different agent's own series) than the one landing (`wt`),
        # so the T-1370 same-worktree exemption must NOT apply here.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], repo)
        wt2 = repo.parent / "wt2"
        _run(["git", "worktree", "add", "-b", "other-agent", str(wt2)], repo)

        held = new_ticket(wt2, _spec("Paused work", scope=("src/held.py",)))
        assert held.is_ok
        held_id = held.danger_ok.id
        assert transition(wt2, held_id, TicketState.PLANNED).is_ok
        # Leases held_id to wt2, NOT wt.
        assert transition(wt2, held_id, TicketState.IN_PROGRESS).is_ok

        # Simulate held_id's work (and its ledger entry) leaking onto
        # wt's branch -- e.g. a bad merge -- despite being leased
        # elsewhere: a real cross-agent leak, not legitimate sharing.
        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "held.py").write_text(
            "# leaked from a different agent's worktree\n"
        )
        held_ticket = load_all(wt2).danger_ok[held_id]
        assert write_ticket(wt, held_ticket).is_ok
        _commit_all(wt, f"{held_id}: leaked onto series-a")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.CrossTicketLeakage
        # Nothing landed: main's tree is untouched.
        assert not (repo / "src" / "fix.py").exists()
        assert not (repo / "src" / "held.py").exists()

    def test_allow_cross_ticket_overrides_the_refusal(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage kind="unit"
        wt, held_id, landing_id = self._seed_two_ticket_worktree(repo)

        result = land(repo, landing_id, wt, dry_run=False, allow_cross_ticket=True)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

    def test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage kind="unit"
        # Sanity check: a single-ticket worktree (the common case) is
        # entirely unaffected by the new preflight.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo", str(wt)], repo)
        created = new_ticket(wt, _spec("Solo work", scope=("src/solo.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "solo.py").write_text("# solo work\n")
        _commit_all(wt, "add solo work")

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "solo.py").exists()

    # frob:ticket T-1967
    def test_sibling_leased_to_same_worktree_does_not_block(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_find_leaked_tickets kind="unit"
        # T-1967 CORRECTION (function name kept for T-1370/T-1639 evidence
        # resolution -- both are DONE tickets citing this node id; renaming
        # it would break their COV003 evidence): this test used to assert
        # the OLD, buggy behavior -- an in-progress sibling sharing the
        # worktree was silently exempted no matter what. That exemption
        # was measured to be the exact guard hole T-1967 fixed (T-1958's
        # docs-only land silently carrying T-1956's entire production
        # change onto main, no flag, no warning). The correct behavior,
        # asserted below, is the opposite of what this test's name says:
        # a same-worktree sibling with real committed hits now REFUSES
        # like any other leaked ticket, unless explicitly acknowledged
        # (see test_sibling_leased_to_same_worktree_lands_with_explicit_
        # ack immediately below for that acknowledgment path).
        wt, held_id, landing_id = self._seed_two_ticket_worktree(repo)

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.CrossTicketLeakage
        assert not (repo / "src" / "fix.py").exists()
        assert not (repo / "src" / "held.py").exists()

    # frob:ticket T-1967
    def test_sibling_leased_to_same_worktree_lands_with_explicit_ack(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_find_leaked_tickets kind="unit"
        # T-1967: the same shape as the refusal test above, but with the
        # operator explicitly acknowledging the carry via the existing
        # `--allow-cross-ticket` escape hatch -- the real T-1370 deadlock
        # concern (two mutually-scoped same-worktree tickets, neither
        # landable) is resolved this way, not by silence.
        wt, held_id, landing_id = self._seed_two_ticket_worktree(repo)

        result = land(repo, landing_id, wt, dry_run=False, allow_cross_ticket=True)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()
        assert (repo / "src" / "held.py").exists()

    def test_sibling_ticket_already_done_on_main_does_not_block(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage kind="unit"
        # A ticket whose scope overlaps the changeset but is ALREADY done
        # (terminal) on main is not a leakage hazard -- its work already
        # shipped legitimately, so it must not block an unrelated land.
        wt, held_id, landing_id = self._seed_two_ticket_worktree(repo)

        # Mark the "held" ticket done directly on root's ledger (simulating
        # it having landed through its own, earlier `frob ticket land`).
        # held_id does not exist on root yet (only in the worktree) --
        # seed a minimal done copy on root instead, matching what a real
        # prior land would have produced.
        held_ticket = load_all(wt).danger_ok[held_id]
        done_ticket = held_ticket.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(repo, done_ticket).is_ok
        _commit_all(repo, f"seed {held_id} as already-done on main")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_ok, result.err

    def test_sibling_declaring_broad_scope_but_untouched_does_not_block(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_find_leaked_tickets kind="unit"
        # T-1390: the measured false-positive class -- an UNRELATED open
        # ticket (never leased to this worktree, never worked on this
        # branch) merely DECLARES a broad scope ("src/**") that happens to
        # cover a file this branch legitimately changes. Its own ledger
        # record never moves on this branch, so it must not block the
        # land even though its declared scope matches.
        broad = new_ticket(repo, _spec("Broad-scope backlog item", scope=("src/**",)))
        assert broad.is_ok
        broad_id = broad.danger_ok.id
        assert transition(repo, broad_id, TicketState.PLANNED).is_ok
        assert transition(repo, broad_id, TicketState.IN_PROGRESS).is_ok
        _commit_all(repo, f"seed {broad_id}: broad-scope backlog item, in-progress")

        # The worktree forks AFTER broad_id already exists on main, so its
        # ledger record is identical at the fork point and now -- nothing
        # in this branch ever touches broad_id.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-broad", str(wt)], repo)
        created = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text("# independent fix, unrelated to broad_id\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()
        assert (repo / "src" / "fix.py").exists()

    # frob:tests \
    # tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage.test_queued_\
    # sibling_scope_overlap_does_not_block
    # frob:ticket T-1639
    def test_queued_sibling_scope_overlap_does_not_block(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_find_leaked_tickets kind="unit"
        # T-1639: the real 2026-08-06 incident shape -- a freshly filed,
        # never-started (QUEUED) sibling declaring a scope that happens to
        # cover a changed path must not refuse the land at all. A declared
        # scope on an unstarted ticket is an intention, not a claim; only
        # an IN_PROGRESS sibling (a real concurrent writer with real
        # commits) may refuse.
        queued = new_ticket(
            repo, _spec("Freshly filed backlog item", scope=("src/**",))
        )
        assert queued.is_ok
        queued_id = queued.danger_ok.id
        # Deliberately left QUEUED -- never planned, never started, no
        # lease, no commits of its own anywhere.
        _commit_all(repo, f"seed {queued_id}: freshly filed, queued")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-queued", str(wt)], repo)
        created = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text(
            "# independent fix, unrelated to queued_id\n"
        )
        _commit_all(wt, f"{landing_id}: independent fix")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

    # frob:ticket T-1639
    # frob:tests \
    # tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage.test_planned\
    # _sibling_scope_overlap_does_not_block
    # frob:ticket T-1639
    def test_planned_sibling_scope_overlap_does_not_block(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_find_leaked_tickets kind="unit"
        # T-1639: PLANNED (the pre-work-sweep state `frob ticket start`
        # sets before a worktree/lease exists) is the same "not actually
        # being worked yet" shape as QUEUED -- must not refuse either.
        planned = new_ticket(repo, _spec("Planned backlog item", scope=("src/**",)))
        assert planned.is_ok
        planned_id = planned.danger_ok.id
        assert transition(repo, planned_id, TicketState.PLANNED).is_ok
        _commit_all(repo, f"seed {planned_id}: planned, not started")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-planned", str(wt)], repo)
        created = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text(
            "# independent fix, unrelated to planned_id\n"
        )
        _commit_all(wt, f"{landing_id}: independent fix")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

    # frob:ticket T-1999
    def test_live_lease_refuses_even_when_roots_ledger_still_reads_planned(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_find_leaked_tickets kind="unit"
        # T-1999 (MUST FAIL on the pre-fix code): the exact measured
        # repro -- held_id already exists on ROOT's own ledger (a real
        # ticket, not merely worktree-local), so `_find_leaked_tickets`
        # trusts root_tickets[held_id].state over the worktree's own
        # copy. The landing worktree starts held_id FOR REAL (taking its
        # cross-worktree lease and flipping its OWN ledger copy to
        # in-progress), but that transition never gets merged back into
        # root -- root's ledger keeps reading `state: planned` the whole
        # time, exactly like T-1977's land of T-1665 (main observed
        # `planned` while T-1665's worktree held a live lease). Pre-fix,
        # root's stale `planned` silently won and the land went through
        # clean; post-fix, the live lease makes held_id count as
        # effectively IN_PROGRESS and the land must refuse.
        held = new_ticket(repo, _spec("Held work", scope=("src/held.py",)))
        assert held.is_ok
        held_id = held.danger_ok.id
        assert transition(repo, held_id, TicketState.PLANNED).is_ok
        _commit_all(repo, f"seed {held_id}: planned, not yet started")

        # Landing worktree forks after held_id exists (planned) on root.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-live-lease", str(wt)], repo)

        # wt genuinely starts held_id: takes its cross-worktree lease and
        # flips wt's OWN ledger copy to in-progress -- but this never
        # gets merged back into root, so root's copy stays `planned`.
        assert transition(wt, held_id, TicketState.IN_PROGRESS).is_ok
        (wt / "src" / "held.py").write_text("# covered by held_id's scope\n")
        _commit_all(wt, f"{held_id}: file under held_id's scope, on the landing branch")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text(
            "# independent fix, unrelated to held_id\n"
        )
        _commit_all(wt, f"{landing_id}: independent fix")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.CrossTicketLeakage
        assert not (repo / "src" / "fix.py").exists()
        assert not (repo / "src" / "held.py").exists()


# frob:ticket T-1618
class TestPassengerTickets:
    """`_check_passenger_tickets` -- the T-1618 fix. Unlike
    `TestCrossTicketLeakage` above, this scans the branch diff's own
    `frob:ticket <id>` directive additions directly, independent of ANY
    sibling ticket's ledger state -- reproducing the real 2026-08-05
    incident shape: a sibling ticket judged unsafe and reverted IN ITS OWN
    WORKTREE, whose code still physically rode onto main via a DIFFERENT
    ticket's land because nothing disclosed it was there."""

    def test_refuses_and_lists_every_passenger_by_id(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_passenger_tickets kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], repo)

        passenger = new_ticket(wt, _spec("Passenger work", scope=("src/passenger.py",)))
        assert passenger.is_ok
        passenger_id = passenger.danger_ok.id
        (wt / "src" / "passenger.py").write_text(
            f"# frob:ticket {passenger_id}\ndef passenger_fn():\n    pass\n"
        )
        _commit_all(wt, f"{passenger_id}: passenger's own work")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.PassengerTickets
        # Nothing landed at all -- neither file made it onto main.
        assert not (repo / "src" / "fix.py").exists()
        assert not (repo / "src" / "passenger.py").exists()

    def test_allow_cross_ticket_logs_and_proceeds(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_passenger_tickets kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-b", str(wt)], repo)

        passenger = new_ticket(wt, _spec("Passenger work", scope=("src/passenger.py",)))
        assert passenger.is_ok
        passenger_id = passenger.danger_ok.id
        (wt / "src" / "passenger.py").write_text(f"# frob:ticket {passenger_id}\n")
        _commit_all(wt, f"{passenger_id}: passenger's own work")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        with caplog.at_level("WARNING"):
            result = land(repo, landing_id, wt, dry_run=False, allow_cross_ticket=True)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()
        assert (repo / "src" / "passenger.py").exists()
        assert passenger_id in caplog.text

    def test_no_op_when_only_the_landing_tickets_own_directives_are_present(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_passenger_tickets kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-directive", str(wt)], repo)

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text(f"# frob:ticket {landing_id}\n")
        _commit_all(wt, f"{landing_id}: independent fix, own directive only")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

    def test_a_dropped_siblings_still_present_code_is_still_reported(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_passenger_tickets kind="unit"
        # The exact T-1618 gap: `_check_cross_ticket_leakage` exempts a
        # DONE/DROPPED sibling outright (`_find_leaked_tickets`'s own
        # `effective_state in (DONE, DROPPED): continue`). A directive-
        # based passenger check must NOT share that blind spot -- a
        # sibling's code riding along onto main is exactly as dangerous
        # whether its own ticket record says DROPPED or IN_PROGRESS.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-c", str(wt)], repo)

        passenger = new_ticket(
            wt, _spec("Rejected work", scope=("src/rejected.py",))
        )
        assert passenger.is_ok
        passenger_id = passenger.danger_ok.id
        (wt / "src" / "rejected.py").write_text(f"# frob:ticket {passenger_id}\n")
        _commit_all(wt, f"{passenger_id}: work later judged unsafe")

        # Mark it DROPPED on root's ledger directly -- simulating the
        # incident's "reverted in the worktree" step having, at minimum,
        # updated the ticket's own state to a terminal one, even though
        # (per the incident) the CODE itself never actually left the
        # branch.
        dropped_ticket = load_all(wt).danger_ok[passenger_id]
        dropped_ticket = dropped_ticket.model_copy(
            update={"state": TicketState.DROPPED}
        )
        assert write_ticket(repo, dropped_ticket).is_ok
        _commit_all(repo, f"seed {passenger_id}: dropped on main")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.PassengerTickets
        assert not (repo / "src" / "fix.py").exists()
