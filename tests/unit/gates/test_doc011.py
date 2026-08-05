"""Tests for DOC011 (T-1486): a `T-####`/`T-draft-<hex>` mention in doc
prose must resolve to a real ticket in the ledger (active or archived).

New test file rather than an addition to `tests/test_gates.py` (this gate
family's usual home) -- that file is leased by another in-progress ticket
(T-1205) for the duration of this ticket's work, per `frob ticket scope
T-1486 --add`'s own `ScopeLeaseConflict` refusal.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.gates import docstatus_gate
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import write_ticket


def _test_rules(violations) -> set[str]:
    """Every distinct `Violation.rule` id in `violations`."""
    return {v.rule for v in violations}


def _test_ticket(
    *, ticket_id: str = "T-0001", state: TicketState = TicketState.QUEUED
) -> Ticket:
    """A minimal, valid `Ticket` for seeding a fake repo's ledger."""
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        body="## Description\nx\n\n## Done report\ndone\n"
        if state.value == "done"
        else "",
    )


# frob:ticket T-1486
class TestDoc011TicketIdProse:
    """DOC011: a doc's prose `T-####` mention must name a real ticket."""

    def test_unknown_ticket_id_in_prose_fires_doc011(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse.test_unknown_ticket_id_in_prose_fires_doc011  # noqa: E501
        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "guide.md").write_text(
            "# Guide\n\nSee T-9999 for background.\n", encoding="utf-8"
        )
        violations = docstatus_gate(root)
        assert "DOC011" in _test_rules(violations)
        doc011 = [v for v in violations if v.rule == "DOC011"]
        assert any("T-9999" in v.message for v in doc011)
        assert any(v.file == "docs/guide.md" for v in doc011)

    def test_known_active_ticket_id_passes(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse.test_known_active_ticket_id_passes  # noqa: E501
        root = tmp_path / "repo"
        write_ticket(root, _test_ticket(ticket_id="T-0001")).danger_ok
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "guide.md").write_text(
            "# Guide\n\nSee T-0001 for background.\n", encoding="utf-8"
        )
        violations = docstatus_gate(root)
        assert "DOC011" not in _test_rules(violations)

    def test_id_inside_fenced_code_block_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse.test_id_inside_fenced_code_block_is_not_flagged  # noqa: E501
        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "guide.md").write_text(
            "# Guide\n\n```\nfrob ticket show T-9999\n```\n", encoding="utf-8"
        )
        violations = docstatus_gate(root)
        assert "DOC011" not in _test_rules(violations)

    def test_id_inside_inline_code_span_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse.test_id_inside_inline_code_span_is_not_flagged  # noqa: E501
        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "guide.md").write_text(
            "# Guide\n\nRun `frob ticket show T-9999` as an example.\n",
            encoding="utf-8",
        )
        violations = docstatus_gate(root)
        assert "DOC011" not in _test_rules(violations)

    def test_no_ledger_at_all_still_flags_prose_mentions(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse.test_no_ledger_at_all_still_flags_prose_mentions  # noqa: E501
        """A repo with no `tickets.md` at all (fresh checkout, or a
        malformed-ledger degrade) has an empty known-id set -- every real
        prose mention still fires DOC011 rather than raising."""
        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "guide.md").write_text(
            "# Guide\n\nSee T-0001 for background.\n", encoding="utf-8"
        )
        violations = docstatus_gate(root)
        assert "DOC011" in _test_rules(violations)

    def test_duplicate_mention_on_one_line_reported_once(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse.test_duplicate_mention_on_one_line_reported_once  # noqa: E501
        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "guide.md").write_text(
            "# Guide\n\nT-9999 and T-9999 again.\n", encoding="utf-8"
        )
        violations = docstatus_gate(root)
        doc011 = [v for v in violations if v.rule == "DOC011"]
        assert len(doc011) == 1
