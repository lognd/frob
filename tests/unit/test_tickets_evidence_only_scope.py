"""T-1944: `evidence_scope` -- separating evidence coverage from write
lease. Citing a PRE-EXISTING test as evidence used to require adding its
file to `scope` to satisfy D-02 (`evidence_covers_scope`), which then
ALSO claimed a write lease on that file via `_scope_add_conflicts`/
`_find_leaked_tickets` (both read `scope` alone) -- the confirmed T-1686
incident: an epic with zero lines of code changed, permanently leasing
the repo's highest-traffic land test file, unable to release it because
`scope --remove` correctly refused via `ScopeRemoveOrphansEvidence`.

Fixture style matches `tests/test_tickets_scope_mutation.py` (no git
worktree needed -- plain `tmp_path` ledger)."""

from __future__ import annotations

from pathlib import Path

from frob.tickets import (
    Origin,
    TicketKind,
    TicketState,
    add_evidence,
    demote_to_evidence_only,
    load_queue,
    new_ticket,
    transition,
)
from frob.tickets._models import TicketError, TicketSpec
from frob.tickets._scope import mutate_scope, scope_lease_conflict


def _make_ticket(
    root: Path,
    *,
    scope: tuple[str, ...] = (),
    state: TicketState = TicketState.QUEUED,
) -> str:
    spec = TicketSpec(
        title=f"evidence-only-scope fixture ({state})",
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        scope=scope,
    )
    created = new_ticket(root, spec)
    assert created.is_ok, created
    ticket_id = created.danger_ok.id
    if state is TicketState.IN_PROGRESS:
        assert transition(root, ticket_id, TicketState.PLANNED).is_ok
        assert transition(root, ticket_id, TicketState.IN_PROGRESS).is_ok
    return ticket_id


class TestAddEvidenceAutoPopulatesEvidenceOnlyScope:
    """T-3141: `add_evidence` must NEVER auto-populate `evidence_scope`
    for an arbitrary cited node -- the original T-1944 landing did
    exactly that (unconditionally, for any node id not already covered),
    which made D-02 (`evidence_covers_scope`) tautological: evidence_
    scope's own self-cover route then always matched the very evidence
    id that had just widened it, so ANY cited evidence -- however
    unrelated -- satisfied close/land
    (`tests/system/test_cli_evidence_enforcement.py::
    TestCliEvidenceEnforcementEndToEnd.test_close_fails_on_unrelated_
    evidence`, D-02's own end-to-end repro, caught this live). The
    deliberate, reasoned remedy for T-1944's real scenario (a pre-
    existing, genuinely-covering test wrongly forced into `scope` and
    thus leased) is `demote_to_evidence_only` (see `TestDemoteToEvidence
    Only` below) -- not an automatic side effect of every `--evidence`
    citation."""

    # frob:ticket T-1944
    # frob:ticket T-3141
    def test_new_evidence_widens_evidence_scope_not_scope(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesE\
        # videnceOnlyScope.test_new_evidence_widens_evidence_scope_not_scope
        # T-3141: name kept (T-1944's own recorded evidence cites it) --
        # the BODY now asserts the corrected behavior: `add_evidence`
        # no longer auto-widens `evidence_scope` at all.
        ticket_id = _make_ticket(tmp_path, scope=("src/fix.py",))

        result = add_evidence(tmp_path, ticket_id, ["tests/test_existing.py::test_ok"])
        assert result.is_ok, result

        updated = result.danger_ok
        assert updated.scope == ("src/fix.py",)
        assert updated.evidence_scope == ()

    # frob:ticket T-1944
    def test_evidence_already_covered_by_scope_widens_nothing(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesE\
        # videnceOnlyScope.test_evidence_already_covered_by_scope_widens_nothing
        ticket_id = _make_ticket(tmp_path, scope=("tests/test_existing.py",))

        result = add_evidence(tmp_path, ticket_id, ["tests/test_existing.py::test_ok"])
        assert result.is_ok, result

        updated = result.danger_ok
        assert updated.scope == ("tests/test_existing.py",)
        assert updated.evidence_scope == ()


class TestEvidenceOnlyScopeNeverLeases:
    """A path present ONLY in `evidence_scope` never conflicts with
    another ticket's `--add` and is invisible to the lease-conflict
    predicate -- the whole point of T-1944's fix. T-3141: `evidence_
    scope` is reached here via the deliberate `demote_to_evidence_only`
    (matching `TestDemoteToEvidenceOnly`), not via plain `add_evidence`,
    which no longer auto-populates it."""

    # frob:ticket T-1944
    # frob:ticket T-3141
    def test_evidence_scope_path_does_not_block_another_tickets_add(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceOnlyScopeNeverLea\
        # ses.test_evidence_scope_path_does_not_block_another_tickets_add
        holder_id = _make_ticket(
            tmp_path,
            scope=("tests/test_ticket_land.py",),
            state=TicketState.IN_PROGRESS,
        )
        result = add_evidence(
            tmp_path, holder_id, ["tests/test_ticket_land.py::test_ok"]
        )
        assert result.is_ok, result

        demoted = demote_to_evidence_only(
            tmp_path,
            holder_id,
            ["tests/test_ticket_land.py"],
            reason="T-3141 fixture: exercise the non-leasing invariant via the "
            "deliberate demote path",
        )
        assert demoted.is_ok, demoted
        assert demoted.danger_ok.evidence_scope == ("tests/test_ticket_land.py",)

        queue = load_queue(tmp_path).danger_ok
        conflict = scope_lease_conflict(
            "T-9999",
            ("tests/test_ticket_land.py",),
            dict(queue.tickets),
            root=tmp_path,
        )
        assert conflict is None


class TestEvidenceCoversScopeWithEvidenceOnlyScope:
    """D-02 (`evidence_covers_scope`) treats `evidence_scope` exactly
    like `scope` for coverage purposes -- moving a path out of `scope`
    and into `evidence_scope` never makes the ticket's own evidence stop
    counting as covered."""

    # frob:ticket T-1944
    # frob:ticket T-3141
    def test_evidence_covers_scope_true_via_evidence_scope_alone(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceCoversScopeWithEv\
        # idenceOnlyScope.test_evidence_covers_scope_true_via_evidence_scope_alone
        from frob.gates import evidence_covers_scope
        from frob.graph import GraphSnapshot

        # T-3141: `evidence_scope` reached via the deliberate `demote_to_
        # evidence_only`, not plain `add_evidence` (which no longer
        # auto-populates it -- see `TestAddEvidenceAutoPopulatesEvidence
        # OnlyScope`'s corrected docstring).
        ticket_id = _make_ticket(
            tmp_path, scope=("tests/test_existing.py",), state=TicketState.IN_PROGRESS
        )
        result = add_evidence(tmp_path, ticket_id, ["tests/test_existing.py::test_ok"])
        assert result.is_ok, result

        demoted = demote_to_evidence_only(
            tmp_path,
            ticket_id,
            ["tests/test_existing.py"],
            reason="T-3141 fixture: exercise evidence_scope-alone coverage via the "
            "deliberate demote path",
        )
        assert demoted.is_ok, demoted
        updated = demoted.danger_ok
        assert updated.scope == ()
        assert updated.evidence_scope == ("tests/test_existing.py",)

        empty_snapshot = GraphSnapshot(root="", symbols={}, edges=())
        assert evidence_covers_scope(updated, empty_snapshot) is True


class TestDemoteToEvidenceOnly:
    """`demote_to_evidence_only` migrates an EXISTING `scope` entry into
    `evidence_scope` atomically -- the T-1686 remedy: release a write
    lease a ticket never uses without ever leaving D-02 coverage false,
    and without weakening `ScopeRemoveOrphansEvidence` (a plain `scope
    --remove` with no demotion still refuses, tested separately)."""

    # frob:ticket T-1944
    def test_demote_releases_the_lease_and_keeps_evidence_covered(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly.test\
        # _demote_releases_the_lease_and_keeps_evidence_covered
        from frob.gates import evidence_covers_scope
        from frob.graph import GraphSnapshot

        # Reproduce the T-1686 shape: scope --add was the only way to
        # satisfy D-02 for a pre-existing test, before this ticket's fix.
        holder_id = _make_ticket(
            tmp_path,
            scope=("tests/test_ticket_land.py",),
            state=TicketState.IN_PROGRESS,
        )
        bound = add_evidence(
            tmp_path, holder_id, ["tests/test_ticket_land.py::test_ok"]
        )
        assert bound.is_ok, bound

        # Before demotion: the path IS a live lease.
        queue = load_queue(tmp_path).danger_ok
        assert (
            scope_lease_conflict(
                "T-9999",
                ("tests/test_ticket_land.py",),
                dict(queue.tickets),
                root=tmp_path,
            )
            is not None
        )

        demoted = demote_to_evidence_only(
            tmp_path,
            holder_id,
            ["tests/test_ticket_land.py"],
            reason="T-1944: release the unused write lease, evidence stays covered",
        )
        assert demoted.is_ok, demoted
        updated = demoted.danger_ok
        assert updated.scope == ()
        assert updated.evidence_scope == ("tests/test_ticket_land.py",)

        # After demotion: the lease is gone.
        queue = load_queue(tmp_path).danger_ok
        assert (
            scope_lease_conflict(
                "T-9999",
                ("tests/test_ticket_land.py",),
                dict(queue.tickets),
                root=tmp_path,
            )
            is None
        )
        # D-02 coverage never lapsed.
        empty_snapshot = GraphSnapshot(root="", symbols={}, edges=())
        assert evidence_covers_scope(updated, empty_snapshot) is True

    # frob:ticket T-1944
    def test_demote_refuses_an_undeclared_glob(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly.test\
        # _demote_refuses_an_undeclared_glob
        ticket_id = _make_ticket(
            tmp_path, scope=("src/fix.py",), state=TicketState.IN_PROGRESS
        )
        result = demote_to_evidence_only(
            tmp_path, ticket_id, ["never/declared.py"], reason="typo'd path"
        )
        assert result.is_err
        assert result.danger_err == TicketError.ScopeRemoveNotDeclared


class TestScopeRemoveOrphansEvidenceUnweakened:
    """T-1944's explicit constraint: `ScopeRemoveOrphansEvidence` must
    still refuse a plain `scope --remove` when nothing else (neither the
    remaining `scope` nor `evidence_scope`) keeps the evidence covered."""

    # frob:ticket T-1944
    def test_remove_without_demotion_still_refuses(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_tickets_evidence_only_scope.py::TestScopeRemoveOrphansEvidenc\
        # eUnweakened.test_remove_without_demotion_still_refuses
        ticket_id = _make_ticket(
            tmp_path,
            scope=("tests/test_ticket_land.py",),
            state=TicketState.IN_PROGRESS,
        )
        bound = add_evidence(
            tmp_path, ticket_id, ["tests/test_ticket_land.py::test_ok"]
        )
        assert bound.is_ok, bound

        result = mutate_scope(
            tmp_path,
            ticket_id,
            remove=("tests/test_ticket_land.py",),
            reason="trying to shed it the old way, without demoting first",
        )
        assert result.is_err
        assert result.danger_err == TicketError.ScopeRemoveOrphansEvidence
