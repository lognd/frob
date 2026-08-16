"""T-2215: BUG003 (`frob.gates.must_still_pass_violations`, built by
T-2193) had zero callers -- this proves it now has a live one, mirroring
T-1421/T-1427's own "the guard was built and unit-tested but nothing
called it" pattern one more time. These tests exercise the wiring
(`frob.tickets._land._must_still_pass_land_violations`,
`_must_still_pass_waiver_reason`) directly, monkeypatching only the one
genuine external boundary (`frob.gates.must_still_pass_violations`
itself, which spawns real pytest subprocesses) -- the same "stub the
external-process seam, exercise the real wiring" shape
`test_ticket_close_bug002_t1427.py` already uses for BUG002.

Acceptance criterion 0: `test_land_refuses_when_control_broke_at_fix`
FAILS against current main -- `_must_still_pass_land_violations` does not
exist there at all (ImportError at collection), so `must_still_pass_
violations`'s finding was inert prose with no caller, exactly the gap
this ticket closes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.gates._models import Severity, Violation
from frob.tickets import Origin, Ticket, TicketKind, TicketState


# frob:ticket T-2215
def _make_ticket(body: str = "") -> Ticket:
    """A minimal ticket with a `body` under test -- only `body` matters
    to `_must_still_pass_waiver_reason`/`_must_still_pass_land_violations`,
    every other field is filler."""
    return Ticket(
        id="T-9001",
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        body=body,
    )


# frob:ticket T-2215
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own tests -- no production caller to wire it to by design" permanent="true"  # noqa: E501
def _sample_violation(rule: str = "BUG003") -> Violation:
    """One synthetic BUG003-shaped finding, standing in for a real
    `must_still_pass_violations` return value without spawning pytest."""
    return Violation(
        rule=rule,
        severity=Severity.ERROR,
        file="tickets.md",
        line=0,
        message="BUG003: T-9001's must-still-pass control broke",
    )


# frob:ticket T-2215
class TestMustStillPassWaiver:
    """`frob.tickets._land._must_still_pass_waiver_reason` -- the
    `frob:waive BUG003 reason="..."` body-text escape hatch, mirroring
    `frob.gates._mutation_evidence._bug002_waiver_reason`'s own shape."""

    # frob:ticket T-2215
    def test_reason_present_suppresses(self) -> None:
        """A well-formed `frob:waive BUG003 reason="..."` line is found
        and its reason text extracted."""
        from frob.tickets._land import _must_still_pass_waiver_reason

        ticket = _make_ticket(
            body='## Description\nfrob:waive BUG003 reason="known infra gap"\n'
        )
        assert _must_still_pass_waiver_reason(ticket) == "known infra gap"

    # frob:ticket T-2215
    def test_bare_directive_without_reason_does_not_suppress(self) -> None:
        """A `frob:waive BUG003` line with no `reason="..."` clause is
        NOT a well-formed waiver -- `None`, not suppression."""
        from frob.tickets._land import _must_still_pass_waiver_reason

        ticket = _make_ticket(body="## Description\nfrob:waive BUG003\n")
        assert _must_still_pass_waiver_reason(ticket) is None

    # frob:ticket T-2215
    def test_no_directive_returns_none(self) -> None:
        """No waiver directive at all -- `None`."""
        from frob.tickets._land import _must_still_pass_waiver_reason

        ticket = _make_ticket(body="## Description\nnothing here.\n")
        assert _must_still_pass_waiver_reason(ticket) is None


# frob:ticket T-2215
class TestMustStillPassWiring:
    """`frob.tickets._land._must_still_pass_land_violations` -- BUG003's
    actual land-time call site, the thing this ticket's own body says has
    zero callers on current main."""

    # frob:ticket T-2215
    @pytest.mark.parametrize(
        "body",
        [
            pytest.param("## Description\nno directive.\n", id="no_directive"),
            pytest.param(
                "## Description\nfrob:must-still-pass tests/x.py::test_y\n",
                id="control_passes_both",
            ),
        ],
    )
    def test_land_succeeds_when_gate_reports_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str
    ) -> None:
        """Dogfood controls 1 and 2 in one parametrized test (DUP002:
        these two shapes exercised identical wiring code, differing only
        in which ticket body produced the gate's clean `()` return --
        merged rather than waived): no `frob:must-still-pass` directive,
        and a declared control that genuinely passes at both fix and
        parent, both leave the underlying gate returning `()` -- wiring
        it in must be a complete no-op for both, so an ordinary land
        (case 1) and an honestly-passing control (case 2) are both
        unaffected."""
        from frob.tickets._land import _must_still_pass_land_violations

        monkeypatch.setattr(
            "frob.gates.must_still_pass_violations",
            lambda root, ticket, base_ref: (),
        )
        ticket = _make_ticket(body=body)
        result = _must_still_pass_land_violations(tmp_path, ticket, "main")
        assert result == ()

    # frob:ticket T-2215
    def test_land_refuses_when_control_broke_at_fix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A genuine BUG003 finding (the gate returns a real ERROR
        violation) is surfaced by the wiring, unwaived -- this is the
        shape that currently CANNOT be produced on main at all, since
        `_must_still_pass_land_violations` does not exist there."""
        from frob.tickets._land import _must_still_pass_land_violations

        monkeypatch.setattr(
            "frob.gates.must_still_pass_violations",
            lambda root, ticket, base_ref: (_sample_violation(),),
        )
        ticket = _make_ticket(
            body="## Description\nfrob:must-still-pass tests/x.py::test_y\n"
        )
        result = _must_still_pass_land_violations(tmp_path, ticket, "main")
        assert len(result) == 1
        assert result[0].rule == "BUG003"

    # frob:ticket T-2215
    def test_waived_finding_is_suppressed_but_logged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A genuine BUG003 finding with a matching `frob:waive BUG003
        reason="..."` in the ticket body is suppressed (same escape-hatch
        shape as BUG002's own `_BUG002_WAIVER_RE`)."""
        from frob.tickets._land import _must_still_pass_land_violations

        monkeypatch.setattr(
            "frob.gates.must_still_pass_violations",
            lambda root, ticket, base_ref: (_sample_violation(),),
        )
        ticket = _make_ticket(
            body=(
                "## Description\nfrob:must-still-pass tests/x.py::test_y\n"
                'frob:waive BUG003 reason="known false positive"\n'
            )
        )
        result = _must_still_pass_land_violations(tmp_path, ticket, "main")
        assert result == ()


# frob:ticket T-2215
class TestMustStillPassCombinesWithBug002:
    """Exercises the REAL `+`-concatenation call sites this ticket edited
    (`_mutation_evidence_deferred`/`_mutation_evidence_synchronous` in
    `_land.py`, `_close_mutation_evidence_for_ticket` in `_close_cmd.py`)
    rather than the `_must_still_pass_land_violations` wrapper alone --
    `TestMustStillPassWiring` above monkeypatches that wrapper's own
    underlying gate directly, which never exercises these three call
    sites' own `bug002_violations + bug003_violations`-shaped lines at
    all (a mutation-evidence sweep against this ticket found exactly
    this: those three concatenation lines had zero mutants killed by the
    tests above). Here BUG002's own gate is stubbed to `()` and ONLY
    BUG003 (`must_still_pass_violations`) contributes a finding, so a
    passing assertion is only possible if the wiring genuinely COMBINES
    both, not merely defers to BUG002 alone."""

    # frob:ticket T-2215
    def test_land_deferred_refuses_on_bug003_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_mutation_evidence_deferred`: BUG002 clean, BUG003 dirty ->
        the land call must still refuse (proves BUG003's contribution is
        genuinely ADDED to BUG002's, not shadowed by it)."""
        from typani.result import Ok

        from frob.tickets._land import _mutation_evidence_deferred

        monkeypatch.setattr(
            "frob.gates.bug_repro_violations", lambda root, ticket, base_ref: ()
        )
        monkeypatch.setattr(
            "frob.gates.must_still_pass_violations",
            lambda root, ticket, base_ref: (_sample_violation(),),
        )
        monkeypatch.setattr(
            "frob.tickets._mutation_sweep_queue.enqueue_pending_sweep",
            lambda worktree, ticket_id, base_ref, kind: Ok(None),
        )
        ticket = _make_ticket(
            body="## Description\nfrob:must-still-pass tests/x.py::test_y\n"
        )
        result = _mutation_evidence_deferred(tmp_path, ticket, "main", rapid=False)
        assert result.is_err

    # frob:ticket T-2215
    def test_land_synchronous_refuses_on_bug003_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_mutation_evidence_synchronous`: TEST016 and BUG002 both
        clean, BUG003 dirty -> the land call must still refuse."""
        from frob.tickets._land import _mutation_evidence_synchronous

        monkeypatch.setattr(
            "frob.gates.mutation_evidence_violations",
            lambda root, ticket, base_ref: (),
        )
        monkeypatch.setattr(
            "frob.gates.bug_repro_violations", lambda root, ticket, base_ref: ()
        )
        monkeypatch.setattr(
            "frob.gates.must_still_pass_violations",
            lambda root, ticket, base_ref: (_sample_violation(),),
        )
        ticket = _make_ticket(
            body="## Description\nfrob:must-still-pass tests/x.py::test_y\n"
        )
        result = _mutation_evidence_synchronous(tmp_path, ticket, "main", skip=False)
        assert result.is_err

    # frob:ticket T-2215
    def test_close_refuses_on_bug003_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_close_mutation_evidence_for_ticket`: TEST016 and BUG002 both
        clean, BUG003 dirty -> the direct `frob ticket close` path must
        also refuse (not just the land path)."""
        from typani.result import Ok

        from frob.app.ticket_runner._close_cmd import (
            _close_mutation_evidence_for_ticket,
        )

        monkeypatch.setattr("frob.gitio._merge_base", lambda root, base_ref: Ok("main"))
        monkeypatch.setattr(
            "frob.gates.mutation_evidence_violations",
            lambda root, ticket, base_ref: (),
        )
        monkeypatch.setattr(
            "frob.gates.bug_repro_violations", lambda root, ticket, base_ref: ()
        )
        monkeypatch.setattr(
            "frob.gates.must_still_pass_violations",
            lambda root, ticket, base_ref: (_sample_violation(),),
        )
        ticket = _make_ticket(
            body="## Description\nfrob:must-still-pass tests/x.py::test_y\n"
        )
        result = _close_mutation_evidence_for_ticket(tmp_path, ticket, "main")
        assert result is False
