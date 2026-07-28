"""Tests for T-0455's formal scope/lease change protocol:
`frob.tickets.mutate_scope` (library) and `frob ticket scope` (CLI)
(docs/modules/tickets.md#scope-lease-mutation)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _scope
from frob.tickets import (
    Origin,
    ScopeChangeOp,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    load_queue,
    mutate_scope,
    new_ticket,
    transition,
)
from frob.tickets._models import TicketSpec, _glob_is_subset


def _make_ticket(
    root: Path,
    *,
    scope: tuple[str, ...],
    state: TicketState = TicketState.QUEUED,
) -> Ticket:
    spec = TicketSpec(
        title=f"scope mutation fixture ({state})",
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        scope=scope,
    )
    created = new_ticket(root, spec)
    assert created.is_ok, created
    ticket = created.danger_ok
    if state is TicketState.IN_PROGRESS:
        planned = transition(root, ticket.id, TicketState.PLANNED)
        assert planned.is_ok, planned
        started = transition(root, ticket.id, TicketState.IN_PROGRESS)
        assert started.is_ok, started
        return started.danger_ok
    return ticket


class TestMutateScope:
    def test_add_free_path_granted(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_scope_mutation.py::TestMutateScope.test_add_free_path_gran\
        # ted
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        result = mutate_scope(
            tmp_path,
            ticket.id,
            add=("src/frob/__main__.py",),
            reason="new subcommand registration",
        )
        assert result.is_ok, result
        updated = result.danger_ok
        assert "src/frob/__main__.py" in updated.scope
        assert len(updated.scope_changes) == 1
        entry = updated.scope_changes[0]
        assert entry.op is ScopeChangeOp.ADD
        assert entry.glob == "src/frob/__main__.py"
        assert entry.reason == "new subcommand registration"
        assert entry.at == date.today()

    def test_add_leased_path_rejected_names_holder(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestMutateScope.test_add_leased_path_rejected_names_holder  # noqa: E501
        holder = _make_ticket(
            tmp_path, scope=("src/frob/gates/**",), state=TicketState.IN_PROGRESS
        )
        agent = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        result = mutate_scope(
            tmp_path,
            agent.id,
            add=("src/frob/gates/foo.py",),
            reason="need it",
        )
        assert result.is_err and result.danger_err == TicketError.ScopeLeaseConflict
        queue = load_queue(tmp_path).danger_ok
        assert "src/frob/gates/foo.py" not in queue.tickets[agent.id].scope
        assert holder.state is TicketState.IN_PROGRESS

    def test_add_subset_of_own_leased_overlap_is_accepted(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestMutateScope.test_add_subset_of_own_leased_overlap_is_accepted  # noqa: E501
        # T-0485: a queued ticket whose scope ALREADY grandfathers a glob
        # ('src/frob/strata/**') that overlaps another in-progress ticket's
        # lease must still be allowed to narrow that overlap down to a
        # concrete subset path -- the narrowing strictly shrinks
        # contention, it never creates any.
        holder = _make_ticket(
            tmp_path, scope=("src/frob/strata/**",), state=TicketState.IN_PROGRESS
        )
        agent = _make_ticket(tmp_path, scope=("src/frob/strata/**",))
        result = mutate_scope(
            tmp_path,
            agent.id,
            add=("src/frob/strata/_host.py",),
            reason="narrow to the file actually touched",
        )
        assert result.is_ok, result
        updated = result.danger_ok
        assert "src/frob/strata/_host.py" in updated.scope
        assert holder.state is TicketState.IN_PROGRESS

    def test_add_beyond_own_leased_overlap_still_rejected(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestMutateScope.test_add_beyond_own_leased_overlap_still_rejected  # noqa: E501
        # T-0485 does not open the door to genuine expansion: an add glob
        # that is NOT a subset of anything the ticket already declares
        # must still be refused against a holder's lease.
        _make_ticket(
            tmp_path, scope=("src/frob/gates/**",), state=TicketState.IN_PROGRESS
        )
        agent = _make_ticket(tmp_path, scope=("src/frob/strata/**",))
        result = mutate_scope(
            tmp_path,
            agent.id,
            add=("src/frob/gates/foo.py",),
            reason="need it",
        )
        assert result.is_err and result.danger_err == TicketError.ScopeLeaseConflict

    def test_remove_frees_path_for_other_doable(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestMutateScope.test_remove_frees_path_for_other_doable  # noqa: E501
        from frob.tickets import doable

        holder = _make_ticket(
            tmp_path,
            scope=("src/frob/gates/**", "src/frob/other/**"),
            state=TicketState.IN_PROGRESS,
        )
        other = _make_ticket(tmp_path, scope=("src/frob/gates/**",))

        blocked = doable(load_queue(tmp_path).danger_ok, tmp_path)
        assert other.id not in {t.id for t in blocked}

        removed = mutate_scope(
            tmp_path, holder.id, remove=("src/frob/gates/**",), reason="narrowed"
        )
        assert removed.is_ok, removed

        freed = doable(load_queue(tmp_path).danger_ok, tmp_path)
        assert other.id in {t.id for t in freed}

    def test_remove_not_declared_rejected(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_scope_mutation.py::TestMutateScope.test_remove_not_declare\
        # d_rejected
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        result = mutate_scope(
            tmp_path, ticket.id, remove=("src/frob/nope/**",), reason="x"
        )
        assert result.is_err and result.danger_err == TicketError.ScopeRemoveNotDeclared

    def test_remove_orphaning_evidence_rejected(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestMutateScope.test_remove_orphaning_evidence_rejected  # noqa: E501
        from frob.tickets import add_evidence

        ticket = _make_ticket(tmp_path, scope=("tests/test_scope_fixture.py",))
        evidenced = add_evidence(
            tmp_path,
            ticket.id,
            ["tests/test_scope_fixture.py::test_x"],
            collected=frozenset({"tests/test_scope_fixture.py::test_x"}),
        )
        assert evidenced.is_ok, evidenced
        result = mutate_scope(
            tmp_path,
            ticket.id,
            remove=("tests/test_scope_fixture.py",),
            reason="narrowed",
        )
        assert (
            result.is_err
            and result.danger_err == TicketError.ScopeRemoveOrphansEvidence
        )

    def test_empty_change_rejected(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_scope_mutation.py::TestMutateScope.test_empty_change_rejec\
        # ted
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        result = mutate_scope(tmp_path, ticket.id, reason="nothing to do")
        assert result.is_err and result.danger_err == TicketError.ScopeChangeEmpty

    def test_missing_reason_rejected(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_scope_mutation.py::TestMutateScope.test_missing_reason_rej\
        # ected
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        result = mutate_scope(
            tmp_path, ticket.id, add=("src/frob/__main__.py",), reason="   "
        )
        assert (
            result.is_err and result.danger_err == TicketError.ScopeChangeReasonMissing
        )

    def test_audit_trail_is_append_only(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_scope_mutation.py::TestMutateScope.test_audit_trail_is_app\
        # end_only
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        first = mutate_scope(
            tmp_path, ticket.id, add=("docs/modules/tickets.md",), reason="doc edge"
        )
        assert first.is_ok, first
        second = mutate_scope(
            tmp_path,
            ticket.id,
            remove=("docs/modules/tickets.md",),
            reason="not needed after all",
        )
        assert second.is_ok, second
        assert len(second.danger_ok.scope_changes) == 2
        assert second.danger_ok.scope_changes[0].op is ScopeChangeOp.ADD
        assert second.danger_ok.scope_changes[1].op is ScopeChangeOp.REMOVE


class TestNewFileCarveOut:
    """T-0561: a broad in-progress umbrella lease (e.g. a repo-wide
    `tests/**` coverage epic) must not block another ticket's ADDITIVE,
    brand-new test file from being added to scope -- only a genuine
    same-file race or a non-test-file expansion still refuses.

    frob:ticket T-0561
    frob:ticket T-0422
    """

    # frob:ticket T-0422
    def test_new_file_under_broad_lease_is_exempt(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestNewFileCarveOut.test_new_file_under_broad_lease_is_exempt  # noqa: E501
        # The exact T-0561 repro shape: a broad tests/** epic in progress,
        # another ticket needs to add ONE brand-new test file.
        holder = _make_ticket(
            tmp_path, scope=("tests/**",), state=TicketState.IN_PROGRESS
        )
        agent = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        result = mutate_scope(
            tmp_path,
            agent.id,
            add=("tests/unit/test_app_runners_batch6.py",),
            reason="new regression test for this ticket's fix",
        )
        assert result.is_ok, result
        assert "tests/unit/test_app_runners_batch6.py" in result.danger_ok.scope
        assert holder.state is TicketState.IN_PROGRESS

    # frob:ticket T-0422
    def test_existing_file_under_broad_lease_still_conflicts(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestNewFileCarveOut.test_existing_file_under_broad_lease_still_conflicts  # noqa: E501
        # The carve-out is new-file-only: a test file that already EXISTS
        # on disk (the holder could plausibly be mid-edit on it) is not
        # exempted, even though it is a "test file" by naming convention.
        holder = _make_ticket(
            tmp_path, scope=("tests/**",), state=TicketState.IN_PROGRESS
        )
        agent = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        existing = tmp_path / "tests" / "test_already_here.py"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("def test_x() -> None:\n    pass\n")
        result = mutate_scope(
            tmp_path,
            agent.id,
            add=("tests/test_already_here.py",),
            reason="need it",
        )
        assert result.is_err and result.danger_err == TicketError.ScopeLeaseConflict
        assert holder.state is TicketState.IN_PROGRESS

    # frob:ticket T-0422
    def test_non_test_file_under_broad_lease_still_conflicts(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestNewFileCarveOut.test_non_test_file_under_broad_lease_still_conflicts  # noqa: E501
        # The carve-out is test-file-only: a brand-new, non-existent
        # PRODUCTION source path is still refused against a broader
        # in-progress lease (test_add_leased_path_rejected_names_holder's
        # exact shape) -- non-existence alone is never a sufficient
        # signal, since a real expansion attempt into a not-yet-created
        # module would otherwise slip through.
        holder = _make_ticket(
            tmp_path, scope=("src/frob/gates/**",), state=TicketState.IN_PROGRESS
        )
        agent = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        result = mutate_scope(
            tmp_path,
            agent.id,
            add=("src/frob/gates/_brand_new_module.py",),
            reason="need it",
        )
        assert result.is_err and result.danger_err == TicketError.ScopeLeaseConflict
        assert holder.state is TicketState.IN_PROGRESS

    # frob:ticket T-0422
    def test_new_file_exact_match_of_holder_scope_still_conflicts(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestNewFileCarveOut.test_new_file_exact_match_of_holder_scope_still_conflicts  # noqa: E501
        # A genuine same-file race: the holder ALREADY declares this exact
        # not-yet-existing test file as its own scope entry -- still
        # refused, never silently exempted just because it's a test file.
        holder = _make_ticket(
            tmp_path,
            scope=("tests/unit/test_same_file.py",),
            state=TicketState.IN_PROGRESS,
        )
        agent = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        result = mutate_scope(
            tmp_path,
            agent.id,
            add=("tests/unit/test_same_file.py",),
            reason="need it too",
        )
        assert result.is_err and result.danger_err == TicketError.ScopeLeaseConflict
        assert holder.state is TicketState.IN_PROGRESS


class TestGlobIsSubset:
    def test_concrete_path_under_double_star_is_subset(self) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestGlobIsSubset.test_concrete_path_under_double_star_is_subset  # noqa: E501
        assert _glob_is_subset("src/frob/strata/_host.py", "src/frob/strata/**")

    def test_concrete_path_outside_broad_glob_is_not_subset(self) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestGlobIsSubset.test_concrete_path_outside_broad_glob_is_not_subset  # noqa: E501
        assert not _glob_is_subset("src/frob/gates/foo.py", "src/frob/strata/**")

    def test_wildcard_bearing_narrow_is_never_subset(self) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestGlobIsSubset.test_wildcard_bearing_narrow_is_never_subset  # noqa: E501
        # Conservative by design: a narrow glob that still carries a
        # wildcard is never proven a subset, even if it would appear to be
        # one -- this keeps the check sound rather than approximate.
        assert not _glob_is_subset("src/frob/strata/*.py", "src/frob/strata/**")


class TestScopeCli:
    def test_cli_add_free_path(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_add_free_path
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        cfg = AppConfig(
            ticket_command="scope",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_scope_add=["src/frob/__main__.py"],
            ticket_scope_reason="new subcommand registration",
        )
        _scope(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        assert "src/frob/__main__.py" in queue.tickets[ticket.id].scope

    def test_cli_add_leased_path_exits_nonzero(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_add_leased_path_exits_nonzero  # noqa: E501
        _make_ticket(
            tmp_path, scope=("src/frob/gates/**",), state=TicketState.IN_PROGRESS
        )
        agent = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        cfg = AppConfig(
            ticket_command="scope",
            ticket_id=agent.id,
            ticket_path=tmp_path,
            ticket_scope_add=["src/frob/gates/foo.py"],
            ticket_scope_reason="need it",
        )
        with pytest.raises(SystemExit) as exc_info:
            _scope(tmp_path, cfg)
        assert exc_info.value.code == 1

    # frob:ticket T-0995
    def test_cli_requires_reason(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_requires_reason
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        cfg = AppConfig(
            ticket_command="scope",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_scope_add=["src/frob/__main__.py"],
        )
        with pytest.raises(SystemExit) as exc_info:
            _scope(tmp_path, cfg)
        assert exc_info.value.code == 1

    def test_cli_requires_add_or_remove(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_requires_add_or_r\
        # emove
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        cfg = AppConfig(
            ticket_command="scope",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_scope_reason="nothing",
        )
        with pytest.raises(SystemExit) as exc_info:
            _scope(tmp_path, cfg)
        assert exc_info.value.code == 1
