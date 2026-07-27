"""Tests for `frob ticket reverify` (T-1005): the missing verb for a
post-close send-back -- re-run the full close-time verification suite
against an already-DONE ticket and refresh its recap, with NO state
transition either way.

Layered like `close`'s own test coverage:
- `TestRecoverDoneReportWhy` -- the pure `_models.py` narrative-recovery
  helper (the mechanical inverse of `compose_done_report`'s narrative
  half).
- `TestReverifyCloseGuard` -- the `frob.tickets` state-machine half
  (`reverify_close_guard`, wrapping the SAME `_done_transition_guard`
  `close` uses, minus the write/transition step).
- `TestReverifyCli` -- the full `frob ticket reverify` CLI wiring,
  exercised the same hermetic way `tests/test_tickets_evidence_cli.py`
  exercises `_close` (monkeypatched collection/pass-check, no real
  subprocess pytest/cargo spawn).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import _close, _done_report, _new, _reverify
from frob.testing._models import CollectedTests
from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    add_evidence,
    load_queue,
    reverify_close_guard,
    transition,
)
from frob.tickets._models import recover_done_report_why
from frob.tickets._store import _serialize_ticket


# frob:waive DUP001 reason="mirrors tests/test_tickets_evidence_cli.py's own \
# _patch_collect/_patch_passing hermetic-collection fixtures exactly (same \
# monkeypatch target, same rationale: stay fast/hermetic without spawning a real \
# pytest/cargo subprocess) -- a shared helper module for these two would be a purely \
# cosmetic extraction across otherwise-independent test files, not a real duplicated \
# rule"
def _patch_collect(monkeypatch: pytest.MonkeyPatch, node_ids: frozenset[str]) -> None:
    """Make `frob.testing.collect_python_tests` return `node_ids` without
    spawning pytest, so CLI evidence-routing tests stay hermetic."""
    import frob.testing as testing_mod

    monkeypatch.setattr(
        testing_mod,
        "collect_python_tests",
        lambda root: Ok(CollectedTests(node_ids=node_ids)),
    )


def _patch_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `_verify_ids_passing` report every id it is asked about as
    passing, without spawning pytest/cargo."""
    import frob.app.ticket_runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "_verify_ids_passing",
        lambda root, node_ids, python_collected, rust_collected, runners: frozenset(
            node_ids
        ),
    )


def _patch_none_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `_verify_ids_passing` report NOTHING as passing -- simulates a
    real regression (evidence that used to pass no longer does) for the
    "surfaces a now-failing evidence id loudly" contract."""
    import frob.app.ticket_runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "_verify_ids_passing",
        lambda root, node_ids, python_collected, rust_collected, runners: frozenset(),
    )


class TestRecoverDoneReportWhy:
    """`frob.tickets._models.recover_done_report_why` -- the mechanical
    inverse of `compose_done_report`'s narrative half."""

    def test_recovers_narrative_before_changed_marker(self) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestRecoverDoneReportWhy.test_recovers_narrative_before_changed_marker  # noqa: E501
        body = (
            "## Description\nx\n\n"
            "## Done report\n\n"
            "did the thing, for real reasons\n\n"
            "### Changed\n- a.py\n\n"
            "### Evidence\n- tests/x.py::test_a\n"
        )
        assert recover_done_report_why(body) == "did the thing, for real reasons"

    def test_none_when_no_done_report_section(self) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestRecoverDoneReportWhy.test_none_when_no_done_report_section  # noqa: E501
        assert recover_done_report_why("## Description\nx\n") is None

    def test_none_when_no_changed_marker_to_anchor_against(self) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestRecoverDoneReportWhy.test_none_when_no_changed_marker_to_anchor_against  # noqa: E501
        # A terse, hand-typed Done report predating T-0458's auto-fill
        # sections -- no "### Changed" marker to anchor a narrative split
        # against, so this must return None rather than guess.
        body = "## Description\nx\n\n## Done report\nDone.\n"
        assert recover_done_report_why(body) is None


def _ticket(
    *,
    ticket_id: str = "T-0001",
    state: TicketState = TicketState.DONE,
    evidence: tuple[str, ...] = ("tests/x.py::test_a",),
    body: str = (
        "## Description\nx\n\n"
        "## Done report\n\nnarrative\n\n"
        "### Changed\n- a.py\n\n"
        "### Evidence\n- tests/x.py::test_a\n"
    ),
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="sample",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=(),
        evidence=evidence,
        body=body,
    )


def _write(root: Path, ticket: Ticket, slug: str = "sample") -> Path:
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    path = tickets_dir / f"{ticket.id}-{slug}.md"
    path.write_text(_serialize_ticket(ticket), encoding="utf-8")
    return path


class TestReverifyCloseGuard:
    """`frob.tickets.reverify_close_guard` -- the state-machine half:
    wraps the SAME `_done_transition_guard` `transition(..., DONE, ...)`
    runs at close time, with no write on either outcome."""

    def test_passes_on_strengthened_done_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestReverifyCloseGuard.test_passes_on_strengthened_done_ticket  # noqa: E501
        _write(tmp_path, _ticket())
        result = reverify_close_guard(
            tmp_path,
            "T-0001",
            evidence_reverified=True,
        )
        assert result.is_ok
        assert result.danger_ok.state == TicketState.DONE
        # No write happened -- the ledger's own state is still exactly done.
        reloaded = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert reloaded.state == TicketState.DONE

    def test_fails_loudly_on_now_failing_evidence(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestReverifyCloseGuard.test_fails_loudly_on_now_failing_evidence  # noqa: E501
        _write(tmp_path, _ticket())
        result = reverify_close_guard(
            tmp_path,
            "T-0001",
            evidence_reverified=False,
        )
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceNotPassing
        # State must remain done -- a failed reverify never transitions.
        reloaded = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert reloaded.state == TicketState.DONE

    def test_refuses_non_done_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestReverifyCloseGuard.test_refuses_non_done_ticket  # noqa: E501
        _write(tmp_path, _ticket(state=TicketState.IN_PROGRESS))
        result = reverify_close_guard(tmp_path, "T-0001")
        assert result.is_err
        assert result.danger_err == TicketError.InvalidTransition


class TestReverifyCli:
    """`frob ticket reverify <id>` -- full CLI wiring, hermetic (no real
    pytest/cargo subprocess for evidence collection)."""

    def _seed_done_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Build a REAL done ticket via new -> start -> evidence ->
        done-report -> close, so its Done report is genuinely
        `compose_done_report`-shaped (has a "### Changed" marker to anchor
        `recover_done_report_why` against, and a Captured claims section)
        -- not a hand-typed static body."""
        new_cfg = AppConfig(
            ticket_command="new",
            ticket_title="reverify smoke",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, new_cfg)
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)

        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        add_evidence(
            tmp_path,
            "T-0001",
            ("tests/x.py::test_a",),
            frozenset({"tests/x.py::test_a"}),
        )

        _patch_passing(monkeypatch)
        report_cfg = AppConfig(
            ticket_command="done-report",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_why="initial narrative",
            ticket_base_ref="does-not-exist",
        )
        _done_report(tmp_path, report_cfg)

        close_cfg = AppConfig(
            ticket_command="close", ticket_id="T-0001", ticket_path=tmp_path
        )
        _close(tmp_path, close_cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.state == TicketState.DONE
        assert "### Changed" in ticket.body

    def test_reruns_verification_and_refreshes_recap_state_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_reruns_verification_and_refreshes_recap_state_unchanged  # noqa: E501
        self._seed_done_ticket(tmp_path, monkeypatch)
        before = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert "- tests: 1 passed (from 1 evidence id(s))" in before.body

        # Post-close send-back: a strengthened/additional evidence id gets
        # bound to the already-done ticket (the churn-item-6 scenario).
        _patch_collect(
            monkeypatch, frozenset({"tests/x.py::test_a", "tests/x.py::test_b"})
        )
        reverify_cfg = AppConfig(
            ticket_command="reverify",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_b"],
            ticket_base_ref="does-not-exist",
        )
        _reverify(tmp_path, reverify_cfg)

        after = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        # State unchanged -- reverify never transitions.
        assert after.state == TicketState.DONE
        # New evidence bound, and the recap reflects it.
        assert after.evidence == ("tests/x.py::test_a", "tests/x.py::test_b")
        assert "- tests: 2 passed (from 2 evidence id(s))" in after.body
        # Narrative carried through verbatim, not replaced.
        assert "initial narrative" in after.body

    def test_surfaces_now_failing_evidence_loudly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_surfaces_now_failing_evidence_loudly  # noqa: E501
        self._seed_done_ticket(tmp_path, monkeypatch)
        before = load_queue(tmp_path).danger_ok.tickets["T-0001"]

        # Simulate a real regression: the bound evidence no longer passes
        # when re-run against the current tree.
        _patch_none_passing(monkeypatch)
        reverify_cfg = AppConfig(
            ticket_command="reverify",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_base_ref="does-not-exist",
        )
        with pytest.raises(SystemExit) as exc:
            _reverify(tmp_path, reverify_cfg)
        assert exc.value.code == 1

        after = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        # State stays done, and the recap is left exactly as it was --
        # a failed reverify never overwrites the last-known-good report.
        assert after.state == TicketState.DONE
        assert after.body == before.body

    def test_refuses_non_done_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_refuses_non_done_ticket  # noqa: E501
        new_cfg = AppConfig(
            ticket_command="new",
            ticket_title="not done yet",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, new_cfg)
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)

        reverify_cfg = AppConfig(
            ticket_command="reverify", ticket_id="T-0001", ticket_path=tmp_path
        )
        with pytest.raises(SystemExit) as exc:
            _reverify(tmp_path, reverify_cfg)
        assert exc.value.code == 1

        after = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert after.state == TicketState.IN_PROGRESS
